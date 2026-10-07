"""繁体中文 PoE crafting prototype: calibrate, inspect, then use Chaos Orbs."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from item_parser import parse_item
from engine import Cancelled, Condition, Crafter, evaluate, parse_tier_spec
from windows_io import WindowsAdapter, clipboard, dpi_awareness, down
from timing import TimingSettings


class App:
    def __init__(self, hidden=False):
        dpi_awareness()
        self.root = tk.Tk()
        if hidden:
            self.root.withdraw()
        self.root.title('PoE2 混沌石洗练 · v0.1.6 实机验证版')
        self.root.geometry('980x820')
        self.adapter = WindowsAdapter()
        self.messages = queue.Queue()
        self.crafter = Crafter(self.adapter, self.log, lambda item: self.messages.put(('item', item)))
        self.worker = None
        self.conditions = []
        self.condition_mode = tk.StringVar(value='全部满足才停止')
        self.probed = False
        self.last_keys = set()
        self.pending_action = None
        self.last_item = None
        self.status = tk.StringVar(value='请将游戏切到前台按 F6 绑定')
        self.combo = tk.StringVar(value='Ctrl+C')
        self.continuous = tk.BooleanVar(value=True)
        self.speed = tk.StringVar(value='3')
        self.random_enabled = tk.BooleanVar(value=True)
        self.random_min = tk.StringVar(value='50')
        self.random_max = tk.StringVar(value='150')
        self.limit = tk.StringVar(value='100')
        self.keyword = tk.StringVar()
        self.tier = tk.StringVar()
        self.minimum = tk.StringVar()
        self.index = tk.StringVar()
        self.kind = tk.StringVar(value='前后缀')
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, textvariable=self.status, wraplength=930).pack(anchor='w')
        ttk.Label(outer, text='游戏前台：F6 绑定窗口 → 鼠标移到混沌石按 F7 → 移到装备按 F8 → F5 只读测试 → F9 开始\nF10 停止。切换窗口会停止。第一次使用请将最大次数设为 1。').pack(anchor='w', pady=8)
        row = ttk.Frame(outer)
        row.pack(fill='x')
        ttk.Label(row, text='复制组合键').pack(side='left')
        combo = ttk.Combobox(row, textvariable=self.combo, values=['Ctrl+C', 'Ctrl+Alt+C'], state='readonly', width=15)
        combo.pack(side='left', padx=5)
        combo.bind('<<ComboboxSelected>>', self.combo_changed)
        ttk.Label(row, text='最大操作次数').pack(side='left', padx=5)
        ttk.Entry(row, textvariable=self.limit, width=7).pack(side='left')
        ttk.Button(row, text='粘贴剪贴板并解析（不操作游戏）', command=self.paste).pack(side='left', padx=10)
        self.export_button = ttk.Button(row, text='导出诊断', command=self.export)
        self.export_button.pack(side='left')
        ttk.Checkbutton(outer, text='连续使用：按住Shift，右键选中一次混沌石；每次左键后读取装备并判断',
                        variable=self.continuous, command=self.mode_changed).pack(anchor='w', pady=(6, 0))
        row = ttk.Frame(outer)
        row.pack(fill='x', pady=(6, 0))
        ttk.Label(row, text='速度倍率（越大越快）').pack(side='left')
        ttk.Combobox(row, textvariable=self.speed, values=['0.5', '1', '2', '3', '4', '5'], width=5).pack(side='left', padx=5)
        ttk.Checkbutton(row, text='随机额外延迟', variable=self.random_enabled).pack(side='left', padx=8)
        ttk.Entry(row, textvariable=self.random_min, width=6).pack(side='left')
        ttk.Label(row, text='至').pack(side='left', padx=4)
        ttk.Entry(row, textvariable=self.random_max, width=6).pack(side='left')
        ttk.Label(row, text='毫秒；下次启动生效').pack(side='left', padx=5)
        ttk.Label(outer, text='实际词缀（符文、装备面板、需求不参与停止条件）').pack(anchor='w', pady=(12, 4))
        self.tree = ttk.Treeview(outer, columns=('kind', 'name', 'tier', 'flags', 'stats'), show='headings', height=8)
        for col, label, width in [('kind', '类型', 60), ('name', '词缀名', 95), ('tier', '阶层', 45), ('flags', '标记', 95), ('stats', '属性 · 实际值 / 范围保留', 570)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(fill='x')
        self.tree.bind('<<TreeviewSelect>>', self.select_stat)
        mode_row = ttk.Frame(outer)
        mode_row.pack(fill='x', pady=(12, 4))
        ttk.Label(mode_row, text='停止条件模式').pack(side='left')
        mode_box = ttk.Combobox(mode_row, textvariable=self.condition_mode,
                               values=['全部满足才停止', '任意一个满足就停止'], state='readonly', width=22)
        mode_box.pack(side='left', padx=5)
        mode_box.bind('<<ComboboxSelected>>', self.condition_mode_changed)
        ttk.Label(mode_row, text='下次启动生效').pack(side='left')
        ttk.Label(outer, text='每条条件：阶层填1为T1，填1-3接受T1至T3；留空不限。数值是下限，两者都填须同时满足。').pack(anchor='w', pady=(0, 4))
        row = ttk.Frame(outer)
        row.pack(fill='x')
        for label, var, width in [('繁体关键词', self.keyword, 23), ('阶层', self.tier, 8), ('数值≥', self.minimum, 7), ('数值位置', self.index, 4)]:
            ttk.Label(row, text=label).pack(side='left', padx=(3, 2))
            ttk.Entry(row, textvariable=var, width=width).pack(side='left')
        ttk.Combobox(row, textvariable=self.kind, values=['前后缀', '前缀', '后缀'], state='readonly', width=8).pack(side='left', padx=5)
        ttk.Button(row, text='添加', command=self.add).pack(side='left')
        ttk.Button(row, text='删除选中', command=self.delete).pack(side='left', padx=5)
        ttk.Label(outer, text='点击词缀行可填入对应属性模板。多数值词缀需指定数值位置：从 1 开始，如火焰伤害的下限为 1、上限为 2。').pack(anchor='w', pady=3)
        self.condition_list = tk.Listbox(outer, height=4)
        self.condition_list.pack(fill='x')
        row = ttk.Frame(outer)
        row.pack(fill='x', pady=7)
        ttk.Button(row, text='开始（3秒后，请切回游戏）', command=lambda: self.schedule('start')).pack(side='left')
        ttk.Button(row, text='只读测试（3秒后，请切回游戏）', command=lambda: self.schedule('probe')).pack(side='left', padx=5)
        ttk.Button(row, text='停止 F10', command=self.stop).pack(side='left')
        self.logbox = scrolledtext.ScrolledText(outer, height=9, state='disabled', wrap='word')
        self.logbox.pack(fill='both', expand=True)
        self.stat_rows = {}
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(30, self.poll)

    def busy(self):
        return self.worker is not None and self.worker.is_alive()

    def log(self, message):
        self.messages.put(('log', f'{datetime.now():%H:%M:%S} {message}'))

    def show_item(self, item):
        self.last_item = item
        self.tree.delete(*self.tree.get_children())
        self.stat_rows.clear()
        for mod in item.modifiers:
            flags = ' / '.join(v for v, present in [('破裂', mod.fractured), ('工艺', mod.crafted)] if present)
            for stat in mod.stats:
                row = self.tree.insert('', 'end', values=('前缀' if mod.kind == 'prefix' else '后缀' if mod.kind == 'suffix' else '固有', mod.name, mod.tier or '未知', flags, stat.text))
                self.stat_rows[row] = mod, stat
        self.log(f'读取：{item.name} / {item.base} / 物等 {item.item_level}；{len(item.modifiers)}组词缀；污染标记 {item.corrupted}')
        for warning in item.warnings:
            self.log(warning)

    def select_stat(self, _=None):
        selected = self.tree.selection()
        if selected:
            mod, stat = self.stat_rows[selected[0]]
            self.keyword.set(stat.template.replace('#', '').strip())
            self.tier.set(str(mod.tier) if mod.tier else '')
            self.kind.set('前缀' if mod.kind == 'prefix' else '后缀' if mod.kind == 'suffix' else '前后缀')
            self.minimum.set('')
            self.index.set('')

    def add(self):
        if self.busy():
            self.log('请停止后再修改条件')
            return
        try:
            tier, tier_max = parse_tier_spec(self.tier.get())
            condition = Condition(self.keyword.get().strip(), tier,
                                  self.minimum.get().strip() or None, int(self.index.get()) - 1 if self.index.get().strip() else None,
                                  {'前后缀': None, '前缀': 'prefix', '后缀': 'suffix'}[self.kind.get()], tier_max=tier_max)
            from item_parser import Item, check_condition
            check_condition(Item(), **vars(condition))  # Validate rule before starting.
            self.conditions.append(condition)
            tier_label = '不限' if tier is None else f'T{tier}' if tier_max is None else f'T{tier}-T{tier_max}'
            self.condition_list.insert('end', f'{self.kind.get()} | {condition.keyword} | {tier_label} | 数值≥{condition.minimum or "不限"} | 位置{self.index.get() or "自动"}')
            if self.last_item:
                self.log(f'当前装备条件预览：{evaluate(self.last_item, self.conditions, self.condition_mode_value())[0]}')
        except Exception as error:
            self.log(f'条件错误：{error}')

    def condition_mode_value(self):
        return 'any' if self.condition_mode.get() == '任意一个满足就停止' else 'all'

    def condition_mode_changed(self, _=None):
        self.log(f'停止条件模式：{self.condition_mode.get()}；下次启动生效')
        if self.last_item and self.conditions and not self.busy():
            self.log(f'当前装备条件预览：{evaluate(self.last_item, self.conditions, self.condition_mode_value())[0]}')

    def delete(self):
        if not self.busy():
            for index in reversed(self.condition_list.curselection()):
                self.conditions.pop(index)
                self.condition_list.delete(index)

    def combo_changed(self, _=None):
        if self.busy():
            self.stop()
        self.probed = False
        self.log('复制组合键已更改，请重新做只读测试')

    def mode_changed(self):
        if self.busy():
            self.stop()
        self.log('下次启动将使用' + ('连续使用模式' if self.continuous.get() else '每轮重新选通货模式'))

    def paste(self):
        if self.busy():
            return
        try:
            self.show_item(parse_item(clipboard() or ''))
        except Exception as error:
            self.log(f'解析失败：{error}')

    def stop(self):
        self.pending_action = None
        self.crafter.stop.set()
        self.log('已请求停止')

    def schedule(self, action):
        if self.busy() or self.pending_action:
            return
        self.pending_action = action
        self.log('3秒后执行，请切回游戏')
        self.root.after(3000, lambda: self.dispatch_pending(action))

    def dispatch_pending(self, action):
        if self.pending_action == action:
            self.pending_action = None
            self.launch(action)

    def launch(self, action):
        if self.busy():
            return
        try:
            self.adapter.guard()
            if '装备' not in self.adapter.points:
                raise ValueError('未校准装备坐标')
            if action == 'start':
                if not self.probed:
                    raise ValueError('必须先完成一次成功的游戏只读测试')
                if '混沌石' not in self.adapter.points:
                    raise ValueError('未校准混沌石坐标')
                if not self.conditions:
                    raise ValueError('未设置停止条件')
            limit = int(self.limit.get())
            conditions = list(self.conditions)
            condition_mode = self.condition_mode_value()
            timing = self.timing_from_ui()
            self.adapter.combo = self.combo.get()
            self.adapter.continuous = self.continuous.get()
            self.adapter.timing = timing
            jitter = f'{timing.random_min_ms:g}至{timing.random_max_ms:g}ms' if timing.random_enabled else '关闭'
            self.log(f'速度 {timing.speed:g}倍；随机额外延迟 {jitter}；每次使用后仍读取并判断装备')
            self.log(f'停止条件模式：{self.condition_mode.get()}')
            self.crafter.stop.clear()
            self.worker = threading.Thread(target=self.work, args=(action, conditions, limit, condition_mode), daemon=True)
            self.worker.start()
        except Exception as error:
            self.log(f'无法启动：{error}')

    def timing_from_ui(self):
        try:
            return TimingSettings(speed=float(self.speed.get()), random_enabled=self.random_enabled.get(),
                                  random_min_ms=float(self.random_min.get()), random_max_ms=float(self.random_max.get()))
        except ValueError as error:
            raise ValueError(f'速度/延迟设置错误：{error}') from error

    def work(self, action, conditions, limit, condition_mode):
        try:
            if action == 'probe':
                item = self.crafter.read()
                self.messages.put(('probed', True))
                if conditions:
                    self.log(f'当前装备条件判断：{evaluate(item, conditions, condition_mode)[0]}')
                self.log('只读测试成功；尚未使用通货')
            else:
                self.crafter.run(conditions, limit, condition_mode)
        except Cancelled:
            self.log('操作已停止')
        except Exception as error:
            self.log(f'已停止：{error}')
        finally:
            self.adapter.release()

    def hotkey(self, key):
        try:
            if key == 0x79:
                self.stop()
            elif self.busy() or self.pending_action:
                return
            elif key == 0x75:
                label = self.adapter.bind()
                self.probed = False
                self.status.set(label + '；坐标已重置，请用F7/F8校准')
            elif key in (0x76, 0x77):
                name = '混沌石' if key == 0x76 else '装备'
                self.log(f'{name}客户区坐标：{self.adapter.capture(name)}')
                self.probed = False
            elif key == 0x74:
                self.launch('probe')
            elif key == 0x78:
                self.launch('start')
        except Exception as error:
            self.log(str(error))

    def poll(self):
        # Process stop first so a simultaneous F9/F10 does not launch a new run.
        keys = {key for key in range(0x74, 0x7A) if down(key)}
        pressed = keys - self.last_keys
        self.last_keys = keys
        if 0x79 in pressed:
            self.hotkey(0x79)
        else:
            for key in sorted(pressed):
                self.hotkey(key)
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == 'item':
                    self.show_item(value)
                elif kind == 'probed':
                    self.probed = value
                else:
                    self.logbox.configure(state='normal')
                    self.logbox.insert('end', value + '\n')
                    self.logbox.see('end')
                    self.logbox.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(30, self.poll)

    def export(self):
        try:
            # Use a user-owned writable directory even for a packaged EXE.
            directory = Path.home() / 'Documents' / 'PoE2Crafter' / 'diagnostics'
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / f'diagnostic-{datetime.now():%Y%m%d-%H%M%S}.json'
            payload = {'window': self.status.get(), 'points': self.adapter.points, 'copy_combo': self.combo.get(),
                       'continuous': self.continuous.get(),
                       'timing_active': asdict(self.adapter.timing),
                       'timing_inputs': {'speed': self.speed.get(), 'random_enabled': self.random_enabled.get(),
                                         'random_min_ms': self.random_min.get(), 'random_max_ms': self.random_max.get()},
                       'condition_mode': self.condition_mode_value(),
                       'conditions': [vars(c) for c in self.conditions], 'item': asdict(self.last_item) if self.last_item else None,
                       'log': self.logbox.get('1.0', 'end')}
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            self.log(f'诊断已保存：{target}')
        except Exception as error:
            self.log(f'导出失败：{error}')

    def close(self):
        self.stop()
        self.wait_close()

    def wait_close(self):
        if self.busy():
            self.root.after(50, self.wait_close)
        else:
            self.root.destroy()


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == '--self-test':
        application = App(hidden=True)
        application.show_item(parse_item(Path(sys.argv[2]).read_text(encoding='utf-8-sig')))
        application.keyword.set('攻擊速度')
        application.tier.set('1-3')
        application.minimum.set('28')
        application.kind.set('后缀')
        application.add()
        application.root.update_idletasks()
        report = {'rows': len(application.tree.get_children()), 'conditions': len(application.conditions),
                  'evaluation': evaluate(application.last_item, application.conditions)[0],
                  'timing': asdict(application.timing_from_ui()),
                  'window_bound': bool(application.adapter.hwnd)}
        Path(sys.argv[3]).write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
        application.root.destroy()
    else:
        App().root.mainloop()
