import threading
import unittest
from unittest.mock import Mock, patch

from engine import Cancelled
from timing import TimingSettings
from windows_io import WindowsAdapter


class TimingTests(unittest.TestCase):
    def test_higher_speed_reduces_waits_without_removing_input_hold(self):
        original = TimingSettings(speed=1)
        faster = TimingSettings(speed=5)
        for phase in ('move', 'select', 'shift', 'click', 'hover', 'key', 'settle'):
            self.assertGreater(faster.seconds(phase), 0)
            self.assertLess(faster.seconds(phase), original.seconds(phase))
        self.assertGreaterEqual(faster.seconds('click'), 0.020)
        self.assertGreaterEqual(faster.seconds('key'), 0.015)
        self.assertGreaterEqual(faster.seconds('settle'), 0.100)

    def test_random_bounds_and_disabled_mode(self):
        settings = TimingSettings(speed=5, random_min_ms=70, random_max_ms=130)
        with patch('timing.random.uniform', return_value=95) as rng:
            self.assertEqual(settings.random_seconds(), 0.095)
            rng.assert_called_once_with(70, 130)
        with patch('timing.random.uniform') as rng:
            self.assertEqual(TimingSettings(random_enabled=False).random_seconds(), 0)
            rng.assert_not_called()

    def test_reject_invalid_and_nonfinite_settings(self):
        for kwargs in ({'speed': 0}, {'speed': 6}, {'speed': float('nan')},
                       {'speed': float('inf')}, {'random_min_ms': -1},
                       {'random_max_ms': float('inf')}, {'random_min_ms': float('nan')},
                       {'random_min_ms': 200, 'random_max_ms': 100}, {'random_max_ms': 10001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                TimingSettings(**kwargs)

    def test_jitter_applied_once_per_application_not_scaled(self):
        adapter = WindowsAdapter()
        adapter.timing = TimingSettings(speed=5, random_min_ms=120, random_max_ms=120)
        adapter.guard = Mock()
        adapter.move = Mock()
        adapter.wait = Mock()
        adapter.click = Mock()
        adapter.send = Mock()
        stop = threading.Event()
        with patch('windows_io.down', side_effect=lambda vk: vk in adapter.held_keys), \
                patch('windows_io.u.SendInput', return_value=1):
            adapter.use_chaos(stop)
            adapter.wait.reset_mock()
            adapter.use_chaos(stop)
            durations = [call.args[0] for call in adapter.wait.call_args_list]
            self.assertEqual(durations[0], 0.120)
            self.assertEqual(durations.count(0.120), 1)
            self.assertIn(adapter.timing.seconds('settle'), durations)
            adapter.release()

    def test_random_wait_cancelled_before_any_click(self):
        adapter = WindowsAdapter()
        adapter.guard = Mock()
        adapter.move = Mock()
        adapter.click = Mock()
        adapter.send = Mock()
        adapter.wait = Mock(side_effect=Cancelled())
        with patch('windows_io.down', return_value=False), self.assertRaises(Cancelled):
            adapter.use_chaos(threading.Event())
        adapter.click.assert_not_called()
        adapter.send.assert_not_called()

    def test_stop_interrupts_long_wait(self):
        adapter = WindowsAdapter()
        adapter.guard = Mock()
        stop = threading.Event()
        stop.set()
        with patch('windows_io.time.sleep') as sleep, self.assertRaises(Cancelled):
            adapter.wait(10, stop)
        sleep.assert_not_called()

    def test_fast_copy_still_rejects_unchanged_clipboard_sequence(self):
        adapter = WindowsAdapter()
        adapter.timing = TimingSettings(speed=5, random_enabled=False)
        adapter.move = Mock()
        adapter.wait = Mock()
        adapter.send = Mock()
        with patch('windows_io.u.GetClipboardSequenceNumber', return_value=100), \
                patch('windows_io.time.monotonic', side_effect=[0, 0, 3]), \
                patch('windows_io.u.SendInput', return_value=1), \
                patch('windows_io.clipboard', return_value='stale equipment') as read:
            with self.assertRaisesRegex(ValueError, '剪贴板没有更新'):
                adapter.copy_item(threading.Event())
            read.assert_not_called()
        self.assertEqual(adapter.held_keys, set())


if __name__ == '__main__':
    unittest.main()
