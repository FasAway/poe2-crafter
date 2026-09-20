"""GUI界面 - CustomTkinter 现代风格"""

import json
import queue
import time
from typing import Dict, Optional
from pathlib import Path

try:
    import customtkinter as ctk
    CTk_AVAILABLE = True
except ImportError:
    CTk_AVAILABLE = False
    print("[GUI] 警告: customtkinter 未安装")

from core.crafter import Crafter, CraftingState


# 配色
COLOR_BG = "#1a1d23"
COLOR_CARD = "#22262e"
COLOR_ACCENT = "#2FA572"
COLOR_DANGER = "#C0392B"
COLOR_WARNING = "#E67E22"
COLOR_TEXT_DIM = "#8a93a6"

STATE_COLORS = {
    CraftingState.IDLE: "#8a93a6",
    CraftingState.RUNNING: "#2FA572",
    CraftingState.PAUSED: "#E67E22",
    CraftingState.STOPPED: "#5b8dd9",
    CraftingState.SUCCESS: "#2ECC71",
    CraftingState.ERROR: "#E74C3C",
}

STATE_TEXTS = {
    CraftingState.IDLE: "空闲",
    CraftingState.RUNNING: "运行中",
    CraftingState.PAUSED: "已暂停",
    CraftingState.STOPPED: "已停止",
    CraftingState.SUCCESS: "成功!",
    CraftingState.ERROR: "错误",
}


