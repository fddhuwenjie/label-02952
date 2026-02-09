"""拼音输入法引擎"""
from typing import List, Dict, Optional
from .pinyin_dict import PINYIN_TO_HANZI


class PinyinEngine:
    """拼音输入法引擎"""
    
    def __init__(self):
        self.pinyin_dict = PINYIN_TO_HANZI
        self._build_prefix_index()
    
    def _build_prefix_index(self):
        """构建前缀索引，用于模糊匹配"""
        self.prefix_index: Dict[str, List[str]] = {}
        for pinyin in self.pinyin_dict.keys():
            for i in range(1, len(pinyin) + 1):
                prefix = pinyin[:i]
                if prefix not in self.prefix_index:
                    self.prefix_index[prefix] = []
                if pinyin not in self.prefix_index[prefix]:
                    self.prefix_index[prefix].append(pinyin)
    
    def get_candidates(self, pinyin: str, limit: int = 10) -> List[str]:
        """根据拼音获取候选汉字列表"""
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return []
        
        # 精确匹配
        if pinyin in self.pinyin_dict:
            return self.pinyin_dict[pinyin][:limit]
        
        # 前缀匹配
        candidates = []
        if pinyin in self.prefix_index:
            for full_pinyin in self.prefix_index[pinyin]:
                candidates.extend(self.pinyin_dict[full_pinyin])
        
        # 去重并限制数量
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)
                if len(unique_candidates) >= limit:
                    break
        
        return unique_candidates

    def get_all_pinyins(self) -> List[str]:
        """获取所有支持的拼音列表"""
        return sorted(self.pinyin_dict.keys())
    
    def search_pinyin(self, query: str) -> List[str]:
        """搜索匹配的拼音"""
        query = query.lower().strip()
        if not query:
            return []
        return [p for p in self.pinyin_dict.keys() if p.startswith(query)]
    
    def convert_sentence(self, pinyin_list: List[str], limit: int = 5) -> List[List[str]]:
        """将拼音列表转换为候选汉字组合"""
        result = []
        for pinyin in pinyin_list:
            candidates = self.get_candidates(pinyin, limit)
            result.append(candidates if candidates else [pinyin])
        return result


# 全局引擎实例
_engine: Optional[PinyinEngine] = None


def get_engine() -> PinyinEngine:
    """获取拼音引擎单例"""
    global _engine
    if _engine is None:
        _engine = PinyinEngine()
    return _engine
