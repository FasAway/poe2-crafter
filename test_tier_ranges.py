import unittest
from pathlib import Path
from engine import Condition, evaluate, parse_tier_spec
from item_parser import check_condition, parse_item


class TierRangeTests(unittest.TestCase):
    def setUp(self):
        self.text = Path(__file__).with_name('sample_item.txt').read_text(encoding='utf-8')

    def test_input_syntax_and_legacy_single_tier(self):
        for value in ('1-3', 'T1-T3', ' t1 - t3 ', '1～3', '1至3'):
            self.assertEqual(parse_tier_spec(value), (1, 3))
        self.assertEqual(parse_tier_spec('3'), (3, None))
        self.assertEqual(parse_tier_spec('T3'), (3, None))
        self.assertEqual(parse_tier_spec(''), (None, None))

    def test_invalid_ranges_rejected(self):
        for value in ('0-3', '3-1', '1,2,3', '1-3-5', '-1', '1.5', 'T'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_tier_spec(value)
        with self.assertRaises(ValueError):
            check_condition(parse_item(self.text), keyword='攻擊速度', tier_max=3)

    def test_each_accepted_tier_and_first_rejected_tier(self):
        rule = Condition('攻擊速度', tier=1, tier_max=3, kind='suffix')
        for tier, expected in [(1, 'matched'), (2, 'matched'), (3, 'matched'), (4, 'not_matched')]:
            item = parse_item(self.text.replace('階層：1)', f'階層：{tier})'))
            with self.subTest(tier=tier):
                self.assertEqual(evaluate(item, [rule])[0], expected)

    def test_range_and_value_must_match_same_modifier(self):
        item = parse_item(self.text.replace('階層：1)', '階層：3)'))
        self.assertEqual(evaluate(item, [Condition('攻擊速度', tier=1, tier_max=3, minimum='28', kind='suffix')])[0], 'matched')
        self.assertEqual(evaluate(item, [Condition('攻擊速度', tier=1, tier_max=3, minimum='29', kind='suffix')])[0], 'not_matched')
        self.assertEqual(evaluate(item, [Condition('攻擊速度', tier=1, kind='suffix')])[0], 'not_matched')

    def test_unknown_tier_stays_unknown(self):
        item = parse_item(self.text.replace('(階層：1)', ''))
        self.assertEqual(evaluate(item, [Condition('攻擊速度', tier=1, tier_max=3, kind='suffix')])[0], 'unknown')


if __name__ == '__main__':
    unittest.main()
