"""洗练循环逻辑 - 核心洗练流程"""

import time
import threading
from typing import Callable, Optional, Dict, List
from datetime import datetime

from core.clipboard import ClipboardManager
from core.parser import ItemParser, AffixChecker, Affix, AffixRequirement
from core.input_sim import InputSimulator, GameActions
from core.coordinates import CoordinateManager


class CraftingState:
    """洗练状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 停止
    SUCCESS = "success"     # 成功
    ERROR = "error"         # 错误


class Crafter:
    """洗练器"""
    
    def __init__(self):
        """初始化洗练器"""
        # 核心组件
        self.clipboard = ClipboardManager()
        self.parser = ItemParser()
        self.checker = AffixChecker()
        self.simulator = InputSimulator()
        self.actions = GameActions(self.simulator)
        self.coordinates = CoordinateManager()
        
        # 状态
        self.state = CraftingState.IDLE
        self.attempt_count = 0
        self.max_attempts = 100
        self.start_time = None
        
        # 延迟设置
        self.delay_min = 0.15
        self.delay_max = 0.35
        
        # 线程控制
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始状态为非暂停
        
        # 回调函数
        self.on_status_change: Optional[Callable] = None
        self.on_attempt: Optional[Callable] = None
        self.on_success: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        print("[洗练器] 初始化完成")
    
    def set_callbacks(self, on_status_change=None, on_attempt=None,
                     on_success=None, on_error=None):
        """设置回调函数
        
        Args:
            on_status_change: 状态变化回调
            on_attempt: 尝试次数回调
            on_success: 成功回调
            on_error: 错误回调
        """
        self.on_status_change = on_status_change
        self.on_attempt = on_attempt
        self.on_success = on_success
        self.on_error = on_error
    
    def _update_state(self, new_state: str, message: str = ""):
        """更新状态
        
        Args:
            new_state: 新状态
            message: 状态消息
        """
        self.state = new_state
        if self.on_status_change:
            self.on_status_change(new_state, message)
    
    def _log(self, message: str):
        """打印日志
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def start(self):
        """开始洗练"""
        if self.state == CraftingState.RUNNING:
            self._log("已经在运行中")
            return
        
        # 检查坐标
        if not self.coordinates.is_valid():
            self._update_state(CraftingState.ERROR, "坐标未设置")
            self._log("错误: 坐标未设置")
            return
        
        # 检查词缀条件
        if not self.checker.included_requirements and not self.checker.excluded_requirements:
            self._update_state(CraftingState.ERROR, "词缀条件未设置")
            self._log("错误: 词缀条件未设置")
            return
        
        # 重置状态
        self.attempt_count = 0
        self.start_time = datetime.now()
        self._stop_event.clear()
        self._pause_event.set()
        
        # 启动线程
        self._thread = threading.Thread(target=self._crafting_loop, daemon=True)
        self._thread.start()
        
        self._update_state(CraftingState.RUNNING, "洗练已开始")
        self._log("洗练已开始")
    
    def stop(self):
        """停止洗练"""
        if self.state != CraftingState.RUNNING and self.state != CraftingState.PAUSED:
            return
        
        self._stop_event.set()
        self._pause_event.set()  # 解除暂停状态
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        self._update_state(CraftingState.STOPPED, "洗练已停止")
        self._log("洗练已停止")
    
    def pause(self):
        """暂停洗练"""
        if self.state != CraftingState.RUNNING:
            return
        
        self._pause_event.clear()
        self._update_state(CraftingState.PAUSED, "洗练已暂停")
        self._log("洗练已暂停")
    
    def resume(self):
        """恢复洗练"""
        if self.state != CraftingState.PAUSED:
            return
        
        self._pause_event.set()
        self._update_state(CraftingState.RUNNING, "洗练已恢复")
        self._log("洗练已恢复")
    
    def _crafting_loop(self):
        """洗练循环"""
        self._log("进入洗练循环")
        
        while not self._stop_event.is_set():
            # 检查暂停
            self._pause_event.wait()
            
            # 检查是否停止
            if self._stop_event.is_set():
                break
            
            # 检查最大次数
            if self.attempt_count >= self.max_attempts:
                self._update_state(CraftingState.STOPPED, f"已达到最大次数: {self.max_attempts}")
                self._log(f"已达到最大次数: {self.max_attempts}")
                break
            
            # 执行一次洗练
            try:
                self._do_craft()
            except Exception as e:
                self._update_state(CraftingState.ERROR, f"洗练错误: {e}")
                self._log(f"洗练错误: {e}")
                break
        
        self._log("退出洗练循环")
    
    def _do_craft(self):
        """执行一次洗练"""
        self.attempt_count += 1
        
        # 获取坐标
        currency_x, currency_y = self.coordinates.get_currency_position()
        item_x, item_y = self.coordinates.get_item_position()
        
        self._log(f"第 {self.attempt_count} 次洗练")
        
        # 1. 鼠标悬停在物品上
        self._log("  鼠标悬停在物品上...")
        if not self.actions.hover_over_item(item_x, item_y):
            raise Exception("鼠标悬停失败")
        
        time.sleep(0.1)
        
        # 2. Ctrl+C 复制物品信息
        self._log("  复制物品信息...")
        if not self.actions.copy_item_info():
            raise Exception("复制失败")
        
        time.sleep(0.2)
        
        # 3. 从剪贴板读取文本
        self._log("  读取剪贴板...")
        text = self.clipboard.get_text()
        if not text:
            raise Exception("剪贴板为空")
        
        # 4. 解析物品
        self._log("  解析物品词缀...")
        item = self.parser.parse_item(text)
        affixes = item['affixes']
        
        self._log(f"  找到 {len(affixes)} 个词缀")
        for affix in affixes:
            self._log(f"    - {affix.raw_text}")
        
        # 5. 检查词缀条件
        self._log("  检查词缀条件...")
        result = self.checker.check(affixes)
        
        if self.on_attempt:
            self.on_attempt(self.attempt_count, item, result)
        
        # 6. 判断是否满足条件
        if result['satisfied']:
            self._stop_event.set()
            self._update_state(CraftingState.SUCCESS, 
                             f"满足条件! 第 {self.attempt_count} 次")
            self._log(f"  ✓ 满足条件!")
            if self.on_success:
                self.on_success(self.attempt_count, item, result)
            return
        
        self._log(f"  ✗ 不满足条件，继续...")
        
        # 7. 执行洗练操作
        self._log("  执行洗练操作...")
        if not self.actions.craft_cycle(currency_x, currency_y, item_x, item_y):
            raise Exception("洗练操作失败")
        
        # 8. 随机延迟
        delay = self.simulator.random_delay(self.delay_min, self.delay_max)
        self._log(f"  等待 {delay:.2f} 秒...")
    
    def get_status(self) -> Dict:
        """获取状态信息
        
        Returns:
            状态信息字典
        """
        elapsed = None
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'state': self.state,
            'attempt_count': self.attempt_count,
            'max_attempts': self.max_attempts,
            'elapsed': elapsed,
            'coordinates': self.coordinates.get_summary(),
            'requirements': self.checker.get_requirements_summary()
        }


# 测试代码
if __name__ == "__main__":
    print("洗练循环逻辑测试")
    print("=" * 40)
    
    crafter = Crafter()
    
    # 设置回调
    def on_status_change(state, message):
        print(f"状态变化: {state} - {message}")
    
    def on_attempt(count, item, result):
        print(f"尝试 {count}: {item['name']}, 满足: {result['satisfied']}")
    
    def on_success(count, item, result):
        print(f"成功! 第 {count} 次")
    
    def on_error(error):
        print(f"错误: {error}")
    
    crafter.set_callbacks(
        on_status_change=on_status_change,
        on_attempt=on_attempt,
        on_success=on_success,
        on_error=on_error
    )
    
    # 设置测试坐标
    crafter.coordinates.set_currency_position(500, 300)
    crafter.coordinates.set_item_position(600, 400)
    
    # 添加词缀条件
    crafter.checker.add_requirement("生命", value=50)
    crafter.checker.add_requirement("抗性", value=30)
    
    # 获取状态
    status = crafter.get_status()
    print(f"\n状态: {status}")
    
    print("\n测试完成")
