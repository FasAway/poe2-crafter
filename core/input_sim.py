"""鼠标键盘模拟模块 - 模拟游戏操作"""

import time
import random
import sys
from typing import Tuple, Optional

# 检查可用的输入模拟库
try:
    if sys.platform == 'win32':
        import pydirectinput
        pydirectinput.FAILSAFE = True
        pydirectinput.PAUSE = 0.01
        INPUT_METHOD = 'pydirectinput'
    else:
        raise ImportError
except ImportError:
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01
        INPUT_METHOD = 'pyautogui'
    except ImportError:
        INPUT_METHOD = 'none'


class InputSimulator:
    """输入模拟器"""
    
    def __init__(self):
        """初始化输入模拟器"""
        self.method = INPUT_METHOD
        print(f"[输入模拟] 使用方法: {self.method}")
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标位置
        
        Returns:
            (x, y) 坐标
        """
        if self.method == 'pydirectinput':
            pos = pydirectinput.position()
            return (pos[0], pos[1])
        elif self.method == 'pyautogui':
            pos = pyautogui.position()
            return (pos[0], pos[1])
        return (0, 0)
    
    def move_to(self, x: int, y: int, jitter: int = 0) -> bool:
        """移动鼠标到指定位置
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
            jitter: 随机偏移量（像素）
        
        Returns:
            是否成功
        """
        try:
            # 添加随机偏移
            actual_x = x + random.randint(-jitter, jitter) if jitter else x
            actual_y = y + random.randint(-jitter, jitter) if jitter else y
            
            # 确保坐标在有效范围内
            actual_x = max(0, actual_x)
            actual_y = max(0, actual_y)
            
            if self.method == 'pydirectinput':
                pydirectinput.moveTo(actual_x, actual_y)
            elif self.method == 'pyautogui':
                pyautogui.moveTo(actual_x, actual_y)
            else:
                return False
            
            return True
        except Exception as e:
            print(f"[输入模拟] 移动鼠标失败: {e}")
            return False
    
    def left_click(self, clicks: int = 1) -> bool:
        """左键点击
        
        Args:
            clicks: 点击次数
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.click(clicks=clicks)
            elif self.method == 'pyautogui':
                pyautogui.click(clicks=clicks)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 左键点击失败: {e}")
            return False
    
    def right_click(self, clicks: int = 1) -> bool:
        """右键点击
        
        Args:
            clicks: 点击次数
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.rightClick(clicks=clicks)
            elif self.method == 'pyautogui':
                pyautogui.rightClick(clicks=clicks)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 右键点击失败: {e}")
            return False
    
    def key_down(self, key: str) -> bool:
        """按下按键
        
        Args:
            key: 键名
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.keyDown(key)
            elif self.method == 'pyautogui':
                pyautogui.keyDown(key)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 按下按键失败: {e}")
            return False
    
    def key_up(self, key: str) -> bool:
        """松开按键
        
        Args:
            key: 键名
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.keyUp(key)
            elif self.method == 'pyautogui':
                pyautogui.keyUp(key)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 松开按键失败: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """按键
        
        Args:
            key: 键名
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.press(key)
            elif self.method == 'pyautogui':
                pyautogui.press(key)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 按键失败: {e}")
            return False
    
    def hotkey(self, *keys) -> bool:
        """组合键
        
        Args:
            *keys: 键名列表
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'pydirectinput':
                pydirectinput.hotkey(*keys)
            elif self.method == 'pyautogui':
                pyautogui.hotkey(*keys)
            else:
                return False
            return True
        except Exception as e:
            print(f"[输入模拟] 组合键失败: {e}")
            return False
    
    def shift_click(self, x: int = None, y: int = None) -> bool:
        """Shift+点击
        
        Args:
            x: X坐标（可选，不传则在当前位置点击）
            y: Y坐标（可选）
        
        Returns:
            是否成功
        """
        try:
            # 移动到目标位置
            if x is not None and y is not None:
                self.move_to(x, y)
            
            # 按住Shift
            self.key_down('shift')
            time.sleep(0.05)
            
            # 左键点击
            self.left_click()
            time.sleep(0.05)
            
            # 释放Shift
            self.key_up('shift')
            
            return True
        except Exception as e:
            print(f"[输入模拟] Shift+点击失败: {e}")
            return False
    
    def ctrl_c(self) -> bool:
        """Ctrl+C 复制
        
        Returns:
            是否成功
        """
        try:
            self.hotkey('ctrl', 'c')
            return True
        except Exception as e:
            print(f"[输入模拟] Ctrl+C失败: {e}")
            return False
    
    def random_delay(self, min_delay: float = 0.1, max_delay: float = 0.3):
        """随机延迟
        
        Args:
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）
        """
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)


class GameActions:
    """游戏操作"""
    
    def __init__(self, simulator: InputSimulator):
        """初始化游戏操作
        
        Args:
            simulator: 输入模拟器
        """
        self.sim = simulator
        self.shift_held = False
    
    def pick_up_currency(self, currency_x: int, currency_y: int) -> bool:
        """拿起通货（右键点击）
        
        Args:
            currency_x: 通货X坐标
            currency_y: 通货Y坐标
        
        Returns:
            是否成功
        """
        # 移动到通货位置
        if not self.sim.move_to(currency_x, currency_y, jitter=2):
            return False
        
        self.sim.random_delay(0.05, 0.1)
        
        # 右键点击拿起通货
        if not self.sim.right_click():
            return False
        
        self.sim.random_delay(0.1, 0.2)
        
        return True
    
    def use_currency_on_item(self, item_x: int, item_y: int) -> bool:
        """在物品上使用通货（Shift+左键点击）
        
        Args:
            item_x: 物品X坐标
            item_y: 物品Y坐标
        
        Returns:
            是否成功
        """
        # 移动到物品位置
        if not self.sim.move_to(item_x, item_y, jitter=2):
            return False
        
        self.sim.random_delay(0.05, 0.1)
        
        # Shift+左键点击
        if not self.sim.shift_click():
            return False
        
        self.sim.random_delay(0.1, 0.2)
        
        return True
    
    def copy_item_info(self) -> bool:
        """复制物品信息（Ctrl+C）
        
        Returns:
            是否成功
        """
        return self.sim.ctrl_c()
    
    def hover_over_item(self, item_x: int, item_y: int) -> bool:
        """鼠标悬停在物品上
        
        Args:
            item_x: 物品X坐标
            item_y: 物品Y坐标
        
        Returns:
            是否成功
        """
        return self.sim.move_to(item_x, item_y, jitter=0)
    
    def craft_cycle(self, currency_x: int, currency_y: int,
                   item_x: int, item_y: int) -> bool:
        """执行一次洗练循环
        
        Args:
            currency_x: 通货X坐标
            currency_y: 通货Y坐标
            item_x: 物品X坐标
            item_y: 物品Y坐标
        
        Returns:
            是否成功
        """
        # 1. 拿起通货
        if not self.pick_up_currency(currency_x, currency_y):
            print("[洗练] 拿起通货失败")
            return False
        
        # 2. 在物品上使用通货
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
    
    # 获取鼠标位置
    pos = sim.get_mouse_position()
    print(f"当前鼠标位置: {pos}")
    
    # 测试移动
    print("\n测试移动鼠标到 (100, 100)...")
    sim.move_to(100, 100, jitter=0)
    time.sleep(0.5)
    
    pos = sim.get_mouse_position()
    print(f"新鼠标位置: {pos}")
    
    print("\n测试完成")
