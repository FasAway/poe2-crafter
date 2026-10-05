"""Regression: equipment-only clipboard client must still reach crafting.

All Windows input is mocked; this test sends no mouse or keyboard events.
"""
import unittest
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from engine import Cancelled, Condition, Crafter
from windows_io import WindowsAdapter


class EquipmentOnlyClipboardTests(unittest.TestCase):
    def test_uncopyable_currency_still_crafts_and_verifies_equipment(self):
        sample = Path(__file__).with_name('sample_item.txt').read_text(encoding='utf-8')
        before = sample.replace('已汙染', '').replace('增加28(26-28)', '增加26(26-28)')
        after = before.replace('增加26(26-28)', '增加28(26-28)')
        adapter = WindowsAdapter()
        adapter.continuous = False
        adapter.guard = Mock()
        adapter.move = Mock()
        adapter.wait = Mock()
        adapter.click = Mock()
        adapter.release = Mock()

        def equipment_only(name, stop):
            if name != '装备':
                raise AssertionError('本客户端不支持复制通货')
            return next(texts)

        texts = iter([before, after])
        adapter.copy_at = Mock(side_effect=equipment_only)
        with patch('windows_io.down', return_value=False):
            result = Crafter(adapter, lambda _: None).run(
                [Condition('攻擊速度', tier=1, minimum='28', kind='suffix')], limit=1)
        self.assertEqual(result, 'matched')
        self.assertEqual([call.args[0] for call in adapter.copy_at.call_args_list], ['装备', '装备'])
        self.assertEqual([call.args[0] for call in adapter.click.call_args_list], ['right', 'left'])
        adapter.release.assert_called_once()


class ContinuousCurrencyTests(unittest.TestCase):
    def setUp(self):
        self.sample = Path(__file__).with_name('sample_item.txt').read_text(encoding='utf-8').replace('已汙染', '')
        self.adapter = WindowsAdapter()
        self.adapter.guard = Mock()
        self.adapter.send = Mock()
        self.adapter.move = Mock()
        self.adapter.click = Mock()
        self.adapter.wait = Mock(side_effect=self.wait)
        self.input_patch = patch('windows_io.u.SendInput', return_value=1)
        self.down_patch = patch('windows_io.down', side_effect=lambda vk: vk in self.adapter.held_keys)
        self.input_patch.start()
        self.down_patch.start()
        self.addCleanup(self.input_patch.stop)
        self.addCleanup(self.down_patch.stop)

    @staticmethod
    def wait(seconds, stop):
        if stop.is_set():
            raise Cancelled()

    def test_two_applications_select_currency_once_and_stop_at_target(self):
        self.adapter.copy_at = Mock(side_effect=[
            self.sample.replace('增加28(26-28)', '增加24(26-28)'),
            self.sample.replace('增加28(26-28)', '增加26(26-28)'), self.sample])
        crafter = Crafter(self.adapter, lambda _: None)
        result = crafter.run([Condition('攻擊速度', tier=1, minimum='28', kind='suffix')], 10)
        self.assertEqual(result, 'matched')
        self.assertEqual(crafter.attempts, 2)
        self.assertEqual([call.args[0] for call in self.adapter.click.call_args_list], ['right', 'left', 'left'])
        self.assertEqual([call.args[0] for call in self.adapter.copy_at.call_args_list], ['装备'] * 3)
        self.assertEqual(self.adapter.held_keys, set())
        self.assertFalse(self.adapter.currency_selected)

    def test_equipment_copy_releases_ctrl_c_but_keeps_shift(self):
        self.adapter.held_keys.add(0x10)
        with patch('windows_io.u.GetClipboardSequenceNumber', side_effect=[100, 101]), \
                patch('windows_io.clipboard', return_value=self.sample):
            text = self.adapter.copy_item(threading.Event())
        self.assertEqual(text, self.sample)
        self.assertEqual(self.adapter.held_keys, {0x10})

    def test_no_change_releases_shift_and_does_not_click_again(self):
        self.adapter.copy_at = Mock(side_effect=[self.sample, self.sample])
        with self.assertRaisesRegex(ValueError, '未变化'):
            Crafter(self.adapter, lambda _: None).run([Condition('最大生命')])
        self.assertEqual([call.args[0] for call in self.adapter.click.call_args_list], ['right', 'left'])
        self.assertEqual(self.adapter.held_keys, set())
        self.assertFalse(self.adapter.currency_selected)

    def test_copy_failure_releases_shift(self):
        self.adapter.copy_at = Mock(side_effect=[self.sample, ValueError('剪贴板未更新')])
        with self.assertRaisesRegex(ValueError, '剪贴板'):
            Crafter(self.adapter, lambda _: None).run([Condition('最大生命')])
        self.assertEqual(self.adapter.held_keys, set())
        self.assertFalse(self.adapter.currency_selected)

    def test_stop_after_selection_prevents_application_and_releases_shift(self):
        self.adapter.copy_at = Mock(return_value=self.sample)
        crafter = Crafter(self.adapter, lambda _: None)
        self.adapter.click.side_effect = lambda button, stop: stop.set()
        self.assertEqual(crafter.run([Condition('最大生命')]), 'cancelled')
        self.assertEqual([call.args[0] for call in self.adapter.click.call_args_list], ['right'])
        self.assertEqual(self.adapter.held_keys, set())
        self.assertFalse(self.adapter.currency_selected)


if __name__ == '__main__':
    unittest.main()