class MainWindow:
    """主窗口"""

    def __init__(self):
        """初始化主窗口"""
        if not CTk_AVAILABLE:
            raise ImportError("customtkinter 未安装")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # 洗练器
        self.crafter = Crafter()

        # 配置目录
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)

        # 坐标捕获状态
        self.capturing = False
        self.capture_target = None
        self.pending_capture = None
        self.mouse_listener = None
        self.key_listener = None
        self.hotkey_listener = None

        # UI线程安全队列
        self._ui_queue = queue.Queue()

        # 主窗口
        self.root = ctk.CTk()
        self.root.title("PoE2 洗练工具 v2.0")
        self.root.geometry("980x660")
        self.root.minsize(880, 600)
        self.root.configure(fg_color=COLOR_BG)

        # 注册回调（worker线程 -> 队列 -> 主线程处理）
        self.crafter.set_callbacks(
            on_status_change=lambda s, m: self._ui_queue.put(("status", s, m)),
            on_attempt=lambda c, i, r: self._ui_queue.put(("attempt", c, i, r)),
            on_success=lambda c, i, r: self._ui_queue.put(("success", c, i, r)),
            on_error=lambda e: self._ui_queue.put(("error", e, None, None)),
        )

        self._build_ui()
        self._register_hotkeys()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._log("程序启动")
        self._log("提示: 配置坐标和词缀条件后，点击开始或按 F9")
        self.root.after(100, self._poll)

    # ==================== UI 构建 ====================

    def _build_ui(self):
        """构建界面"""
        self.root.grid_columnconfigure(0, weight=5)
        self.root.grid_columnconfigure(1, weight=4)
        self.root.grid_rowconfigure(0, weight=1)

        # ---------- 左侧：Tab页 ----------
        self.tabs = ctk.CTkTabview(
            self.root, corner_radius=12,
            fg_color=COLOR_CARD, segmented_button_fg_color="#2b303b",
        )
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        self._build_coord_tab()
        self._build_affix_tab()
        self._build_settings_tab()

        # ---------- 右侧：状态 + 控制 + 日志 ----------
        right = ctk.CTkFrame(self.root, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(3, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # 状态卡片
        status_card = ctk.CTkFrame(right, corner_radius=12, fg_color=COLOR_CARD)
        status_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        status_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(status_card, text="状态", font=("Microsoft YaHei UI", 12, "bold"),
                     text_color=COLOR_TEXT_DIM).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))

        row2 = ctk.CTkFrame(status_card, fg_color="transparent")
        row2.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))
        row2.grid_columnconfigure(3, weight=1)

        self.state_dot = ctk.CTkLabel(row2, text="●", font=("", 14), text_color=STATE_COLORS[CraftingState.IDLE])
        self.state_dot.grid(row=0, column=0, padx=(0, 4))
        self.state_label = ctk.CTkLabel(row2, text="空闲", font=("Microsoft YaHei UI", 14, "bold"))
        self.state_label.grid(row=0, column=1, padx=(0, 16))
        self.attempts_label = ctk.CTkLabel(row2, text="次数 0/100", font=("Consolas", 13),
                                           text_color=COLOR_TEXT_DIM)
        self.attempts_label.grid(row=0, column=2)
        self.elapsed_label = ctk.CTkLabel(row2, text="00:00:00", font=("Consolas", 13),
                                          text_color=COLOR_TEXT_DIM)
        self.elapsed_label.grid(row=0, column=3, sticky="e")

        # 控制按钮
        btn_card = ctk.CTkFrame(right, corner_radius=12, fg_color=COLOR_CARD)
        btn_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        btn_card.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            btn_card, text="▶  开始 (F9)", height=42, corner_radius=8,
            font=("Microsoft YaHei UI", 14, "bold"), fg_color=COLOR_ACCENT,
            hover_color="#27885f", command=self._on_start)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=10)

        self.pause_btn = ctk.CTkButton(
            btn_card, text="⏸  暂停 (F10)", height=42, corner_radius=8,
            font=("Microsoft YaHei UI", 14, "bold"), fg_color=COLOR_WARNING,
            hover_color="#c96d1c", command=self._on_pause)
        self.pause_btn.grid(row=0, column=1, sticky="ew", padx=(4, 10), pady=10)

        self.stop_btn = ctk.CTkButton(
            btn_card, text="⏹  停止 (F11)", height=36, corner_radius=8,
            font=("Microsoft YaHei UI", 13), fg_color=COLOR_DANGER,
            hover_color="#992d21", command=self._on_stop)
        self.stop_btn.grid(row=1, column=0, sticky="ew", padx=(10, 4), pady=(0, 10))

        self.emergency_btn = ctk.CTkButton(
            btn_card, text="🚨 紧急停止 (F12)", height=36, corner_radius=8,
            font=("Microsoft YaHei UI", 13, "bold"), fg_color="#7b1f16",
            hover_color="#5a1610", command=self._on_emergency)
        self.emergency_btn.grid(row=1, column=1, sticky="ew", padx=(4, 10), pady=(0, 10))

        # 日志
        log_card = ctk.CTkFrame(right, corner_radius=12, fg_color=COLOR_CARD)
        log_card.grid(row=3, column=0, sticky="nsew")
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_card, text="运行日志", font=("Microsoft YaHei UI", 12, "bold"),
                     text_color=COLOR_TEXT_DIM).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))

        self.log_box = ctk.CTkTextbox(
            log_card, font=("Consolas", 12), wrap="word",
            fg_color="#16191e", text_color="#c8d3e0", corner_radius=8)
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6, 10))
        self.log_box.configure(state="disabled")

    def _build_coord_tab(self):
        """坐标配置Tab"""
        tab = self.tabs.add("坐标配置")
        tab.grid_columnconfigure(1, weight=1)

        def coord_row(parent, row, label, name):
            frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2b303b")
            frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(12, 0))
            frame.grid_columnconfigure(4, weight=1)

            ctk.CTkLabel(frame, text=label, font=("Microsoft YaHei UI", 13, "bold"),
                         width=70).grid(row=0, column=0, padx=(12, 8), pady=10)
            x_entry = ctk.CTkEntry(frame, width=70, font=("Consolas", 13))
            x_entry.grid(row=0, column=1, padx=(0, 4), pady=10)
            ctk.CTkLabel(frame, text="X", text_color=COLOR_TEXT_DIM).grid(row=0, column=2, padx=(0, 8))
            y_entry = ctk.CTkEntry(frame, width=70, font=("Consolas", 13))
            y_entry.grid(row=0, column=3, padx=(0, 4), pady=10)
            ctk.CTkLabel(frame, text="Y", text_color=COLOR_TEXT_DIM).grid(row=0, column=4, sticky="w")

            btn = ctk.CTkButton(
                frame, text="点击捕获", width=110, height=32, corner_radius=6,
                font=("Microsoft YaHei UI", 12, "bold"),
                fg_color="#3a6ea5", hover_color="#2f5a87",
                command=lambda: self._start_capture(name))
            btn.grid(row=0, column=5, padx=(8, 12), pady=10)

            setattr(self, f"entry_{name}_x", x_entry)
            setattr(self, f"entry_{name}_y", y_entry)
            setattr(self, f"capture_btn_{name}", btn)

        coord_row(tab, 0, "通货位置", "currency")
        coord_row(tab, 1, "物品位置", "item")

        ctk.CTkLabel(tab, text="点击「点击捕获」后，用鼠标点击游戏内目标位置即可记录坐标\n（捕获点击会被拦截，不影响游戏；按 ESC 取消）",
                     font=("Microsoft YaHei UI", 12), text_color=COLOR_TEXT_DIM,
                     justify="left").grid(row=2, column=0, sticky="w", padx=14, pady=(10, 0))

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=12)
        ctk.CTkButton(btns, text="保存坐标", width=100, height=32, corner_radius=6,
                      command=self._save_coords).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btns, text="加载坐标", width=100, height=32, corner_radius=6,
                      fg_color="#4a5364", hover_color="#3c4452",
                      command=self._load_coords).grid(row=0, column=1)

    def _build_affix_tab(self):
        """词缀条件Tab"""
        tab = self.tabs.add("词缀条件")
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # 类型选择
        self.req_type = ctk.CTkSegmentedButton(
            tab, values=["包含 (满足才停)", "排除 (出现即停)"],
            font=("Microsoft YaHei UI", 13))
        self.req_type.set("包含 (满足才停)")
        self.req_type.grid(row=0, column=0, sticky="w", padx=10, pady=(12, 6))

        # 输入行
        input_row = ctk.CTkFrame(tab, corner_radius=10, fg_color="#2b303b")
        input_row.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        input_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_row, text="关键词", font=("Microsoft YaHei UI", 12),
                     text_color=COLOR_TEXT_DIM).grid(row=0, column=0, padx=(12, 6), pady=10)
        self.keyword_entry = ctk.CTkEntry(input_row, placeholder_text="如: 生命 / 冰冷抗性 / 伤害",
                                          font=("Microsoft YaHei UI", 13))
        self.keyword_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=10)

        self.operator_combo = ctk.CTkComboBox(input_row, values=[">=", ">", "<=", "<", "==", "!="],
                                              width=70, font=("Consolas", 13))
        self.operator_combo.set(">=")
        self.operator_combo.grid(row=0, column=2, padx=4, pady=10)

        self.value_entry = ctk.CTkEntry(input_row, placeholder_text="数值", width=70,
                                        font=("Consolas", 13))
        self.value_entry.grid(row=0, column=3, padx=4, pady=10)

        ctk.CTkButton(input_row, text="＋ 添加", width=80, height=32, corner_radius=6,
                      fg_color=COLOR_ACCENT, hover_color="#27885f",
                      font=("Microsoft YaHei UI", 12, "bold"),
                      command=self._add_requirement).grid(row=0, column=4, padx=(4, 12), pady=10)

        # 需求列表
        list_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#16191e")
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=6)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.req_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.req_scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 12))
        ctk.CTkButton(btns, text="清空全部", width=100, height=30, corner_radius=6,
                      fg_color=COLOR_DANGER, hover_color="#992d21",
                      command=self._clear_requirements).grid(row=0, column=0)

    def _build_settings_tab(self):
        """设置Tab"""
        tab = self.tabs.add("设置")
        tab.grid_columnconfigure(1, weight=1)

        def setting_row(row, label, default, width=80):
            frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#2b303b")
            frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(12, 0))
            frame.grid_columnconfigure(3, weight=1)
            ctk.CTkLabel(frame, text=label, font=("Microsoft YaHei UI", 13),
                         width=110).grid(row=0, column=0, padx=(12, 8), pady=10)
            entry = ctk.CTkEntry(frame, width=width, font=("Consolas", 13))
            entry.insert(0, str(default))
            entry.grid(row=0, column=1, pady=10)
            return entry

        self.max_attempts_entry = setting_row(0, "最大尝试次数", 100)
        self.delay_min_entry = setting_row(1, "点击延迟(秒)", 0.15)
        self.delay_max_entry = setting_row(2, "延迟上限(秒)", 0.35)

        ctk.CTkLabel(tab, text="延迟用于模拟人工操作节奏，避免点击过快",
                     font=("Microsoft YaHei UI", 12), text_color=COLOR_TEXT_DIM
                     ).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 0))

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=10, pady=14)
        ctk.CTkButton(btns, text="保存全部配置", width=120, height=32, corner_radius=6,
                      command=self._save_config).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btns, text="加载配置", width=100, height=32, corner_radius=6,
                      fg_color="#4a5364", hover_color="#3c4452",
                      command=self._load_config).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(btns, text="测试剪贴板", width=100, height=32, corner_radius=6,
                      fg_color="#4a5364", hover_color="#3c4452",
                      command=self._test_clipboard).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(btns, text="测试解析", width=100, height=32, corner_radius=6,
                      fg_color="#4a5364", hover_color="#3c4452",
                      command=self._test_parse).grid(row=0, column=3)

    # ==================== 日志与状态 ====================

    def _log(self, message: str):
        """写入日志（仅主线程调用）"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, state: str, message: str = ""):
        """更新状态显示"""
        text = STATE_TEXTS.get(state, state)
        color = STATE_COLORS.get(state, "#8a93a6")
        self.state_label.configure(text=text, text_color=color)
        self.state_dot.configure(text_color=color)
        if message:
            self._log(message)

    def _update_attempts(self):
        """更新尝试次数显示"""
        self.attempts_label.configure(
            text=f"次数 {self.crafter.attempt_count}/{self.crafter.max_attempts}")

    def _update_elapsed(self):
        """更新用时显示"""
        if self.crafter.start_time:
            elapsed = time.time() - self.crafter.start_time.timestamp()
            h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
            self.elapsed_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

    # ==================== 主循环 ====================

    def _poll(self):
        """定时处理队列事件与捕获结果"""
        # 1. 处理worker线程事件
        while True:
            try:
                item = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_ui_event(item)

        # 2. 处理坐标捕获结果
        self._process_pending_capture()

        # 3. 刷新运行信息
        if self.crafter.state in (CraftingState.RUNNING, CraftingState.PAUSED):
            self._update_attempts()
            self._update_elapsed()

        self.root.after(100, self._poll)

    def _handle_ui_event(self, item: tuple):
        """处理来自队列的UI事件"""
        kind = item[0]
        if kind == "hotkey":
            action = item[1]
            if action == "start":
                self._on_start()
            elif action == "pause":
                self._on_pause()
            elif action == "stop":
                self._on_stop()
            elif action == "emergency":
                self._on_emergency()
        elif kind == "status":
            self._set_status(item[1], item[2])
        elif kind == "attempt":
            _, count, item_dict, result = item
            self._log(f"第 {count} 次: {item_dict['name']} -> "
                      f"{'满足' if result['satisfied'] else '不满足'}")
        elif kind == "success":
            _, count, item_dict, result = item
            self._log(f"✓ 成功! 第 {count} 次尝试")
            for match in result['included_matched']:
                self._log(f"  匹配: {match['requirement']} = {match['value']}")
        elif kind == "error":
            self._log(f"✗ 错误: {item[1]}")

    # ==================== 坐标捕获 ====================

    def _get_mouse_position(self) -> tuple:
        """获取鼠标位置（pynput实现，不依赖pyautogui）"""
        try:
            from pynput.mouse import Controller
            pos = Controller().position
            return (int(pos.x), int(pos.y))
        except Exception:
            return (0, 0)

    def _start_capture(self, target: str):
        """开始坐标捕获：下一次鼠标点击即记录坐标"""
        if self.capturing:
            self.pending_capture = ('cancel', 0, 0)
            self.capturing = False
            return

        target_name = '通货' if target == 'currency' else '物品'
        self.capturing = True
        self.capture_target = target
        self._log(f"[捕获] 请点击{target_name}位置（该点击不会生效，ESC取消）...")
        self.state_label.configure(text=f"捕获{target_name}坐标...", text_color=COLOR_WARNING)
        getattr(self, f"capture_btn_{target}").configure(text="点击中...", fg_color="#7b1f16")

        def on_click(x, y, button, pressed):
            if not self.capturing:
                return True
            if pressed:
                self.pending_capture = (target, int(x), int(y))
                self.capturing = False
                return False  # 拦截该点击并停止监听
            return True

        def on_press(key):
            from pynput import keyboard
            if key == keyboard.Key.esc:
                self.pending_capture = ('cancel', 0, 0)
                self.capturing = False
                return False
            return True

        try:
            from pynput import mouse, keyboard
            try:
                self.mouse_listener = mouse.Listener(on_click=on_click, suppress=True)
                self.mouse_listener.start()
            except Exception:
                self.mouse_listener = mouse.Listener(on_click=on_click)
                self.mouse_listener.start()
                self._log("[捕获] 注意: 无法拦截点击，捕获点击会同时作用于游戏")

            self.key_listener = keyboard.Listener(on_press=on_press)
            self.key_listener.start()
        except Exception as e:
            self._log(f"[捕获] 启动失败: {e}，改为获取当前鼠标位置")
            self.capturing = False
            x, y = self._get_mouse_position()
            self.pending_capture = (target, x, y)

    def _stop_capture(self):
        """停止捕获监听"""
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
        """处理捕获结果"""
        if self.pending_capture is None:
            return

        target, x, y = self.pending_capture
        self.pending_capture = None
        self._stop_capture()

        if target == 'cancel':
            self._log("[捕获] 已取消")
            self._reset_capture_buttons()
            self._set_status(self.crafter.state)
            return

        if target == 'currency':
            self.crafter.coordinates.set_currency_position(x, y)
            self.entry_currency_x.delete(0, "end")
            self.entry_currency_x.insert(0, x)
            self.entry_currency_y.delete(0, "end")
            self.entry_currency_y.insert(0, y)
            self._log(f"通货位置已捕获: ({x}, {y})")
        else:
            self.crafter.coordinates.set_item_position(x, y)
            self.entry_item_x.delete(0, "end")
            self.entry_item_x.insert(0, x)
            self.entry_item_y.delete(0, "end")
            self.entry_item_y.insert(0, y)
            self._log(f"物品位置已捕获: ({x}, {y})")

        self._reset_capture_buttons()
        self._set_status(self.crafter.state)

    def _reset_capture_buttons(self):
        """恢复捕获按钮文字"""
        self.capture_btn_currency.configure(text="点击捕获", fg_color="#3a6ea5")
        self.capture_btn_item.configure(text="点击捕获", fg_color="#3a6ea5")

    def _refresh_coord(self):
        """刷新坐标显示"""
        coords = self.crafter.coordinates.coordinates
        self.entry_currency_x.delete(0, "end")
        self.entry_currency_x.insert(0, coords['currency']['x'])
        self.entry_currency_y.delete(0, "end")
        self.entry_currency_y.insert(0, coords['currency']['y'])
        self.entry_item_x.delete(0, "end")
        self.entry_item_x.insert(0, coords['item']['x'])
        self.entry_item_y.delete(0, "end")
        self.entry_item_y.insert(0, coords['item']['y'])

    # ==================== 词缀条件 ====================

    def _add_requirement(self):
        """添加词缀条件"""
        keyword = self.keyword_entry.get().strip()
        operator = self.operator_combo.get()
        value_str = self.value_entry.get().strip()
        is_include = self.req_type.get().startswith("包含")

        if not keyword:
            self._log("请输入关键词")
            return

        try:
            value = int(value_str) if value_str else None
        except ValueError:
            self._log("数值必须是整数")
            return

        self.crafter.checker.add_requirement(keyword, operator, value, is_include)
        self.keyword_entry.delete(0, "end")
        self.value_entry.delete(0, "end")
        self._refresh_requirements()
        self._log(f"已添加条件: [{'包含' if is_include else '排除'}] {keyword} {operator} {value_str}")

    def _delete_requirement(self, index: int, is_include: bool):
        """删除指定条件"""
        self.crafter.checker.remove_requirement(index, is_include)
        self._refresh_requirements()

    def _clear_requirements(self):
        """清空所有条件"""
        self.crafter.checker.clear_requirements()
        self._refresh_requirements()
        self._log("已清空所有词缀条件")

    def _refresh_requirements(self):
        """重建条件列表显示"""
        for child in self.req_scroll.winfo_children():
            child.destroy()

        rows = []
        for i, req in enumerate(self.crafter.checker.included_requirements):
            value_str = f" {req.operator} {req.value}" if req.value is not None else ""
            rows.append((f"包含  {req.keyword}{value_str}", i, True))
        for i, req in enumerate(self.crafter.checker.excluded_requirements):
            value_str = f" {req.operator} {req.value}" if req.value is not None else ""
            rows.append((f"排除  {req.keyword}{value_str}", i, False))

        if not rows:
            ctk.CTkLabel(self.req_scroll, text="暂无条件，在上方添加",
                         text_color=COLOR_TEXT_DIM,
                         font=("Microsoft YaHei UI", 12)).grid(row=0, column=0, pady=16)
            return

        for row, (text, index, is_include) in enumerate(rows):
            item_frame = ctk.CTkFrame(self.req_scroll, corner_radius=8, fg_color="#2b303b")
            item_frame.grid(row=row, column=0, sticky="ew", pady=3, padx=2)
            item_frame.grid_columnconfigure(0, weight=1)

            color = COLOR_ACCENT if is_include else COLOR_DANGER
            ctk.CTkLabel(item_frame, text=text, font=("Microsoft YaHei UI", 13),
                         text_color=color).grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkButton(item_frame, text="✕", width=28, height=24, corner_radius=6,
                          fg_color="#4a5364", hover_color=COLOR_DANGER,
                          font=("", 12),
                          command=lambda i=index, inc=is_include: self._delete_requirement(i, inc)
                          ).grid(row=0, column=1, padx=(0, 8), pady=6)

    # ==================== 配置读写 ====================

    def _apply_settings(self):
        """从输入框读取设置"""
        try:
            self.crafter.max_attempts = int(self.max_attempts_entry.get())
        except ValueError:
            pass
        try:
            self.crafter.delay_min = float(self.delay_min_entry.get())
            self.crafter.delay_max = float(self.delay_max_entry.get())
        except ValueError:
            pass

    def _save_coords(self):
        self.crafter.coordinates.save()
        self._log("坐标已保存")

    def _load_coords(self):
        self.crafter.coordinates.load()
        self._refresh_coord()
        self._log("坐标已加载")

    def _save_config(self):
        """保存全部配置"""
        try:
            self._apply_settings()
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

    def _load_config(self):
        """加载全部配置"""
        try:
            config_path = self.config_dir / "config.json"
            if not config_path.exists():
                self._log("配置文件不存在")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'coordinates' in config:
                self.crafter.coordinates.coordinates = config['coordinates']
                self._refresh_coord()

            if 'requirements' in config:
                self.crafter.checker.clear_requirements()
                for req in config['requirements'].get('included', []):
                    self.crafter.checker.add_requirement(
                        req['keyword'], req.get('operator', '>='), req.get('value'), True)
                for req in config['requirements'].get('excluded', []):
                    self.crafter.checker.add_requirement(
                        req['keyword'], req.get('operator', '>='), req.get('value'), False)
                self._refresh_requirements()

            if 'settings' in config:
                s = config['settings']
                self.crafter.max_attempts = s.get('max_attempts', 100)
                self.crafter.delay_min = s.get('delay_min', 0.15)
                self.crafter.delay_max = s.get('delay_max', 0.35)
                self.max_attempts_entry.delete(0, "end")
                self.max_attempts_entry.insert(0, str(self.crafter.max_attempts))
                self.delay_min_entry.delete(0, "end")
                self.delay_min_entry.insert(0, str(self.crafter.delay_min))
                self.delay_max_entry.delete(0, "end")
                self.delay_max_entry.insert(0, str(self.crafter.delay_max))

            self._log("配置已加载")
        except Exception as e:
            self._log(f"加载配置失败: {e}")

    # ==================== 测试 ====================

    def _test_clipboard(self):
        """测试剪贴板读取"""
        text = self.crafter.clipboard.get_text()
        if text:
            preview = text[:80].replace('\n', ' | ')
            self._log(f"剪贴板: {preview}...")
        else:
            self._log("剪贴板为空")

    def _test_parse(self):
        """测试物品解析"""
        text = self.crafter.clipboard.get_text()
        if not text:
            self._log("剪贴板为空，请先在游戏中复制物品(Ctrl+C)")
            return
        item = self.crafter.parser.parse_item(text)
        self._log(f"解析: {item['name']} ({item['rarity']})")
        for affix in item['affixes']:
            self._log(f"  - {affix.raw_text}")

    # ==================== 控制 ====================

    def _on_start(self):
        """开始洗练"""
        if self.crafter.state == CraftingState.RUNNING:
            return
        self._apply_settings()
        self._log(f"开始洗练: 通货{self.crafter.coordinates.get_currency_position()} "
                  f"物品{self.crafter.coordinates.get_item_position()}")
        self.crafter.start()

    def _on_pause(self):
        """暂停/继续"""
        if self.crafter.state == CraftingState.RUNNING:
            self.crafter.pause()
        elif self.crafter.state == CraftingState.PAUSED:
            self.crafter.resume()

    def _on_stop(self):
        """停止"""
        self.crafter.stop()

    def _on_emergency(self):
        """紧急停止"""
        self.crafter.stop()
        self._log("紧急停止!")

    def _register_hotkeys(self):
        """注册全局热键 F9-F12"""
        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    if key == keyboard.Key.f9:
                        self._ui_queue.put(("hotkey", "start", None, None))
                    elif key == keyboard.Key.f10:
                        self._ui_queue.put(("hotkey", "pause", None, None))
                    elif key == keyboard.Key.f11:
                        self._ui_queue.put(("hotkey", "stop", None, None))
                    elif key == keyboard.Key.f12:
                        self._ui_queue.put(("hotkey", "emergency", None, None))
                except Exception:
                    pass
                return True

            self.hotkey_listener = keyboard.Listener(on_press=on_press)
            self.hotkey_listener.daemon = True
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[GUI] 全局热键注册失败: {e}")

    def _on_close(self):
        """关闭窗口"""
        self._stop_capture()
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        self.crafter.stop()
        self.root.destroy()

    # ==================== 启动 ====================

    def start(self):
        """启动GUI"""
        self.root.mainloop()


if __name__ == "__main__":
    if CTk_AVAILABLE:
        app = MainWindow()
        app.start()
    else:
        print("需要安装 customtkinter: pip install customtkinter")
