"""拼音输入法引擎

增强功能：
- 结构化日志
- 用户词库与词频智能排序
- 配置化参数
- 完善的输入校验与错误处理
"""
import re
from typing import Dict, List, Optional

from .config import get_config
from .exceptions import InvalidLimitError, InvalidPinyinError
from .logger import get_logger
from .pinyin_dict import PINYIN_TO_HANZI
from .phrase_engine import get_phrase_engine, PhraseEngine
from .user_dict import UserDict

logger = get_logger("engine")

# 合法拼音字符
_PINYIN_PATTERN = re.compile(r"^[a-zA-Z]+$")


def _validate_pinyin_input(pinyin: str, max_length: int) -> str:
    """校验并规范化拼音输入"""
    if not isinstance(pinyin, str):
        raise InvalidPinyinError(str(pinyin), "输入必须为字符串")
    pinyin = pinyin.strip().lower()
    if not pinyin:
        return ""
    if len(pinyin) > max_length:
        raise InvalidPinyinError(pinyin, f"长度超过上限 {max_length}")
    if not _PINYIN_PATTERN.match(pinyin):
        raise InvalidPinyinError(pinyin, "包含非法字符，仅允许英文字母")
    return pinyin


def _validate_limit(limit: int, max_limit: int) -> int:
    """校验候选数量限制"""
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise InvalidLimitError(limit, max_limit)
    if limit < 1 or limit > max_limit:
        raise InvalidLimitError(limit, max_limit)
    return limit


