"""拼音输入法引擎"""
from typing import List, Dict, Optional
from .pinyin_dict import PINYIN_TO_HANZI


class PinyinEngine:
    """拼音输入法引擎"""
    
    def __init__(self):
        self.pinyin_dict = PINYIN_TO_HANZI
        self._build_prefix_index()
    
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
    
    def segment_pinyin(self, pinyin_str: str) -> List[List[str]]:
        """将连续拼音字符串切分为可能的拼音音节组合（动态规划）
        
        返回所有可能的切分方案，按音节数从少到多排序。
        例如: "nihao" -> [["ni", "hao"]]
              "xian" -> [["xian"], ["xi", "an"]]
        """
        pinyin_str = pinyin_str.lower().strip()
        if not pinyin_str:
            return []
        
        all_pinyins = set(self.pinyin_dict.keys())
        n = len(pinyin_str)
        # dp[i] 存储从位置 i 开始的所有可能切分
        dp: List[Optional[List[List[str]]]] = [None] * (n + 1)
        dp[n] = [[]]  # 空串的切分
        
        for i in range(n - 1, -1, -1):
            results = []
            for j in range(i + 1, n + 1):
                substr = pinyin_str[i:j]
                if substr in all_pinyins and dp[j] is not None:
                    for rest in dp[j]:
                        results.append([substr] + rest)
            if results:
                dp[i] = results
        
        if dp[0] is None:
            return []
        
        # 按音节数排序，少的优先
        dp[0].sort(key=lambda x: len(x))
        return dp[0]

    def get_candidates_continuous(self, pinyin_str: str, limit: int = 10) -> dict:
        """处理连续拼音输入，自动切分并返回候选
        
        返回格式:
        {
            "segments": ["ni", "hao"],  # 最优切分方案
            "candidates": [["你", ...], ["好", ...]],  # 每个音节的候选
            "all_segments": [["ni", "hao"], ...]  # 所有可能的切分
        }
        """
        pinyin_str = pinyin_str.lower().strip()
        if not pinyin_str:
            return {"segments": [], "candidates": [], "all_segments": []}
        
        # 先尝试精确匹配单个拼音
        if pinyin_str in self.pinyin_dict:
            return {
                "segments": [pinyin_str],
                "candidates": [self.pinyin_dict[pinyin_str][:limit]],
                "all_segments": self.segment_pinyin(pinyin_str)
            }
        
        # 尝试切分
        all_segments = self.segment_pinyin(pinyin_str)
        if not all_segments:
            # 切分失败，尝试前缀匹配
            candidates = self.get_candidates(pinyin_str, limit)
            return {
                "segments": [pinyin_str],
                "candidates": [candidates] if candidates else [],
                "all_segments": []
            }
        
        # 使用最优切分（音节最少的方案）
        best = all_segments[0]
        candidates = []
        for seg in best:
            c = self.get_candidates(seg, limit)
            candidates.append(c if c else [seg])
        
        return {
            "segments": best,
            "candidates": candidates,
            "all_segments": all_segments
        }

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
