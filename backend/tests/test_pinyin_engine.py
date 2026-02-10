"""拼音引擎单元测试"""
import unittest
from app.pinyin_engine import PinyinEngine, get_engine


class TestPinyinEngine(unittest.TestCase):
    """拼音引擎测试类"""

    def setUp(self):
        """测试前初始化"""
        self.engine = PinyinEngine()

    def test_get_candidates_exact_match(self):
        """测试精确匹配"""
        candidates = self.engine.get_candidates("ni")
        self.assertIn("你", candidates)
        self.assertGreater(len(candidates), 0)

    def test_get_candidates_prefix_match(self):
        """测试前缀匹配"""
        candidates = self.engine.get_candidates("zho")
        self.assertGreater(len(candidates), 0)

    def test_get_candidates_empty_input(self):
        """测试空输入"""
        candidates = self.engine.get_candidates("")
        self.assertEqual(candidates, [])

    def test_get_candidates_invalid_pinyin(self):
        """测试无效拼音"""
        candidates = self.engine.get_candidates("xyz")
        self.assertEqual(candidates, [])

    def test_get_candidates_limit(self):
        """测试候选数量限制"""
        candidates = self.engine.get_candidates("shi", limit=3)
        self.assertLessEqual(len(candidates), 3)

    def test_get_all_pinyins(self):
        """测试获取所有拼音"""
        pinyins = self.engine.get_all_pinyins()
        self.assertGreater(len(pinyins), 200)
        self.assertIn("zhong", pinyins)

    def test_search_pinyin(self):
        """测试拼音搜索"""
        results = self.engine.search_pinyin("zh")
        self.assertIn("zhong", results)
        self.assertIn("zhi", results)

    def test_search_pinyin_empty(self):
        """测试空搜索"""
        results = self.engine.search_pinyin("")
        self.assertEqual(results, [])

    def test_convert_sentence(self):
        """测试句子转换"""
        result = self.engine.convert_sentence(["ni", "hao"])
        self.assertEqual(len(result), 2)
        self.assertIn("你", result[0])
        self.assertIn("好", result[1])

    def test_convert_sentence_invalid_pinyin(self):
        """测试包含无效拼音的句子"""
        result = self.engine.convert_sentence(["ni", "xyz"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], ["xyz"])

    def test_get_engine_singleton(self):
        """测试单例模式"""
        engine1 = get_engine()
        engine2 = get_engine()
        self.assertIs(engine1, engine2)

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        candidates_lower = self.engine.get_candidates("ni")
        candidates_upper = self.engine.get_candidates("NI")
        self.assertEqual(candidates_lower, candidates_upper)


if __name__ == "__main__":
    unittest.main()
