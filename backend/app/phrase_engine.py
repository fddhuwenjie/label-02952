"""智能词组联想引擎

基于 Trie 树实现高效前缀查找，支持：
- 最长词组优先匹配
- 所有可能切分方案
- 模糊前缀匹配（如 zhongg 匹配 zhongguo -> 中国）
- 按词频排序
"""
from typing import Dict, List, Optional, Tuple

from .logger import get_logger
from .phrase_dict import PHRASE_DICT

logger = get_logger("phrase_engine")


class TrieNode:
    __slots__ = ("children", "is_end", "phrases")

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.is_end: bool = False
        self.phrases: List[Tuple[str, int]] = []


class PhraseTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, pinyin: str, phrases: List[Tuple[str, int]]) -> None:
        node = self.root
        for ch in pinyin:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
        node.phrases = sorted(phrases, key=lambda x: -x[1])

    def search_exact(self, pinyin: str) -> List[Tuple[str, int]]:
        node = self._find_node(pinyin)
        if node is None or not node.is_end:
            return []
        return node.phrases

    def prefix_search(self, prefix: str) -> List[Tuple[str, List[Tuple[str, int]]]]:
        node = self._find_node(prefix)
        if node is None:
            return []
        results: List[Tuple[str, List[Tuple[str, int]]]] = []
        self._collect(node, prefix, results)
        return results

    def _find_node(self, prefix: str) -> Optional[TrieNode]:
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def _collect(
        self,
        node: TrieNode,
        current: str,
        results: List[Tuple[str, List[Tuple[str, int]]]],
    ) -> None:
        if node.is_end:
            results.append((current, node.phrases))
        for ch, child in node.children.items():
            self._collect(child, current + ch, results)

    def longest_match(self, pinyin: str) -> Optional[Tuple[str, List[Tuple[str, int]]]]:
        node = self.root
        last_match: Optional[Tuple[str, List[Tuple[str, int]]]] = None
        current = ""
        for ch in pinyin:
            if ch not in node.children:
                break
            current += ch
            node = node.children[ch]
            if node.is_end:
                last_match = (current, node.phrases)
        return last_match


class PhraseEngine:
    def __init__(self):
        self._trie = PhraseTrie()
        self._all_pinyins: set = set()
        self._build_trie()
        logger.info(
            "词组引擎初始化完成，加载 %d 条拼音词组",
            len(self._all_pinyins),
        )

    def _build_trie(self) -> None:
        for pinyin, phrases in PHRASE_DICT.items():
            pinyin_lower = pinyin.lower()
            self._trie.insert(pinyin_lower, phrases)
            self._all_pinyins.add(pinyin_lower)

    def match_phrases(self, pinyin: str) -> List[Tuple[str, int]]:
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return []
        exact = self._trie.search_exact(pinyin)
        if exact:
            return exact
        prefix_results = self._trie.prefix_search(pinyin)
        if not prefix_results:
            return []
        all_phrases: List[Tuple[str, int]] = []
        seen: set = set()
        for _, phrases in prefix_results:
            for phrase, freq in phrases:
                if phrase not in seen:
                    seen.add(phrase)
                    all_phrases.append((phrase, freq))
        all_phrases.sort(key=lambda x: -x[1])
        return all_phrases

    def longest_phrase_match(self, pinyin: str) -> Optional[Tuple[str, List[Tuple[str, int]]]]:
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return None
        return self._trie.longest_match(pinyin)

    def segment_phrases(self, pinyin: str) -> List[List[Tuple[str, List[Tuple[str, int]]]]]:
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return []
        n = len(pinyin)
        dp: List[Optional[List[List[Tuple[str, List[Tuple[str, int]]]]]]] = [None] * (n + 1)
        dp[n] = [[]]

        for i in range(n - 1, -1, -1):
            results = []
            for j in range(i + 1, n + 1):
                substr = pinyin[i:j]
                exact = self._trie.search_exact(substr)
                if exact and dp[j] is not None:
                    for rest in dp[j]:
                        if len([(substr, exact)] + rest) <= 20:
                            results.append([(substr, exact)] + rest)
            if results:
                dp[i] = results

        if dp[0] is None:
            return []
        dp[0].sort(key=lambda seg: len(seg))
        return dp[0]

    def query(self, pinyin: str, limit: int = 10) -> dict:
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return {"phrases": [], "alternatives": []}

        phrases = self.match_phrases(pinyin)[:limit]

        alternatives_raw = self.segment_phrases(pinyin)

        longest_result = self.longest_phrase_match(pinyin)

        alternatives: List[dict] = []
        seen_keys: set = set()

        if longest_result:
            longest_pinyin, longest_phrases = longest_result
            key = "longest|" + longest_pinyin
            seen_keys.add(key)
            alternatives.append(
                {
                    "type": "longest",
                    "text": longest_phrases[0][0] if longest_phrases else "",
                    "segments": [
                        {"pinyin": longest_pinyin, "phrases": longest_phrases[:limit]}
                    ],
                }
            )

        for seg_list in alternatives_raw:
            seg_dicts = []
            text_parts = []
            for seg_pinyin, seg_phrases in seg_list:
                top_phrase = seg_phrases[0][0] if seg_phrases else seg_pinyin
                text_parts.append(top_phrase)
                seg_dicts.append(
                    {
                        "pinyin": seg_pinyin,
                        "phrases": seg_phrases[:limit],
                    }
                )
            key = "|".join(s["pinyin"] for s in seg_dicts)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            total_freq = 0
            for _, seg_phrases in seg_list:
                if seg_phrases:
                    total_freq += seg_phrases[0][1]

            alternatives.append(
                {
                    "type": "segmentation",
                    "text": "".join(text_parts),
                    "segments": seg_dicts,
                    "total_freq": total_freq,
                }
            )

        type_order = {"longest": 0, "segmentation": 1}
        alternatives.sort(
            key=lambda a: (type_order.get(a.get("type", ""), 2), -a.get("total_freq", 0), len(a.get("segments", [])))
        )

        return {"phrases": phrases, "alternatives": alternatives}


_phrase_engine: Optional[PhraseEngine] = None


def get_phrase_engine() -> PhraseEngine:
    global _phrase_engine
    if _phrase_engine is None:
        _phrase_engine = PhraseEngine()
    return _phrase_engine
