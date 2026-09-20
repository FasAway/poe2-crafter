"""GUI界面 - PySimpleGUI界面（自适应布局）"""

import json
import time
import threading
from typing import Dict, List
from pathlib import Path

try:
    import PySimpleGUI as sg
    PSG_AVAILABLE = True
except ImportError:
    PSG_AVAILABLE = False
    print("[GUI] 警告: PySimpleGUI 未安装")

from core.crafter import Crafter, CraftingState
from core.parser import AffixRequirement


class MainWindow:
    """主窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        if not PSG_AVAILABLE:
            raise ImportError("PySimpleGUI 未安装")
        
        # 设置主题
        sg.theme('DarkBlue3')
        
        # 洗练器
        self.crafter = Crafter()
        
        # 配置目录
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # 窗口
        self.window = None
        
        # 坐标捕获状态
        self.capturing = False
        self.capture_target = None
        self.pending_capture = None
        self.mouse_listener = None
        self.key_listener = None
        
        # 设置回调
        self.crafter.set_callbacks(
            on_status_change=self._on_status_change,
            on_attempt=self._on_attempt,
            on_success=self._on_success,
            on_error=self._on_error
        )
        
        print("[GUI] 初始化完成")
    
    def create_layout(self) -> list:
        """创建界面布局（自适应）"""
        # 坐标配置区域
        coord_frame = sg.Frame('坐标配置', [
            [sg.Text('通货位置:', size=(10, 1)),
             sg.Input(key='-CURRENCY_X-', size=(8, 1)),
             sg.Text('X'),
             sg.Input(key='-CURRENCY_Y-', size=(8, 1)),
             sg.Text('Y'),
             sg.Push(),
             sg.Button('点击捕获通货坐标', key='-GET_CURRENCY-')],
            [sg.Text('物品位置:', size=(10, 1)),
             sg.Input(key='-ITEM_X-', size=(8, 1)),
             sg.Text('X'),
             sg.Input(key='-ITEM_Y-', size=(8, 1)),
             sg.Text('Y'),
             sg.Push(),
             sg.Button('点击捕获物品坐标', key='-GET_ITEM-')],
            [sg.Button('保存坐标', key='-SAVE_COORD-'),
             sg.Button('加载坐标', key='-LOAD_COORD-'),
             sg.Text('提示: 点击捕获按钮后，用鼠标点击目标位置即可记录坐标',
                    text_color='lightgray'),
             sg.Push()]
        ], expand_x=True)
        
        # 词缀条件区域
        affix_frame = sg.Frame('词缀条件', [
            [sg.Radio('包含 (Included)', 'AFFIX_TYPE', default=True, key='-INCLUDE-'),
             sg.Radio('排除 (Excluded)', 'AFFIX_TYPE', key='-EXCLUDE-')],
            [sg.Text('关键词:', size=(8, 1)),
             sg.Input(key='-KEYWORD-', size=(20, 1)),
             sg.Text('数值:'),
             sg.Combo(['>=', '>', '<=', '<', '==', '!='], default_value='>=', 
                     key='-OPERATOR-', size=(4, 1)),
             sg.Input(key='-VALUE-', size=(8, 1)),
             sg.Button('添加', key='-ADD_REQ-')],
            [sg.Listbox(values=[], size=(60, 5), key='-REQ_LIST-',
                       select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                       expand_x=True, expand_y=True)],
            [sg.Button('删除选中', key='-DEL_REQ-'),
             sg.Button('清空全部', key='-CLEAR_REQ-'),
             sg.Push()]
        ], expand_x=True)
        
        # 设置区域
        settings_frame = sg.Frame('设置', [
            [sg.Text('最大尝试次数:'),
             sg.Input(key='-MAX_ATTEMPTS-', size=(8, 1), default_text='100'),
             sg.Text('点击延迟:'),
             sg.Input(key='-DELAY_MIN-', size=(5, 1), default_text='0.15'),
             sg.Text('~'),
             sg.Input(key='-DELAY_MAX-', size=(5, 1), default_text='0.35'),
             sg.Text('秒'),
             sg.Push()]
        ], expand_x=True)
        
        # 控制按钮区域
        button_frame = sg.Frame('控制', [
            [sg.Button('保存配置', key='-SAVE_CONFIG-'),
             sg.Button('加载配置', key='-LOAD_CONFIG-'),
             sg.Button('测试剪贴板', key='-TEST_CLIP-'),
             sg.Button('测试解析', key='-TEST_PARSE-')],
            [sg.Button('▶ 开始 (F9)', key='-START-', button_color=('white', 'green')),
             sg.Button('⏸ 暂停 (F10)', key='-PAUSE-', button_color=('white', 'orange')),
             sg.Button('⏹ 停止 (F11)', key='-STOP-', button_color=('white', 'red')),
             sg.Button('🚨 紧急停止 (F12)', key='-EMERGENCY-', button_color=('white', 'darkred'))]
        ], expand_x=True)
        
        # 状态区域
        status_frame = sg.Frame('状态', [
            [sg.Text('状态: 空闲', key='-STATUS-', size=(20, 1)),
             sg.Text('次数: 0/100', key='-ATTEMPTS-', size=(15, 1)),
             sg.Text('用时: 00:00:00', key='-ELAPSED-', size=(15, 1))],
            [sg.Multiline(size=(70, 10), key='-LOG-', disabled=True, autoscroll=True,
                         expand_x=True, expand_y=True)]
        ], expand_x=True, expand_y=True)
        
        # 完整布局
        layout = [
            [coord_frame],
            [affix_frame],
            [settings_frame],
            [button_frame],
            [status_frame]
        ]
        
        return layout
    
    def create_window(self) -> sg.Window:
        """创建窗口"""
        layout = self.create_layout()
        
        window = sg.Window(
            'PoE2 洗练工具 v2.0 (剪贴板版)',
            layout,
            finalize=True,
            resizable=True,
            font=('Microsoft YaHei', 10)
        )
        
        # 设置最小窗口大小
        window.set_min_size((600, 700))
        
        return window
    
    def _log(self, message: str):
        """添加日志"""
        if self.window:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            self.window['-LOG-'].update(log_entry, append=True)
    
    def _update_status(self, state: str, message: str = ""):
        """更新状态"""
        if self.window:
            state_text = {
                CraftingState.IDLE: '空闲',
                CraftingState.RUNNING: '运行中',
                CraftingState.PAUSED: '已暂停',
                CraftingState.STOPPED: '已停止',
                CraftingState.SUCCESS: '成功!',
                CraftingState.ERROR: '错误'
            }.get(state, state)
            
            self.window['-STATUS-'].update(f"状态: {state_text}")
            if message:
                self._log(message)
    
    def _on_status_change(self, state: str, message: str):
        """状态变化回调"""
        self._update_status(state, message)
    
    def _on_attempt(self, count: int, item: Dict, result: Dict):
        """尝试次数回调"""
        if self.window:
            max_attempts = self.crafter.max_attempts
            self.window['-ATTEMPTS-'].update(f"次数: {count}/{max_attempts}")
            
            # 更新用时
            if self.crafter.start_time:
                elapsed = (time.time() - self.crafter.start_time.timestamp())
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                self.window['-ELAPSED-'].update(f"用时: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _on_success(self, count: int, item: Dict, result: Dict):
        """成功回调"""
        self._log(f"✓ 成功! 第 {count} 次尝试")
        for match in result['included_matched']:
            self._log(f"  匹配: {match['requirement']} = {match['value']}")
    
    def _on_error(self, error: str):
        """错误回调"""
        self._log(f"✗ 错误: {error}")
    
    def _get_mouse_position(self) -> tuple:
        """获取鼠标位置"""
        import pyautogui
        pos = pyautogui.position()
        return (pos.x, pos.y)
    
    def _start_capture(self, target: str):
        """开始坐标捕获模式
        
        进入捕获模式后，用户在任意位置点击鼠标左键，
        即可记录该点击位置的XY坐标（点击会被拦截，不影响游戏）。
        按 ESC 取消捕获。
        
        Args:
            target: 捕获目标 ('currency' 或 'item')
        """
        # 已在捕获模式时，再次点击按钮取消捕获
        if self.capturing:
            self.pending_capture = ('cancel', 0, 0)
            self.capturing = False
            return
        
        target_name = '通货' if target == 'currency' else '物品'
        self.capturing = True
        self.capture_target = target
        
        self._log(f"[捕获] 请点击{target_name}位置（该点击不会生效，ESC取消）...")
        if self.window:
            self.window['-STATUS-'].update(f"状态: 等待点击捕获{target_name}坐标")
        
        def on_click(x, y, button, pressed):
            if not self.capturing:
                return True
            if pressed:
                # 记录坐标，拦截此次点击
                self.pending_capture = (target, int(x), int(y))
                self.capturing = False
                return False  # 抑制该点击并停止监听
            return True  # 放行释放事件
        
        def on_press(key):
            from pynput import keyboard
            if key == keyboard.Key.esc:
                self.pending_capture = ('cancel', 0, 0)
                self.capturing = False
                return False  # 停止键盘监听
            return True
        
        try:
            from pynput import mouse, keyboard
            try:
                # 优先使用抑制模式：捕获点击不会传递到游戏
                self.mouse_listener = mouse.Listener(on_click=on_click, suppress=True)
                self.mouse_listener.start()
            except Exception:
                self.mouse_listener = mouse.Listener(on_click=on_click)
                self.mouse_listener.start()
                self._log("[捕获] 注意: 无法拦截点击，捕获点击会同时作用于游戏")
            
            self.key_listener = keyboard.Listener(on_press=on_press)
            self.key_listener.start()
        except Exception as e:
            # 回退方案：直接获取当前鼠标位置
            self._log(f"[捕获] 捕获模式启动失败: {e}，改为获取当前鼠标位置")
            self.capturing = False
            x, y = self._get_mouse_position()
            self.pending_capture = (target, x, y)
    
    def _stop_capture(self):
        """停止坐标捕获"""
        self.capturing = False
        for listener in (self.mouse_listener, self.key_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self.mouse_listener = None
        self.key_listener = None
    
    def _process_pending_capture(self):
        """处理捕获结果（在主事件循环中调用，保证线程安全）"""
        if self.pending_capture is None:
            return
        
        target, x, y = self.pending_capture
        self.pending_capture = None
        self._stop_capture()
        
        if not self.window:
            return
        
        if target == 'cancel':
            self._log("[捕获] 已取消")
            self.window['-STATUS-'].update("状态: 空闲")
            return
        
        if target == 'currency':
            self.crafter.coordinates.set_currency_position(x, y)
            self.window['-CURRENCY_X-'].update(x)
            self.window['-CURRENCY_Y-'].update(y)
            self._log(f"通货位置已捕获: ({x}, {y})")
        else:
            self.crafter.coordinates.set_item_position(x, y)
            self.window['-ITEM_X-'].update(x)
            self.window['-ITEM_Y-'].update(y)
            self._log(f"物品位置已捕获: ({x}, {y})")
        
        self.window['-STATUS-'].update("状态: 空闲")
    
    def _update_coord_display(self):
        """更新坐标显示"""
        if self.window:
            coords = self.crafter.coordinates.coordinates
            
            self.window['-CURRENCY_X-'].update(coords['currency']['x'])
            self.window['-CURRENCY_Y-'].update(coords['currency']['y'])
            self.window['-ITEM_X-'].update(coords['item']['x'])
            self.window['-ITEM_Y-'].update(coords['item']['y'])
    
    def _update_req_display(self):
        """更新需求列表显示"""
        if self.window:
            req_list = []
            
            for req in self.crafter.checker.included_requirements:
                value_str = f" {req.operator} {req.value}" if req.value else ""
                req_list.append(f"[包含] {req.keyword}{value_str}")
            
            for req in self.crafter.checker.excluded_requirements:
                value_str = f" {req.operator} {req.value}" if req.value else ""
                req_list.append(f"[排除] {req.keyword}{value_str}")
            
            self.window['-REQ_LIST-'].update(req_list)
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'coordinates': self.crafter.coordinates.coordinates,
                'requirements': self.crafter.checker.get_requirements_summary(),
                'settings': {
                    'max_attempts': self.crafter.max_attempts,
                    'delay_min': self.crafter.delay_min,
                    'delay_max': self.crafter.delay_max
                }
            }
            
            config_path = self.config_dir / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self._log(f"配置已保存: {config_path}")
        except Exception as e:
            self._log(f"保存配置失败: {e}")
    
    def load_config(self):
        """加载配置"""
        try:
            config_path = self.config_dir / "config.json"
            if not config_path.exists():
                self._log("配置文件不存在")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载坐标
            if 'coordinates' in config:
                self.crafter.coordinates.coordinates = config['coordinates']
                self._update_coord_display()
            
            # 加载需求
            if 'requirements' in config:
                self.crafter.checker.clear_requirements()
                
                for req in config['requirements'].get('included', []):
                    self.crafter.checker.add_requirement(
                        req['keyword'], req.get('operator', '>='), 
                        req.get('value'), is_include=True
                    )
                
                for req in config['requirements'].get('excluded', []):
                    self.crafter.checker.add_requirement(
                        req['keyword'], req.get('operator', '>='), 
                        req.get('value'), is_include=False
                    )
                
                self._update_req_display()
            
            # 加载设置
            if 'settings' in config:
                settings = config['settings']
                self.crafter.max_attempts = settings.get('max_attempts', 100)
                self.crafter.delay_min = settings.get('delay_min', 0.15)
                self.crafter.delay_max = settings.get('delay_max', 0.35)
                
                self.window['-MAX_ATTEMPTS-'].update(str(self.crafter.max_attempts))
                self.window['-DELAY_MIN-'].update(str(self.crafter.delay_min))
                self.window['-DELAY_MAX-'].update(str(self.crafter.delay_max))
            
            self._log(f"配置已加载: {config_path}")
        except Exception as e:
            self._log(f"加载配置失败: {e}")
    
    def run(self):
        """运行主窗口"""
        self.window = self.create_window()
        
        # 初始化显示
        self._update_coord_display()
        self._update_req_display()
        
        self._log("程序启动")
        self._log("请配置坐标和词缀条件")
        
        # 事件循环
        while True:
            event, values = self.window.read(timeout=100)
            
            # 处理坐标捕获结果
            self._process_pending_capture()
            
            if event == sg.WIN_CLOSED:
                break
            
            # 坐标配置
            elif event == '-GET_CURRENCY-':
                self._start_capture('currency')
            
            elif event == '-GET_ITEM-':
                self._start_capture('item')
            
            elif event == '-SAVE_COORD-':
                self.crafter.coordinates.save()
                self._log("坐标已保存")
            
            elif event == '-LOAD_COORD-':
                self.crafter.coordinates.load()
                self._update_coord_display()
                self._log("坐标已加载")
            
            # 词缀条件
            elif event == '-ADD_REQ-':
                keyword = values['-KEYWORD-']
                operator = values['-OPERATOR-']
                value = values['-VALUE-']
                is_include = values['-INCLUDE-']
                
                if keyword:
                    value_int = int(value) if value else None
                    self.crafter.checker.add_requirement(keyword, operator, value_int, is_include)
                    self._update_req_display()
                    self._log(f"已添加词缀条件: {keyword}")
                else:
                    self._log("请输入关键词")
            
            elif event == '-DEL_REQ-':
                selected = values['-REQ_LIST-']
                if selected:
                    self._log("请使用清空全部功能")
            
            elif event == '-CLEAR_REQ-':
                self.crafter.checker.clear_requirements()
                self._update_req_display()
                self._log("已清空所有词缀条件")
            
            # 配置
            elif event == '-SAVE_CONFIG-':
                self.save_config()
            
            elif event == '-LOAD_CONFIG-':
                self.load_config()
            
            # 测试
            elif event == '-TEST_CLIP-':
                text = self.crafter.clipboard.get_text()
                if text:
                    self._log(f"剪贴板内容: {text[:100]}...")
                else:
                    self._log("剪贴板为空")
            
            elif event == '-TEST_PARSE-':
                text = self.crafter.clipboard.get_text()
                if text:
                    item = self.crafter.parser.parse_item(text)
                    self._log(f"解析结果: {item['name']}")
                    for affix in item['affixes']:
                        self._log(f"  - {affix.raw_text}")
                else:
                    self._log("剪贴板为空，请先复制物品信息")
            
            # 控制
            elif event == '-START-':
                try:
                    self.crafter.max_attempts = int(values['-MAX_ATTEMPTS-'])
                    self.crafter.delay_min = float(values['-DELAY_MIN-'])
                    self.crafter.delay_max = float(values['-DELAY_MAX-'])
                except:
                    pass
                
                self.crafter.start()
            
            elif event == '-PAUSE-':
                if self.crafter.state == CraftingState.RUNNING:
                    self.crafter.pause()
                elif self.crafter.state == CraftingState.PAUSED:
                    self.crafter.resume()
            
            elif event == '-STOP-':
                self.crafter.stop()
            
            elif event == '-EMERGENCY-':
                self.crafter.stop()
                self._log("紧急停止!")
        
        # 清理
        self._stop_capture()
        self.crafter.stop()
        self.window.close()
    
    def start(self):
        """启动GUI"""
        if not PSG_AVAILABLE:
            print("PySimpleGUI 未安装，无法启动图形界面")
            return
        
        self.run()


# 测试代码
if __name__ == "__main__":
    print("GUI界面测试")
    print("=" * 40)
    
    if PSG_AVAILABLE:
        window = MainWindow()
        window.start()
    else:
        print("需要安装 PySimpleGUI:")
        print("pip install PySimpleGUI")
