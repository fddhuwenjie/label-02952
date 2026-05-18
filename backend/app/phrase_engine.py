"""词组匹配引擎

使用 Trie 树数据结构实现高效的拼音前缀查找和词组匹配。
支持最长词组优先匹配和所有可能切分方案。
"""
from typing import Dict, List, Optional, Set, Tuple

from .logger import get_logger
from .phrase_dict import PHRASE_DICT

logger = get_logger("phrase_engine")


class TrieNode:
    """Trie 树节点"""

    __slots__ = ("children", "is_end", "words", "frequency")

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.is_end: bool = False
        self.words: List[Tuple[str, int]] = []
        self.frequency: int = 0

    def get_child(self, char: str) -> "TrieNode":
        if char not in self.children:
            self.children[char] = TrieNode()
        return self.children[char]


class Trie:
    """Trie 树 - 用于拼音前缀匹配"""

    def __init__(self):
        self.root = TrieNode()
        self.size = 0

    def insert(self, pinyin_str: str, word: str, frequency: int = 1) -> None:
        node = self.root
        for char in pinyin_str:
            node = node.get_child(char)
        node.is_end = True
        node.frequency += frequency
        node.words.append((word, node.frequency))
        self.size += 1

    def search(self, pinyin_str: str) -> Optional[TrieNode]:
        node = self.root
        for char in pinyin_str:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def starts_with(self, prefix: str) -> bool:
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True

    def get_all_words(self, prefix: str) -> List[Tuple[str, int]]:
        """获取指定前缀下的所有词组及其词频"""
        node = self.search(prefix)
        if node is None:
            return []
        result = []
        self._collect_words(node, result)
        return result

    def _collect_words(self, node: TrieNode, result: List[Tuple[str, int]]) -> None:
        if node.is_end:
            result.extend(node.words)
        for child in node.children.values():
            self._collect_words(child, result)


