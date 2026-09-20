"""鼠标键盘模拟模块 - 模拟游戏操作（pydirectinput + pynput，无pyautogui依赖）"""

import time
import random
import sys
from typing import Tuple

# 优先使用 pydirectinput（DirectX游戏兼容）
try:
    import pydirectinput
    pydirectinput.FAILSAFE = False
    pydirectinput.PAUSE = 0.01
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    PYDIRECTINPUT_AVAILABLE = False

# pynput 作为兜底方案
try:
    from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class InputSimulator:
    """输入模拟器"""

    def __init__(self):
        """初始化输入模拟器"""
        if PYDIRECTINPUT_AVAILABLE:
            self.method = 'pydirectinput'
        elif PYNPUT_AVAILABLE:
            self.method = 'pynput'
        else:
            self.method = 'none'
        print(f"[输入模拟] 使用方法: {self.method}")

        if PYNPUT_AVAILABLE:
            self._mouse = pynput_mouse.Controller()
            self._keyboard = pynput_keyboard.Controller()
        else:
            self._mouse = None
            self._keyboard = None

    # ---------- 坐标 ----------

    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标位置"""
        try:
            if PYNPUT_AVAILABLE and self._mouse:
                pos = self._mouse.position
                return (int(pos.x), int(pos.y))
            if PYDIRECTINPUT_AVAILABLE:
                pos = pydirectinput.position()
                return (pos[0], pos[1])
        except Exception:
            pass
        return (0, 0)

    # ---------- 鼠标 ----------

    def move_to(self, x: int, y: int, jitter: int = 0) -> bool:
        """移动鼠标到指定位置"""
        try:
            actual_x = max(0, x + (random.randint(-jitter, jitter) if jitter else 0))
            actual_y = max(0, y + (random.randint(-jitter, jitter) if jitter else 0))

            if self.method == 'pydirectinput':
                pydirectinput.moveTo(actual_x, actual_y)
            elif self.method == 'pynput':
                self._mouse.position = (actual_x, actual_y)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 移动鼠标失败: {e}")
            return False

    def left_click(self, clicks: int = 1) -> bool:
        """左键点击"""
        try:
            if self.method == 'pydirectinput':
                pydirectinput.click(buttons='left', clicks=clicks)
            elif self.method == 'pynput':
                for _ in range(clicks):
                    self._mouse.click(pynput_mouse.Button.left)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 左键点击失败: {e}")
            return False

    def right_click(self, clicks: int = 1) -> bool:
        """右键点击"""
        try:
            if self.method == 'pydirectinput':
                pydirectinput.rightClick(clicks=clicks)
            elif self.method == 'pynput':
                for _ in range(clicks):
                    self._mouse.click(pynput_mouse.Button.right)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 右键点击失败: {e}")
            return False

    # ---------- 键盘 ----------

    def key_down(self, key: str) -> bool:
        """按下按键"""
        try:
            if self.method == 'pydirectinput':
                pydirectinput.keyDown(key)
            elif self.method == 'pynput':
                self._keyboard.press(self._pynput_key(key))
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 按下按键失败: {e}")
            return False

    def key_up(self, key: str) -> bool:
        """松开按键"""
        try:
            if self.method == 'pydirectinput':
                pydirectinput.keyUp(key)
            elif self.method == 'pynput':
                self._keyboard.release(self._pynput_key(key))
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 松开按键失败: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """按键"""
        return self.key_down(key) and self.key_up(key)

    def hotkey(self, *keys) -> bool:
        """组合键"""
        try:
            if self.method == 'pydirectinput':
                pydirectinput.hotkey(*keys)
            elif self.method == 'pynput':
                converted = [self._pynput_key(k) for k in keys]
                for k in converted:
                    self._keyboard.press(k)
                for k in reversed(converted):
                    self._keyboard.release(k)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 组合键失败: {e}")
            return False

    @staticmethod
    def _pynput_key(key: str):
        """将键名转换为pynput按键对象"""
        special = {
            'shift': pynput_keyboard.Key.shift,
            'lshift': pynput_keyboard.Key.shift_l,
            'rshift': pynput_keyboard.Key.shift_r,
            'ctrl': pynput_keyboard.Key.ctrl,
            'ctrl_l': pynput_keyboard.Key.ctrl_l,
            'alt': pynput_keyboard.Key.alt,
            'esc': pynput_keyboard.Key.esc,
        }
        if key.lower() in special:
            return special[key.lower()]
        return key

    def shift_click(self, x: int = None, y: int = None) -> bool:
        """Shift+左键点击"""
        try:
            if x is not None and y is not None:
                self.move_to(x, y)

            self.key_down('shift')
            time.sleep(0.05)
            self.left_click()
            time.sleep(0.05)
            self.key_up('shift')
            return True
        except Exception as e:
            print(f"[输入模拟] Shift+点击失败: {e}")
            try:
                self.key_up('shift')
            except Exception:
                pass
            return False

    def ctrl_c(self) -> bool:
        """Ctrl+C 复制"""
        return self.hotkey('ctrl', 'c')

    def random_delay(self, min_delay: float = 0.1, max_delay: float = 0.3) -> float:
        """随机延迟"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        return delay


class GameActions:
    """游戏操作"""

    def __init__(self, simulator: InputSimulator):
        """初始化游戏操作"""
        self.sim = simulator
        self.shift_held = False

    def pick_up_currency(self, currency_x: int, currency_y: int) -> bool:
        """拿起通货（右键点击）"""
        if not self.sim.move_to(currency_x, currency_y, jitter=2):
            return False
        self.sim.random_delay(0.05, 0.1)
        if not self.sim.right_click():
            return False
        self.sim.random_delay(0.1, 0.2)
        return True

    def use_currency_on_item(self, item_x: int, item_y: int) -> bool:
        """在物品上使用通货（Shift+左键点击）"""
        if not self.sim.move_to(item_x, item_y, jitter=2):
            return False
        self.sim.random_delay(0.05, 0.1)
        if not self.sim.shift_click():
            return False
        self.sim.random_delay(0.1, 0.2)
        return True

    def copy_item_info(self) -> bool:
        """复制物品信息（Ctrl+C）"""
        return self.sim.ctrl_c()

    def hover_over_item(self, item_x: int, item_y: int) -> bool:
        """鼠标悬停在物品上"""
        return self.sim.move_to(item_x, item_y, jitter=0)

    def craft_cycle(self, currency_x: int, currency_y: int,
                    item_x: int, item_y: int) -> bool:
        """执行一次洗练循环"""
        if not self.pick_up_currency(currency_x, currency_y):
            print("[洗练] 拿起通货失败")
            return False
        if not self.use_currency_on_item(item_x, item_y):
            print("[洗练] 使用通货失败")
            return False
        return True


# 测试代码
if __name__ == "__main__":
    print("输入模拟模块测试")
    print("=" * 40)

    sim = InputSimulator()
    print(f"使用方法: {sim.method}")

    pos = sim.get_mouse_position()
    print(f"当前鼠标位置: {pos}")
