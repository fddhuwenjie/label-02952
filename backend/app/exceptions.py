"""自定义异常类"""


class PinyinError(Exception):
    """拼音引擎基础异常"""
    pass


class InvalidPinyinError(PinyinError):
    """无效拼音输入"""

    def __init__(self, pinyin: str, reason: str = ""):
        self.pinyin = pinyin
        self.reason = reason
        msg = f"无效拼音输入: '{pinyin}'"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class InvalidLimitError(PinyinError):
    """无效的候选数量限制"""

    def __init__(self, limit: int, max_limit: int):
        self.limit = limit
        self.max_limit = max_limit
        super().__init__(f"候选数量 {limit} 无效，应在 1~{max_limit} 之间")


class DictLoadError(PinyinError):
    """词库加载失败"""

    def __init__(self, path: str, reason: str = ""):
        self.path = path
        super().__init__(f"词库加载失败: {path}" + (f" ({reason})" if reason else ""))
