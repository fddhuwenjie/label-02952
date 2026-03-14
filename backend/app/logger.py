"""结构化日志模块

支持 JSON 和文本两种格式，可通过配置文件控制日志级别和输出目标。
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from .config import get_config


class JsonFormatter(logging.Formatter):
    """JSON 格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 附加自定义字段
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """可读文本格式日志"""

    FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s"

    def __init__(self):
        super().__init__(fmt=self.FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


_initialized = False


def setup_logging() -> None:
    """根据配置初始化日志系统"""
    global _initialized
    if _initialized:
        return

    config = get_config()
    root_logger = logging.getLogger("pinyin")
    root_logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stderr)
    if config.log_format == "json":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(TextFormatter())
    root_logger.addHandler(console_handler)

    # 文件输出（可选）
    if config.log_file:
        try:
            file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
            file_handler.setFormatter(JsonFormatter())
            root_logger.addHandler(file_handler)
        except OSError as e:
            root_logger.warning("无法打开日志文件 %s: %s", config.log_file, e)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    setup_logging()
    return logging.getLogger(f"pinyin.{name}")
