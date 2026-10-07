import unittest

from engine import Condition, Crafter
from item_parser import check_condition, parse_item
from test_engine import FakeAdapter

RING = '''物品種類: 戒指
稀有度: 稀有
魔域 之輪
金光戒指
--------
需求: 等級 61
--------
物品等級: 80
--------
{ 固定詞綴 — 丟置 }
增加11(6-15)%找到的物品稀有度
--------
{ 已破裂 前綴 "算計的" — 魔力,法術 }
增加26(23-26)%法術的魔力消耗效用
{ 後綴 "專精之"(階層：3) — 法術,速度 }
增加18(16-18)%施法速度
--------
破裂之物
'''


class RingImplicitTests(unittest.TestCase):
    def test_base_implicit_is_preserved_without_warning(self):
        for marker in ('固定詞綴', '固定词缀'):
            item = parse_item(RING.replace('固定詞綴', marker))
            self.assertEqual(item.warnings, [])
            self.assertTrue(item.detailed)
            self.assertEqual(len(item.modifiers), 2)
            self.assertTrue(any('增加11(6-15)%找到的物品稀有度' in s for s in item.other_sections))
            self.assertEqual(check_condition(item, keyword='物品稀有度')['status'], 'not_matched')

    def test_suffix_tier_and_missing_unrelated_tier(self):
        item = parse_item(RING)
        self.assertTrue(item.modifiers[0].fractured)
        self.assertIsNone(item.modifiers[0].tier)
        self.assertEqual(check_condition(item, keyword='施法速度', tier=1, tier_max=3, minimum='18')['status'], 'matched')
        self.assertEqual(check_condition(item, keyword='施法速度', tier=1)['status'], 'not_matched')
        self.assertEqual(check_condition(item, keyword='魔力消耗效用', tier=1)['status'], 'unknown')

    def test_controller_accepts_ring_before_spending(self):
        adapter = FakeAdapter([RING])
        self.assertEqual(Crafter(adapter, lambda _: None).run([Condition('施法速度', tier=1, tier_max=3)]), 'matched')
        self.assertEqual(adapter.clicks, 0)
        self.assertTrue(adapter.released)

    def test_unrecognized_annotation_still_stops(self):
        item = parse_item(RING.replace('固定詞綴', '未來未知標記'))
        self.assertTrue(item.warnings)
        self.assertEqual(check_condition(item, keyword='施法速度')['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
