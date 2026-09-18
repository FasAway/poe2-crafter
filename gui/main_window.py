"""GUI界面 - PySimpleGUI界面"""

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
        
        # 设置回调
        self.crafter.set_callbacks(
            on_status_change=self._on_status_change,
            on_attempt=self._on_attempt,
            on_success=self._on_success,
            on_error=self._on_error
        )
        
        print("[GUI] 初始化完成")
    
    def create_layout(self) -> list:
        """创建界面布局"""
        # 坐标配置区域
        coord_frame = sg.Frame('坐标配置', [
            [sg.Text('通货位置:', size=(10, 1)),
             sg.Input(key='-CURRENCY_X-', size=(8, 1)),
             sg.Text('X'),
             sg.Input(key='-CURRENCY_Y-', size=(8, 1)),
             sg.Text('Y'),
             sg.Button('获取鼠标位置', key='-GET_CURRENCY-', size=(12, 1))],
            [sg.Text('物品位置:', size=(10, 1)),
             sg.Input(key='-ITEM_X-', size=(8, 1)),
             sg.Text('X'),
             sg.Input(key='-ITEM_Y-', size=(8, 1)),
             sg.Text('Y'),
             sg.Button('获取鼠标位置', key='-GET_ITEM-', size=(12, 1))],
            [sg.Button('保存坐标', key='-SAVE_COORD-', size=(10, 1)),
             sg.Button('加载坐标', key='-LOAD_COORD-', size=(10, 1))]
        ], size=(600, 120))
        
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
             sg.Button('添加', key='-ADD_REQ-', size=(6, 1))],
            [sg.Listbox(values=[], size=(70, 5), key='-REQ_LIST-',
                       select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)],
            [sg.Button('删除选中', key='-DEL_REQ-', size=(10, 1)),
             sg.Button('清空全部', key='-CLEAR_REQ-', size=(10, 1))]
        ], size=(600, 180))
        
        # 设置区域
        settings_frame = sg.Frame('设置', [
            [sg.Text('最大尝试次数:'),
             sg.Input(key='-MAX_ATTEMPTS-', size=(8, 1), default_text='100'),
             sg.Text('点击延迟:'),
             sg.Input(key='-DELAY_MIN-', size=(5, 1), default_text='0.15'),
             sg.Text('~'),
             sg.Input(key='-DELAY_MAX-', size=(5, 1), default_text='0.35'),
             sg.Text('秒')]
        ], size=(600, 60))
        
        # 控制按钮区域
        button_frame = sg.Frame('控制', [
            [sg.Button('保存配置', key='-SAVE_CONFIG-', size=(10, 1)),
             sg.Button('加载配置', key='-LOAD_CONFIG-', size=(10, 1)),
             sg.Button('测试剪贴板', key='-TEST_CLIP-', size=(10, 1)),
             sg.Button('测试解析', key='-TEST_PARSE-', size=(10, 1))],
            [sg.Button('▶ 开始 (F9)', key='-START-', size=(14, 1), button_color=('white', 'green')),
             sg.Button('⏸ 暂停 (F10)', key='-PAUSE-', size=(14, 1), button_color=('white', 'orange')),
             sg.Button('⏹ 停止 (F11)', key='-STOP-', size=(14, 1), button_color=('white', 'red')),
             sg.Button('🚨 紧急停止 (F12)', key='-EMERGENCY-', size=(16, 1), button_color=('white', 'darkred'))]
        ], size=(600, 100))
        
        # 状态区域
        status_frame = sg.Frame('状态', [
            [sg.Text('状态: 空闲', key='-STATUS-', size=(30, 1)),
             sg.Text('次数: 0/100', key='-ATTEMPTS-', size=(15, 1)),
             sg.Text('用时: 00:00:00', key='-ELAPSED-', size=(15, 1))],
            [sg.Multiline(size=(80, 10), key='-LOG-', disabled=True, autoscroll=True)]
        ], size=(600, 200))
        
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
            
            if event == sg.WIN_CLOSED:
                break
            
            # 坐标配置
            elif event == '-GET_CURRENCY-':
                x, y = self._get_mouse_position()
                self.crafter.coordinates.set_currency_position(x, y)
                self.window['-CURRENCY_X-'].update(x)
                self.window['-CURRENCY_Y-'].update(y)
                self._log(f"通货位置已设置: ({x}, {y})")
            
            elif event == '-GET_ITEM-':
                x, y = self._get_mouse_position()
                self.crafter.coordinates.set_item_position(x, y)
                self.window['-ITEM_X-'].update(x)
                self.window['-ITEM_Y-'].update(y)
                self._log(f"物品位置已设置: ({x}, {y})")
            
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
                    # 简化处理：清空并重新添加
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
                # 更新设置
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
