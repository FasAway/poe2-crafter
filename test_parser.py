import unittest
from pathlib import Path
from item_parser import check_condition, parse_item, parse_stat


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.item = parse_item(Path(__file__).with_name('sample_item.txt').read_text(encoding='utf-8'))

    def test_header_and_groups(self):
        self.assertEqual((self.item.item_class, self.item.name, self.item.base, self.item.item_level),
                         ('長矛', '腐化 刀鋒', '展翼長矛', 83))
        self.assertEqual(len(self.item.modifiers), 6)
        self.assertEqual([m.kind for m in self.item.modifiers], ['prefix'] * 3 + ['suffix'] * 3)
        self.assertTrue(self.item.corrupted)
        self.assertEqual(self.item.warnings, [])

    def test_actual_damage_and_range(self):
        self.assertEqual([r.value for r in self.item.modifiers[0].stats[0].rolls], ['2', '5'])
        self.assertEqual([r.value for r in self.item.modifiers[1].stats[0].rolls], ['1', '4'])
        self.assertEqual(self.item.modifiers[0].stats[0].rolls[0].low, '1')

    def test_compound_modifier_preserved(self):
        self.assertEqual(len(self.item.modifiers[2].stats), 2)
        self.assertTrue(self.item.modifiers[2].crafted)
        self.assertTrue(self.item.modifiers[0].fractured)
        self.assertEqual(self.item.modifiers[2].stats[0].rolls[0].value, '+422')

    def test_tier_and_actual_value(self):
        yes = check_condition(self.item, keyword='攻擊速度', tier=1, minimum='28')
        self.assertEqual(yes['status'], 'matched')
        self.assertEqual(len(yes['matches']), 1)
        self.assertEqual(check_condition(self.item, keyword='攻擊速度', tier=1, minimum='29', kind='suffix')['status'], 'not_matched')
        self.assertEqual(check_condition(self.item, keyword='命中值', minimum='425')['status'], 'not_matched')

    def test_non_mod_stats_not_matched(self):
        for keyword in ('物理傷害', '每秒攻擊次數', '賦予技能'):
            self.assertEqual(check_condition(self.item, keyword=keyword)['status'], 'not_matched')
        self.assertEqual(check_condition(self.item, keyword='攻擊速度', minimum='18', kind='prefix')['status'], 'not_matched')

    def test_missing_values_and_ambiguous_range(self):
        self.assertEqual(check_condition(self.item, keyword='火焰傷害', minimum='3')['status'], 'unknown')
        self.assertEqual(check_condition(self.item, keyword='火焰傷害', minimum='3', value_index=0)['status'], 'not_matched')
        self.assertEqual(check_condition(self.item, keyword='火焰傷害', minimum='3', value_index=1)['status'], 'matched')
        self.assertEqual(check_condition(self.item, keyword='無法變動的值', tier=1)['status'], 'unknown')

    def test_decimal_and_negative_actual_values(self):
        stat = parse_stat('增加2.62(2.50-2.70)%速度，-10(-15--5)需求')
        self.assertEqual([r.value for r in stat.rolls], ['2.62', '-10'])
        self.assertEqual((stat.rolls[1].low, stat.rolls[1].high), ('-15', '-5'))

    def test_plain_clipboard_is_unknown(self):
        item = parse_item('稀有度: 稀有\n測試\n長矛\n--------\n增加28%攻擊速度')
        self.assertEqual(check_condition(item, keyword='攻擊速度')['status'], 'unknown')
        with self.assertRaises(ValueError):
            parse_item('hello')


if __name__ == '__main__':
    unittest.main()
