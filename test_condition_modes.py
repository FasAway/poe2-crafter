import unittest

from engine import Condition, Crafter, evaluate
from item_parser import parse_item
from test_engine import FakeAdapter, SAMPLE


class ConditionModeTests(unittest.TestCase):
    def test_one_of_three_is_enough_only_in_any_mode(self):
        item = parse_item(SAMPLE)
        rules = [Condition('最大生命'), Condition('攻擊速度', tier=1, minimum='28', kind='suffix'), Condition('冰冷抗性')]
        self.assertEqual(evaluate(item, rules)[0], 'not_matched')
        self.assertEqual(evaluate(item, rules, 'any')[0], 'matched')

    def test_any_still_requires_tier_and_value_on_same_modifier(self):
        item = parse_item(SAMPLE)
        rules = [Condition('攻擊速度', tier=1, minimum='29', kind='suffix'), Condition('最大生命')]
        self.assertEqual(evaluate(item, rules, 'any')[0], 'not_matched')

    def test_unknown_without_match_prevents_spending(self):
        adapter = FakeAdapter([SAMPLE.replace('已汙染', '')])
        with self.assertRaisesRegex(ValueError, '歧义'):
            Crafter(adapter, lambda _: None).run([Condition('火焰傷害', minimum='3'), Condition('最大生命')], mode='any')
        self.assertEqual(adapter.clicks, 0)
        self.assertTrue(adapter.released)

    def test_definite_any_match_can_stop_despite_unrelated_unknown(self):
        rules = [Condition('火焰傷害', minimum='3'), Condition('攻擊速度', tier=1)]
        self.assertEqual(evaluate(parse_item(SAMPLE), rules)[0], 'unknown')
        adapter = FakeAdapter([SAMPLE])
        self.assertEqual(Crafter(adapter, lambda _: None).run(rules, mode='any'), 'matched')
        self.assertEqual(adapter.clicks, 0)
        self.assertTrue(adapter.released)

    def test_stops_immediately_after_first_new_match(self):
        before = SAMPLE.replace('已汙染', '').replace('增加28(26-28)', '增加26(26-28)')
        after = before.replace('增加26(26-28)', '增加28(26-28)')
        adapter = FakeAdapter([before, after])
        logs = []
        rules = [Condition('最大生命'), Condition('攻擊速度', tier=1, minimum='28', kind='suffix'), Condition('冰冷抗性')]
        self.assertEqual(Crafter(adapter, logs.append).run(rules, 5, 'any'), 'matched')
        self.assertEqual(adapter.clicks, 1)
        self.assertTrue(adapter.released)
        self.assertTrue(any('至少一个条件' in line for line in logs))

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(parse_item(SAMPLE), [Condition('攻擊速度')], 'invalid')


if __name__ == '__main__':
    unittest.main()
