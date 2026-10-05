import unittest
from pathlib import Path
from engine import Condition, Crafter

SAMPLE = Path(__file__).with_name('sample_item.txt').read_text(encoding='utf-8')


class FakeAdapter:
    def __init__(self, texts, fail_guard=False):
        self.texts = iter(texts)
        self.fail_guard = fail_guard
        self.clicks = 0
        self.released = False

    def guard(self):
        if self.fail_guard:
            raise ValueError('失去焦点')

    def copy_item(self, stop):
        return next(self.texts)

    def use_chaos(self, stop):
        self.clicks += 1

    def release(self):
        self.released = True


class EngineTests(unittest.TestCase):
    def test_initial_match_does_not_spend(self):
        adapter = FakeAdapter([SAMPLE])
        result = Crafter(adapter, lambda _: None).run([Condition('攻擊速度', tier=1, minimum='28')])
        self.assertEqual(result, 'matched')
        self.assertEqual(adapter.clicks, 0)
        self.assertTrue(adapter.released)

    def test_corrupted_item_not_clicked(self):
        adapter = FakeAdapter([SAMPLE])
        with self.assertRaisesRegex(ValueError, '污染'):
            Crafter(adapter, lambda _: None).run([Condition('最大生命', minimum='100')])
        self.assertEqual(adapter.clicks, 0)

    def test_change_then_match_at_last_allowed_attempt(self):
        before = SAMPLE.replace('已汙染', '').replace('增加28(26-28)', '增加26(26-28)')
        after = before.replace('增加26(26-28)', '增加28(26-28)')
        adapter = FakeAdapter([before, after])
        self.assertEqual(Crafter(adapter, lambda _: None).run([Condition('攻擊速度', tier=1, minimum='28', kind='suffix')], 1), 'matched')
        self.assertEqual(adapter.clicks, 1)

    def test_unchanged_result_stops_without_extra_click(self):
        text = SAMPLE.replace('已汙染', '')
        adapter = FakeAdapter([text, text])
        with self.assertRaisesRegex(ValueError, '未变化'):
            Crafter(adapter, lambda _: None).run([Condition('最大生命', minimum='100')])
        self.assertEqual(adapter.clicks, 1)
        self.assertTrue(adapter.released)

    def test_switch_item_stops(self):
        text = SAMPLE.replace('已汙染', '')
        adapter = FakeAdapter([text, text.replace('展翼長矛', '另一個基底')])
        with self.assertRaisesRegex(ValueError, '基底'):
            Crafter(adapter, lambda _: None).run([Condition('最大生命')])
        self.assertEqual(adapter.clicks, 1)

    def test_unknown_condition_not_clicked(self):
        adapter = FakeAdapter([SAMPLE.replace('已汙染', '')])
        with self.assertRaisesRegex(ValueError, '歧义'):
            Crafter(adapter, lambda _: None).run([Condition('火焰傷害', minimum='3')])
        self.assertEqual(adapter.clicks, 0)

    def test_focus_lost_and_cancelled_not_clicked(self):
        adapter = FakeAdapter([SAMPLE], fail_guard=True)
        with self.assertRaisesRegex(ValueError, '焦点'):
            Crafter(adapter, lambda _: None).run([Condition('最大生命')])
        self.assertEqual(adapter.clicks, 0)
        adapter = FakeAdapter([SAMPLE])
        crafter = Crafter(adapter, lambda _: None)
        crafter.stop.set()
        self.assertEqual(crafter.run([Condition('最大生命')]), 'cancelled')
        self.assertEqual(adapter.clicks, 0)


if __name__ == '__main__':
    unittest.main()
