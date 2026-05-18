"""词组匹配引擎
基于 Trie 树实现高效词组前缀查找和匹配。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .phrase_dict import PHRASE_DICT


@dataclass
class TrieNode:
    """Trie 树节点"""
    children: Dict[str, 'TrieNode'] = field(default_factory=dict)
    is_end_of_word: bool = False
    phrase: Optional[str] = None


class PhraseEngine:
    """词组匹配引擎
    使用 Trie 树数据结构实现高效的词组前缀查找和匹配。
    """

    def __init__(self, phrase_dict: Optional[Dict[str, str]] = None):
        self.root = TrieNode()
        self.phrase_dict = phrase_dict or PHRASE_DICT
        self._build_trie()

    def _build_trie(self) -> None:
        """构建 Trie 树"""
        for pinyin, phrase in self.phrase_dict.items():
            node = self.root
            for char in pinyin:
                if char not in node.children:
                    node.children[char] = TrieNode()
                node = node.children[char]
            node.is_end_of_word = True
            node.phrase = phrase

    def search_prefix(self, prefix: str) -> List[Tuple[str, str]]:
        """搜索所有以指定前缀开头的词组
        返回: [(拼音, 词组), ...]
        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return self._collect_phrases(node, prefix)

    def _collect_phrases(self, node: TrieNode, current_pinyin: str) -> List[Tuple[str, str]]:
        """收集节点下所有词组"""
        results = []
        if node.is_end_of_word and node.phrase:
            results.append((current_pinyin, node.phrase))
        for char, child in node.children.items():
            results.extend(self._collect_phrases(child, current_pinyin + char))
        return results

    def match_longest(self, pinyin_str: str, start: int = 0) -> Tuple[Optional[str], Optional[str], int]:
        """最长匹配词组
        从指定位置开始查找最长的匹配词组
        返回: (拼音, 词组, 结束位置)，未找到返回 (None, None, start)
        """
        node = self.root
        longest_pinyin = None
        longest_phrase = None
        longest_end = start

        for i in range(start, len(pinyin_str)):
            char = pinyin_str[i]
            if char not in node.children:
                break
            node = node.children[char]
            if node.is_end_of_word and node.phrase:
                longest_pinyin = pinyin_str[start:i + 1]
                longest_phrase = node.phrase
                longest_end = i + 1

        return (longest_pinyin, longest_phrase, longest_end)

    def match_all_prefix(self, pinyin_str: str, start: int = 0) -> List[Tuple[str, str, int]]:
        """匹配所有以 start 开头的词组（包括模糊前缀匹配）
        返回: [(拼音, 词组, 结束位置), ...]，按拼音长度从长到短排序
        """
        # 精确匹配词组
        results = []
        node = self.root

        for i in range(start, len(pinyin_str)):
            char = pinyin_str[i]
            if char not in node.children:
                break
            node = node.children[char]
            if node.is_end_of_word and node.phrase:
                results.append((pinyin_str[start:i + 1], node.phrase, i + 1))

        # 模糊前缀匹配 - 如果当前位置是不完整的拼音前缀，尝试匹配以该前缀开头的词组
        # 但只返回那些能够在输入字符串范围内匹配的词组
        current_prefix = pinyin_str[start:]
        fuzzy_matches = self.search_prefix(current_prefix)
        for pinyin, phrase in fuzzy_matches:
            # 只有当词组的拼音完全在输入字符串范围内才返回
            # 对于模糊匹配，我们只在整个输入字符串作为前缀时返回
            if len(pinyin) <= len(pinyin_str) - start and pinyin_str[start:start + len(pinyin)] == pinyin:
                end_pos = start + len(pinyin)
                results.append((pinyin, phrase, end_pos))

        # 去重并按长度排序
        seen = set()
        unique_results = []
        for item in results:
            key = (item[0], item[1])
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        unique_results.sort(key=lambda x: len(x[0]), reverse=True)
        return unique_results

    def segment_longest_first(self, pinyin_str: str) -> List[str]:
        """最长词组优先切分
        返回切分后的词组列表
        """
        segments = []
        i = 0
        n = len(pinyin_str)

        while i < n:
            pinyin, phrase, end = self.match_longest(pinyin_str, i)
            if phrase:
                segments.append(phrase)
                i = end
            else:
                segments.append(pinyin_str[i])
                i += 1

        return segments

    def segment_all_possible(self, pinyin_str: str, max_segments: int = 10) -> List[List[str]]:
        """所有可能的词组切分方案
        返回所有可能的切分方案列表，按词频和长度排序
        """
        n = len(pinyin_str)
        if n == 0:
            return []

        # 动态规划，dp[i] 表示从位置 i 到末尾的所有切分方案
        dp: List[List[List[str]]] = [[] for _ in range(n + 1)]
        dp[n] = [[]]

        for i in range(n - 1, -1, -1):
            matches = self.match_all_prefix(pinyin_str, i)
            for pinyin, phrase, end in matches:
                for rest in dp[end]:
                    if len([phrase] + rest) <= max_segments:
                        dp[i].append([phrase] + rest)

            # 如果没有词组匹配，保留单字（拼音）
            if not dp[i]:
                for rest in dp[i + 1]:
                    if len([pinyin_str[i]] + rest) <= max_segments:
                        dp[i].append([pinyin_str[i]] + rest)

        # 去重并排序
        seen = set()
        unique_segments = []
        for seg in dp[0]:
            key = tuple(seg)
            if key not in seen:
                seen.add(key)
                unique_segments.append(seg)

        # 按切分数量（越少越好）和总词频排序
        unique_segments.sort(key=lambda x: (len(x), -sum(len(word) for word in x)))

        return unique_segments

    def match_phrases(self, pinyin_str: str) -> Dict:
        """匹配连续拼音，返回最长匹配和所有可能切分
        返回:
        {
            "longest_match": ["中华人民共和国"],
            "all_segments": [
                ["中华人民共和国"],
                ["中华", "人民", "共和国"],
                ["中", "华人", "民工", "和国"],
                ...
            ]
        }
        """
        # 先尝试完整匹配
        longest = self.segment_longest_first(pinyin_str)
        all_segments = self.segment_all_possible(pinyin_str)

        # 添加模糊前缀匹配的词组（输入是某个词组的前缀）
        fuzzy_matches = self.search_prefix(pinyin_str)
        for pinyin, phrase in fuzzy_matches:
            if len(pinyin) > len(pinyin_str):  # 只添加比输入长的词组（即输入是前缀）
                # 将模糊匹配作为单元素切分方案
                fuzzy_seg = [phrase]
                if fuzzy_seg not in all_segments:
                    all_segments.insert(0, fuzzy_seg)
                # 更新最长匹配
                if len("".join(fuzzy_seg)) > len("".join(longest)):
                    longest = fuzzy_seg

        # 过滤掉重复的 longest match
        if all_segments and all_segments[0] == longest:
            pass  # 已经在最前面了

        return {
            "longest_match": longest,
            "all_segments": all_segments,
        }

    def get_phrases_by_prefix(self, prefix: str, limit: int = 20) -> List[Tuple[str, str]]:
        """根据前缀获取候选词组
        支持模糊匹配，如 "zhongg" 匹配 "zhongguo" -> "中国"
        """
        results = self.search_prefix(prefix)
        # 按拼音长度排序，优先返回更精确的匹配
        results.sort(key=lambda x: (abs(len(x[0]) - len(prefix)), len(x[0])))
        return results[:limit]

    def get_stats(self) -> Dict:
        """获取词组词典统计信息"""
        return {
            "total_phrases": len(self.phrase_dict),
        }


# 全局引擎实例
_phrase_engine: Optional[PhraseEngine] = None


def get_phrase_engine() -> PhraseEngine:
    """获取词组引擎单例"""
    global _phrase_engine
    if _phrase_engine is None:
        _phrase_engine = PhraseEngine()
    return _phrase_engine