class PhraseEngine:
    """词组匹配引擎

    使用 Trie 树实现拼音前缀匹配，支持：
    - 最长词组优先匹配
    - 所有可能切分方案
    - 模糊前缀匹配
    - 词频排序
    """

    def __init__(self):
        self._trie = Trie()
        self._word_to_pinyins: Dict[str, Tuple[str, ...]] = {}
        self._pinyin_to_words: Dict[str, List[str]] = {}
        self._build_index()
        logger.info("词组引擎初始化完成，内置词组 %d 条", len(PHRASE_DICT))

    def _build_index(self) -> None:
        for word, pinyins in PHRASE_DICT.items():
            self._word_to_pinyins[word] = pinyins
            pinyin_str = "".join(pinyins)
            self._trie.insert(pinyin_str, word)
            if pinyin_str not in self._pinyin_to_words:
                self._pinyin_to_words[pinyin_str] = []
            self._pinyin_to_words[pinyin_str].append(word)

    def find_longest_match(self, pinyin_str: str) -> List[str]:
        """查找最长匹配的词组（贪心算法）

        支持模糊前缀匹配：输入前缀即可匹配到对应词组。
        例如: "zhonghuarenmingongheguo" -> ["中华人民共和国"]
        例如: "zhongg" -> ["中国"]
        """
        result = []
        i = 0
        n = len(pinyin_str)
        while i < n:
            best_len = 0
            best_word = None
            node = self._trie.root
            for j in range(i, n + 1):
                if node.is_end:
                    pinyin_substr = pinyin_str[i:j]
                    if pinyin_substr in self._pinyin_to_words:
                        if j - i > best_len:
                            best_len = j - i
                            candidates = self._pinyin_to_words[pinyin_substr]
                            best_word = candidates[0]
                if j < n:
                    char = pinyin_str[j]
                    if char in node.children:
                        node = node.children[char]
                    else:
                        break
                else:
                    break

            if best_word is None:
                best_word, best_len = self._find_fuzzy_match(pinyin_str, i)

            if best_word is not None:
                result.append(best_word)
                i += best_len
            else:
                i += 1
        return result

    def _find_fuzzy_match(self, pinyin_str: str, start: int) -> Tuple[Optional[str], int]:
        """模糊前缀匹配：从 start 位置开始查找能匹配到的最长词组"""
        prefix = pinyin_str[start:]
        if not prefix:
            return None, 0
        candidates = self.find_phrases_by_prefix(prefix)
        if not candidates:
            return None, 0
        longest_word = max(candidates, key=lambda x: len(x[0]))[0]
        pinyin_full = "".join(self._word_to_pinyins[longest_word])
        return longest_word, len(pinyin_full)

    def find_all_segmentations(self, pinyin_str: str) -> List[List[str]]:
        """查找所有可能的切分方案（动态规划）

        例如: "zhonghuarenmingongheguo" -> [
            ["中华人民共和国"],
            ["中华", "人民", "共和国"],
            ["中", "华人", "民工", "和国"],
            ...
        ]
        """
        n = len(pinyin_str)
        dp: List[Optional[List[List[str]]]] = [None] * (n + 1)
        dp[n] = [[]]

        for i in range(n - 1, -1, -1):
            results = []
            node = self._trie.root
            for j in range(i, n + 1):
                if node.is_end:
                    pinyin_substr = pinyin_str[i:j]
                    if pinyin_substr in self._pinyin_to_words and dp[j] is not None:
                        for rest in dp[j]:
                            if len([pinyin_substr] + rest) <= 20:
                                results.append([pinyin_substr] + rest)
                if j < n:
                    char = pinyin_str[j]
                    if char in node.children:
                        node = node.children[char]
                    else:
                        break
                else:
                    break
            if results:
                dp[i] = results

        if dp[0] is None:
            return []

        # 转换为汉字词组
        word_results = []
        for seg_scheme in dp[0]:
            word_scheme = []
            for pinyin_seg in seg_scheme:
                if pinyin_seg in self._pinyin_to_words:
                    word_scheme.append(self._pinyin_to_words[pinyin_seg][0])
                else:
                    word_scheme.append(pinyin_seg)
            word_results.append(word_scheme)

        # 按长度排序（最长优先），再按词频排序
        word_results.sort(key=lambda x: (-len(x), x))
        return word_results

    def find_phrases_by_prefix(self, prefix: str) -> List[Tuple[str, int]]:
        """通过前缀查找可能的词组（用于模糊匹配）

        例如: "zhongg" -> [("中国", 1), ("中华", 1), ...]
        """
        if not prefix:
            return []
        return self._trie.get_all_words(prefix)

    def get_phrase_candidates(self, pinyin_str: str, limit: int = 10) -> List[str]:
        """获取连续拼音的词组候选

        返回:
            - 最长词组优先匹配结果
            - 所有可能切分方案（按词频排序）
        """
        pinyin_str = pinyin_str.lower().strip()
        if not pinyin_str:
            return []

        result = self.find_all_segmentations(pinyin_str)
        if not result:
            return []

        # 展平切分方案为候选词组列表
        candidates = []
        for scheme in result:
            for word in scheme:
                if word not in candidates:
                    candidates.append(word)

        return candidates[:limit]

    def get_stats(self) -> dict:
        """获取引擎统计信息"""
        return {
            "phrases_count": len(PHRASE_DICT),
            "trie_nodes": self._count_nodes(self._trie.root),
            "pinyin_to_words_mappings": len(self._pinyin_to_words),
        }

    def _count_nodes(self, node: TrieNode) -> int:
        count = 1
        for child in node.children.values():
            count += self._count_nodes(child)
        return count


_engine: Optional[PhraseEngine] = None


def get_phrase_engine() -> PhraseEngine:
    """获取词组引擎单例"""
    global _engine
    if _engine is None:
        _engine = PhraseEngine()
    return _engine
