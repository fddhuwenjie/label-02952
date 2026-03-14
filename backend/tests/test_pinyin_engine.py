"""拼音引擎单元测试"""
import unittest

from app.config import reset_config
from app.exceptions import InvalidLimitError, InvalidPinyinError
from app.pinyin_engine import PinyinEngine, get_engine


class TestPinyinEngine(unittest.TestCase):

    def setUp(self):
        reset_config()
        self.engine = PinyinEngine()

    def test_get_candidates_exact_match(self):
        candidates = self.engine.get_candidates("ni")
        self.assertIn("你", candidates)
        self.assertGreater(len(candidates), 0)

    def test_get_candidates_prefix_match(self):
        candidates = self.engine.get_candidates("zho")
        self.assertGreater(len(candidates), 0)

    def test_get_candidates_empty_input(self):
        self.assertEqual(self.engine.get_candidates(""), [])

    def test_get_candidates_invalid_pinyin(self):
        self.assertEqual(self.engine.get_candidates("xyz"), [])

    def test_get_candidates_limit(self):
        candidates = self.engine.get_candidates("shi", limit=3)
        self.assertLessEqual(len(candidates), 3)

    def test_get_all_pinyins(self):
        pinyins = self.engine.get_all_pinyins()
        self.assertGreater(len(pinyins), 200)
        self.assertIn("zhong", pinyins)

    def test_search_pinyin(self):
        results = self.engine.search_pinyin("zh")
        self.assertIn("zhong", results)

    def test_search_pinyin_empty(self):
        self.assertEqual(self.engine.search_pinyin(""), [])

    def test_convert_sentence(self):
        result = self.engine.convert_sentence(["ni", "hao"])
        self.assertEqual(len(result), 2)
        self.assertIn("你", result[0])

    def test_convert_sentence_invalid(self):
        result = self.engine.convert_sentence(["ni", "xyz"])
        self.assertEqual(result[1], ["xyz"])

    def test_singleton(self):
        self.assertIs(get_engine(), get_engine())

    def test_case_insensitive(self):
        self.assertEqual(
            self.engine.get_candidates("ni"),
            self.engine.get_candidates("NI"),
        )

    def test_segment_continuous(self):
        result = self.engine.get_candidates_continuous("nihao")
        self.assertEqual(result["segments"], ["ni", "hao"])

    def test_invalid_limit_zero(self):
        with self.assertRaises(InvalidLimitError):
            self.engine.get_candidates("ni", limit=0)

    def test_invalid_limit_negative(self):
        with self.assertRaises(InvalidLimitError):
            self.engine.get_candidates("ni", limit=-1)

    def test_invalid_limit_too_large(self):
        with self.assertRaises(InvalidLimitError):
            self.engine.get_candidates("ni", limit=999)

    def test_special_chars_rejected(self):
        with self.assertRaises(InvalidPinyinError):
            self.engine.get_candidates("ni123")

    def test_too_long_input(self):
        with self.assertRaises(InvalidPinyinError):
            self.engine.get_candidates("a" * 100)

    def test_add_user_word(self):
        self.engine.add_user_word("test", "测试词")
        self.assertIn("测试词", self.engine.get_candidates("test"))

    def test_add_user_word_empty_pinyin(self):
        with self.assertRaises(InvalidPinyinError):
            self.engine.add_user_word("", "词")

    def test_add_user_word_empty_word(self):
        with self.assertRaises(InvalidPinyinError):
            self.engine.add_user_word("test", "")

    def test_frequency_sorting(self):
        self.engine.add_user_word("ce", "测A")
        self.engine.add_user_word("ce", "测B")
        self.engine.record_selection("ce", "测B")
        self.engine.record_selection("ce", "测B")
        candidates = self.engine.get_candidates("ce")
        self.assertLess(candidates.index("测B"), candidates.index("测A"))

    def test_get_stats(self):
        stats = self.engine.get_stats()
        self.assertIn("builtin_pinyins", stats)
        self.assertGreater(stats["builtin_pinyins"], 200)


if __name__ == "__main__":
    unittest.main()