class PinyinEngine:
    """拼音输入法引擎"""

    def __init__(self):
        self._config = get_config()
        self.pinyin_dict = dict(PINYIN_TO_HANZI)
        self._user_dict = UserDict()
        self._phrase_engine: PhraseEngine = get_phrase_engine()
        self._build_prefix_index()
        logger.info(
            "引擎初始化完成，内置拼音 %d 条，用户词库 %d 条，词组 %d 条",
            len(self.pinyin_dict),
            self._user_dict.get_stats()["user_words_count"],
            self._phrase_engine.get_stats()["total_phrases"],
        )

    def _build_prefix_index(self) -> None:
        """构建前缀索引，用于模糊匹配"""
        self.prefix_index: Dict[str, List[str]] = {}
        for pinyin in self.pinyin_dict.keys():
            for i in range(1, len(pinyin) + 1):
                prefix = pinyin[:i]
                if prefix not in self.prefix_index:
                    self.prefix_index[prefix] = []
                if pinyin not in self.prefix_index[prefix]:
                    self.prefix_index[prefix].append(pinyin)

    def get_candidates(self, pinyin: str, limit: Optional[int] = None) -> List[str]:
        """根据拼音获取候选汉字列表

        Args:
            pinyin: 拼音字符串
            limit: 候选数量上限，默认使用配置值

        Returns:
            候选汉字列表

        Raises:
            InvalidPinyinError: 拼音格式无效
            InvalidLimitError: limit 值无效
        """
        if limit is None:
            limit = self._config.default_candidate_limit
        limit = _validate_limit(limit, self._config.max_candidate_limit)
        pinyin = _validate_pinyin_input(pinyin, self._config.max_pinyin_length)

        if not pinyin:
            return []

        logger.debug("查询拼音: %s, limit=%d", pinyin, limit)

        # 合并用户词库 + 内置词库
        user_words = self._user_dict.get_user_words(pinyin)
        builtin_words = []

        # 精确匹配
        if pinyin in self.pinyin_dict:
            builtin_words = list(self.pinyin_dict[pinyin])
        elif pinyin in self.prefix_index:
            # 前缀匹配
            for full_pinyin in self.prefix_index[pinyin]:
                builtin_words.extend(self.pinyin_dict[full_pinyin])

        # 用户词优先，去重
        merged = user_words + [w for w in builtin_words if w not in user_words]

        # 词频智能排序
        if self._config.enable_frequency:
            merged = self._user_dict.sort_by_frequency(pinyin, merged)

        result = merged[:limit]
        logger.debug("拼音 '%s' 返回 %d 个候选", pinyin, len(result))
        return result

    def get_phrase_candidates(self, pinyin: str, limit: Optional[int] = None) -> List[str]:
        """根据拼音获取候选词组列表

        Args:
            pinyin: 拼音字符串（支持连续拼音）
            limit: 候选数量上限，默认使用配置值

        Returns:
            候选词组列表
        """
        if limit is None:
            limit = self._config.default_candidate_limit
        limit = _validate_limit(limit, self._config.max_candidate_limit)
        pinyin = _validate_pinyin_input(pinyin, self._config.max_pinyin_length)

        if not pinyin:
            return []

        logger.debug("查询词组: %s, limit=%d", pinyin, limit)

        phrase_results = self._phrase_engine.match_phrases(pinyin)
        longest_match = phrase_results["longest_match"]
        all_segments = phrase_results["all_segments"]

        # 合并结果，优先最长匹配，然后是其他切分方案
        phrases = []
        if longest_match:
            phrases.append("".join(longest_match))
        for seg in all_segments[:limit]:
            phrase = "".join(seg)
            if phrase not in phrases:
                phrases.append(phrase)

        result = phrases[:limit]
        logger.debug("拼音 '%s' 返回 %d 个词组候选", pinyin, len(result))
        return result

    def get_phrases_with_alternatives(self, pinyin: str, limit: Optional[int] = None) -> Dict:
        """获取词组候选及所有可能的切分方案

        Returns:
            {
                "phrases": ["中华人民共和国", "中华", "中国", ...],
                "alternatives": [
                    ["中华", "人民", "共和国"],
                    ["中", "华人", "民工", "和国"],
                    ...
                ]
            }
        """
        if limit is None:
            limit = self._config.default_candidate_limit
        limit = _validate_limit(limit, self._config.max_candidate_limit)
        pinyin = _validate_pinyin_input(pinyin, self._config.max_pinyin_length)

        if not pinyin:
            return {"phrases": [], "alternatives": []}

        phrase_results = self._phrase_engine.match_phrases(pinyin)
        all_segments = phrase_results["all_segments"]

        phrases = []
        alternatives = []

        for seg in all_segments:
            phrase = "".join(seg)
            if phrase not in phrases and len(phrases) < limit:
                phrases.append(phrase)
            if len(seg) > 1 and alternatives is not None:
                alternatives.append(seg)

        # 限制 alternatives 数量
        alternatives = alternatives[:limit]

        logger.debug("拼音 '%s' 返回 %d 个词组, %d 个备选切分", pinyin, len(phrases), len(alternatives))
        return {
            "phrases": phrases,
            "alternatives": alternatives,
        }

    def get_all_pinyins(self) -> List[str]:
        """获取所有支持的拼音列表"""
        return sorted(self.pinyin_dict.keys())

    def search_pinyin(self, query: str) -> List[str]:
        """搜索匹配的拼音

        Raises:
            InvalidPinyinError: 查询格式无效
        """
        query = _validate_pinyin_input(query, self._config.max_pinyin_length)
        if not query:
            return []
        results = [p for p in self.pinyin_dict.keys() if p.startswith(query)]
        logger.debug("搜索 '%s' 匹配 %d 个拼音", query, len(results))
        return results

    def segment_pinyin(self, pinyin_str: str) -> List[List[str]]:
        """将连续拼音字符串切分为可能的拼音音节组合（动态规划）

        返回所有可能的切分方案，按音节数从少到多排序。
        例如: "nihao" -> [["ni", "hao"]]
              "xian" -> [["xian"], ["xi", "an"]]

        Raises:
            InvalidPinyinError: 输入格式无效
        """
        pinyin_str = _validate_pinyin_input(pinyin_str, self._config.max_pinyin_length)
        if not pinyin_str:
            return []

        all_pinyins = set(self.pinyin_dict.keys())
        n = len(pinyin_str)
        dp: List[Optional[List[List[str]]]] = [None] * (n + 1)
        dp[n] = [[]]

        for i in range(n - 1, -1, -1):
            results = []
            for j in range(i + 1, n + 1):
                substr = pinyin_str[i:j]
                if substr in all_pinyins and dp[j] is not None:
                    for rest in dp[j]:
                        if len([substr] + rest) <= self._config.max_segments:
                            results.append([substr] + rest)
            if results:
                dp[i] = results

        if dp[0] is None:
            logger.debug("拼音切分失败: %s", pinyin_str)
            return []

        dp[0].sort(key=lambda x: len(x))
        logger.debug("拼音 '%s' 切分为 %d 种方案", pinyin_str, len(dp[0]))
        return dp[0]

    def get_candidates_continuous(self, pinyin_str: str, limit: Optional[int] = None) -> dict:
        """处理连续拼音输入，自动切分并返回候选

        Returns:
            {
                "segments": ["ni", "hao"],
                "candidates": [["你", ...], ["好", ...]],
                "all_segments": [["ni", "hao"], ...],
                "phrases": ["你好", ...],
                "alternatives": [...]
            }

        Raises:
            InvalidPinyinError: 输入格式无效
            InvalidLimitError: limit 值无效
        """
        if limit is None:
            limit = self._config.default_candidate_limit
        limit = _validate_limit(limit, self._config.max_candidate_limit)
        pinyin_str = _validate_pinyin_input(pinyin_str, self._config.max_pinyin_length)

        if not pinyin_str:
            return {"segments": [], "candidates": [], "all_segments": [], "phrases": [], "alternatives": []}

        logger.info("连续拼音查询: %s", pinyin_str)

        # 获取词组匹配结果
        phrase_result = self.get_phrases_with_alternatives(pinyin_str, limit)

        # 精确匹配单个拼音
        if pinyin_str in self.pinyin_dict:
            candidates = self.get_candidates(pinyin_str, limit)
            return {
                "segments": [pinyin_str],
                "candidates": [candidates],
                "all_segments": self.segment_pinyin(pinyin_str),
                "phrases": phrase_result["phrases"],
                "alternatives": phrase_result["alternatives"],
            }

        # 尝试切分
        all_segments = self.segment_pinyin(pinyin_str)
        if not all_segments:
            candidates = self.get_candidates(pinyin_str, limit)
            return {
                "segments": [pinyin_str],
                "candidates": [candidates] if candidates else [],
                "all_segments": [],
                "phrases": phrase_result["phrases"],
                "alternatives": phrase_result["alternatives"],
            }

        best = all_segments[0]
        candidates = []
        for seg in best:
            c = self.get_candidates(seg, limit)
            candidates.append(c if c else [seg])

        logger.info("连续拼音 '%s' -> %s", pinyin_str, best)
        return {
            "segments": best,
            "candidates": candidates,
            "all_segments": all_segments,
            "phrases": phrase_result["phrases"],
            "alternatives": phrase_result["alternatives"],
        }

    def convert_sentence(self, pinyin_list: List[str], limit: Optional[int] = None) -> List[List[str]]:
        """将拼音列表转换为候选汉字组合

        Raises:
            InvalidPinyinError: 拼音格式无效
            InvalidLimitError: limit 值无效
        """
        if limit is None:
            limit = self._config.sentence_candidate_limit
        limit = _validate_limit(limit, self._config.max_candidate_limit)

        if not isinstance(pinyin_list, list):
            raise InvalidPinyinError(str(pinyin_list), "输入必须为拼音列表")

        result = []
        for pinyin in pinyin_list:
            candidates = self.get_candidates(pinyin, limit)
            result.append(candidates if candidates else [pinyin])

        logger.info("句子转换: %s -> %d 组候选", " ".join(pinyin_list), len(result))
        return result

    def record_selection(self, pinyin: str, word: str) -> None:
        """记录用户选词（用于词频学习）"""
        pinyin = _validate_pinyin_input(pinyin, self._config.max_pinyin_length)
        if pinyin and word:
            self._user_dict.record_selection(pinyin, word)

    def add_user_word(self, pinyin: str, word: str) -> None:
        """添加用户自定义词条"""
        pinyin = _validate_pinyin_input(pinyin, self._config.max_pinyin_length)
        if not pinyin:
            raise InvalidPinyinError("", "拼音不能为空")
        if not word or not word.strip():
            raise InvalidPinyinError(pinyin, "词条不能为空")
        self._user_dict.add_word(pinyin, word.strip())
        logger.info("添加用户词条: %s -> %s", pinyin, word)

    def get_stats(self) -> dict:
        """获取引擎统计信息"""
        return {
            "builtin_pinyins": len(self.pinyin_dict),
            "prefix_entries": len(self.prefix_index),
            **self._user_dict.get_stats(),
        }

    def save_user_data(self) -> None:
        """持久化用户数据"""
        self._user_dict.save()


# 全局引擎实例
_engine: Optional[PinyinEngine] = None


def get_engine() -> PinyinEngine:
    """获取拼音引擎单例"""
    global _engine
    if _engine is None:
        _engine = PinyinEngine()
    return _engine
