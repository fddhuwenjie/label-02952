"""拼音输入法配置模块

支持通过配置文件或环境变量自定义参数。
配置优先级: 环境变量 > 配置文件 > 默认值
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATH = os.environ.get(
    "PINYIN_CONFIG_PATH",
    str(Path(__file__).parent.parent / "config.json"),
)


@dataclass
class PinyinConfig:
    """拼音输入法配置"""

    # 候选词相关
    default_candidate_limit: int = 10
    max_candidate_limit: int = 50
    sentence_candidate_limit: int = 5

    # 词库路径
    user_dict_path: Optional[str] = None

    # 词频统计
    enable_frequency: bool = True
    frequency_db_path: Optional[str] = None

    # 日志
    log_level: str = "WARNING"
    log_format: str = "json"  # "json" 或 "text"
    log_file: Optional[str] = None

    # 引擎
    max_pinyin_length: int = 50
    max_segments: int = 20


_config: Optional[PinyinConfig] = None


def load_config(path: Optional[str] = None) -> PinyinConfig:
    """加载配置，合并文件配置和环境变量"""
    config = PinyinConfig()
    config_path = path or DEFAULT_CONFIG_PATH

    # 从文件加载
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except (json.JSONDecodeError, OSError):
            pass  # 配置文件损坏时使用默认值，日志模块会记录

    # 环境变量覆盖（PINYIN_ 前缀）
    env_mapping = {
        "PINYIN_CANDIDATE_LIMIT": ("default_candidate_limit", int),
        "PINYIN_MAX_CANDIDATE_LIMIT": ("max_candidate_limit", int),
        "PINYIN_USER_DICT_PATH": ("user_dict_path", str),
        "PINYIN_ENABLE_FREQUENCY": ("enable_frequency", lambda v: v.lower() in ("1", "true", "yes")),
        "PINYIN_LOG_LEVEL": ("log_level", str),
        "PINYIN_LOG_FORMAT": ("log_format", str),
        "PINYIN_LOG_FILE": ("log_file", str),
    }

    for env_key, (attr, converter) in env_mapping.items():
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                setattr(config, attr, converter(env_val))
            except (ValueError, TypeError):
                pass

    return config


def get_config() -> PinyinConfig:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """重置配置（用于测试）"""
    global _config
    _config = None
