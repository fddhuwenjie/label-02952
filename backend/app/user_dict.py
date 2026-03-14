"""用户词库与词频统计模块

支持：
- 用户自定义词库（JSON 格式）
- 词频统计与智能排序
- 运行时动态添加词条
"""
import json
import os
import threading
from collections import defaultdict
from typing import Dict, List, Optional

from .config import get_config
from .logger import get_logger

logger = get_logger("user_dict")


class UserDict:
    """用户词库管理"""

    def __init__(self, dict_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._user_words: Dict[str, List[str]] = {}
        self._frequency: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._dict_path = dict_path or get_config().user_dict_path
        self._freq_path = get_config().frequency_db_path

        if self._dict_path:
            self._load_user_dict(self._dict_path)
        if self._freq_path:
            self._load_frequency(self._freq_path)

    def _load_user_dict(self, path: str) -> None:
        """加载用户词库文件"""
        if not os.path.isfile(path):
            logger.debug("用户词库文件不存在: %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._user_words = data
                logger.info("已加载用户词库: %s (%d 条)", path, len(data))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("加载用户词库失败: %s - %s", path, e)

    def _load_frequency(self, path: str) -> None:
        """加载词频数据"""
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for pinyin, freq_map in data.items():
                for char, count in freq_map.items():
                    self._frequency[pinyin][char] = count
            logger.info("已加载词频数据: %s", path)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("加载词频数据失败: %s - %s", path, e)

    def get_user_words(self, pinyin: str) -> List[str]:
        """获取用户词库中的候选词"""
        return list(self._user_words.get(pinyin, []))

    def add_word(self, pinyin: str, word: str) -> None:
        """动态添加用户词条"""
        with self._lock:
            if pinyin not in self._user_words:
                self._user_words[pinyin] = []
            if word not in self._user_words[pinyin]:
                self._user_words[pinyin].append(word)
                logger.debug("添加用户词条: %s -> %s", pinyin, word)

    def record_selection(self, pinyin: str, word: str) -> None:
        """记录用户选词，更新词频"""
        with self._lock:
            self._frequency[pinyin][word] += 1
            logger.debug("更新词频: %s -> %s (次数: %d)", pinyin, word, self._frequency[pinyin][word])

    def sort_by_frequency(self, pinyin: str, candidates: List[str]) -> List[str]:
        """根据词频对候选词排序（高频优先，保持原始顺序作为次要排序）"""
        freq_map = self._frequency.get(pinyin, {})
        if not freq_map:
            return candidates
        return sorted(candidates, key=lambda c: (-freq_map.get(c, 0), candidates.index(c)))

    def save(self) -> None:
        """持久化用户词库和词频数据"""
        with self._lock:
            if self._dict_path and self._user_words:
                try:
                    os.makedirs(os.path.dirname(self._dict_path) or ".", exist_ok=True)
                    with open(self._dict_path, "w", encoding="utf-8") as f:
                        json.dump(self._user_words, f, ensure_ascii=False, indent=2)
                    logger.info("已保存用户词库: %s", self._dict_path)
                except OSError as e:
                    logger.error("保存用户词库失败: %s", e)

            if self._freq_path and self._frequency:
                try:
                    os.makedirs(os.path.dirname(self._freq_path) or ".", exist_ok=True)
                    with open(self._freq_path, "w", encoding="utf-8") as f:
                        json.dump(dict(self._frequency), f, ensure_ascii=False, indent=2)
                    logger.info("已保存词频数据: %s", self._freq_path)
                except OSError as e:
                    logger.error("保存词频数据失败: %s", e)

    def get_stats(self) -> dict:
        """获取词频统计信息"""
        total_selections = sum(
            count for freq_map in self._frequency.values() for count in freq_map.values()
        )
        return {
            "user_words_count": sum(len(v) for v in self._user_words.values()),
            "frequency_entries": len(self._frequency),
            "total_selections": total_selections,
        }
