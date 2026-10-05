"""Windows APIs only. No injection, screen recognition or external packages."""
import ctypes as c
from ctypes import wintypes as w
import os
import time
from engine import Cancelled
from timing import TimingSettings

u = c.WinDLL('user32', use_last_error=True)
k = c.WinDLL('kernel32', use_last_error=True)
ULONG_PTR = c.c_size_t


class MOUSEINPUT(c.Structure):
    _fields_ = [('dx', w.LONG), ('dy', w.LONG), ('mouseData', w.DWORD), ('dwFlags', w.DWORD), ('time', w.DWORD), ('dwExtraInfo', ULONG_PTR)]


class KEYBDINPUT(c.Structure):
    _fields_ = [('wVk', w.WORD), ('wScan', w.WORD), ('dwFlags', w.DWORD), ('time', w.DWORD), ('dwExtraInfo', ULONG_PTR)]


class INPUTUNION(c.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT)]


class INPUT(c.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', w.DWORD), ('data', INPUTUNION)]


u.GetForegroundWindow.restype = w.HWND
u.IsWindow.argtypes = [w.HWND]
u.IsIconic.argtypes = [w.HWND]
u.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
u.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u.ScreenToClient.argtypes = [w.HWND, c.POINTER(w.POINT)]
u.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
u.SendInput.argtypes = [w.UINT, c.POINTER(INPUT), c.c_int]
u.SendInput.restype = w.UINT
u.GetClipboardData.argtypes = [w.UINT]
u.GetClipboardData.restype = w.HANDLE
u.OpenClipboard.argtypes = [w.HWND]
u.GetAsyncKeyState.argtypes = [c.c_int]
u.GetAsyncKeyState.restype = c.c_short
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
k.CloseHandle.argtypes = [w.HANDLE]
k.GlobalLock.argtypes = [w.HGLOBAL]
k.GlobalLock.restype = c.c_void_p
k.GlobalUnlock.argtypes = [w.HGLOBAL]


def dpi_awareness():
    try:
        u.SetProcessDpiAwarenessContext.argtypes = [c.c_void_p]
        u.SetProcessDpiAwarenessContext(c.c_void_p(-4))
    except AttributeError:
        u.SetProcessDPIAware()


def down(vk):
    return bool(u.GetAsyncKeyState(vk) & 0x8000)


def clipboard():
    if not u.OpenClipboard(None):
        return None
    try:
        handle = u.GetClipboardData(13)
        if not handle:
            return None
        pointer = k.GlobalLock(handle)
        if not pointer:
            return None
        try:
            return c.wstring_at(pointer)
        finally:
            k.GlobalUnlock(handle)
    finally:
        u.CloseClipboard()


class WindowsAdapter:
    def __init__(self):
        self.hwnd = None
        self.pid = None
        self.size = None
        self.points = {}
        self.combo = 'Ctrl+C'
        self.continuous = True
        self.currency_selected = False
        self.timing = TimingSettings()
        self.held_keys = set()
        self.held_buttons = set()

    def bind(self):
        hwnd = u.GetForegroundWindow()
        pid = w.DWORD()
        u.GetWindowThreadProcessId(hwnd, c.byref(pid))
        process = k.OpenProcess(0x1000, False, pid.value)
        if not process:
            raise OSError('无法读取游戏进程信息；检查程序与游戏的权限级别')
        try:
            buffer = c.create_unicode_buffer(32768)
            length = w.DWORD(len(buffer))
            if not k.QueryFullProcessImageNameW(process, 0, buffer, c.byref(length)):
                raise c.WinError(c.get_last_error())
            exe = os.path.basename(buffer.value)
        finally:
            k.CloseHandle(process)
        if 'pathofexile' not in exe.lower():
            raise ValueError(f'当前前台进程不是流放之路：{exe}')
        rect = w.RECT()
        if not u.GetClientRect(hwnd, c.byref(rect)):
            raise c.WinError()
        self.hwnd, self.pid = hwnd, pid.value
        self.size = rect.right, rect.bottom
        self.points.clear()
        title = c.create_unicode_buffer(1024)
        u.GetWindowTextW(hwnd, title, len(title))
        return f'{title.value} / {exe} / {self.size[0]}×{self.size[1]}'

    def guard(self):
        if not self.hwnd or not u.IsWindow(self.hwnd):
            raise ValueError('游戏窗口未绑定或已关闭；在游戏前台按F6绑定')
        pid = w.DWORD()
        u.GetWindowThreadProcessId(self.hwnd, c.byref(pid))
        if pid.value != self.pid:
            raise ValueError('游戏进程变化，请重新绑定')
        if u.GetForegroundWindow() != self.hwnd or u.IsIconic(self.hwnd):
            raise ValueError('游戏失去前台焦点，已停止')
        rect = w.RECT()
        if not u.GetClientRect(self.hwnd, c.byref(rect)):
            raise c.WinError()
        if (rect.right, rect.bottom) != self.size:
            raise ValueError('游戏窗口尺寸改变，请重新绑定和校准坐标')

    def capture(self, name):
        self.guard()
        point = w.POINT()
        if not u.GetCursorPos(c.byref(point)) or not u.ScreenToClient(self.hwnd, c.byref(point)):
            raise c.WinError()
        if not (0 <= point.x < self.size[0] and 0 <= point.y < self.size[1]):
            raise ValueError('鼠标不在游戏客户区内')
        self.points[name] = point.x, point.y
        return self.points[name]

    def wait(self, seconds, stop):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if stop.is_set():
                raise Cancelled()
            self.guard()
            time.sleep(min(0.02, max(0, deadline - time.monotonic())))

    def send(self, event):
        self.guard()
        if u.SendInput(1, c.byref(event), c.sizeof(INPUT)) != 1:
            raise OSError('Windows拒绝模拟输入；检查工具与游戏的权限级别')

    def pause(self, phase, stop):
        self.wait(self.timing.seconds(phase), stop)

    def key(self, vk, release=False, guarded=True):
        event = INPUT(type=1, ki=KEYBDINPUT(vk, 0, 2 if release else 0, 0, 0))
        if guarded:
            self.send(event)
        else:
            u.SendInput(1, c.byref(event), c.sizeof(INPUT))
        self.held_keys.discard(vk) if release else self.held_keys.add(vk)

    def move(self, name):
        self.guard()
        if name not in self.points:
            raise ValueError(f'未校准{name}坐标')
        point = w.POINT(*self.points[name])
        if not u.ClientToScreen(self.hwnd, c.byref(point)) or not u.SetCursorPos(point.x, point.y):
            raise c.WinError()

    def click(self, button, stop):
        flags = (2, 4) if button == 'left' else (8, 16)
        self.send(INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, flags[0], 0, 0)))
        self.held_buttons.add(button)
        try:
            self.pause('click', stop)
        finally:
            # Always release even when the foreground window changes.
            u.SendInput(1, c.byref(INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, flags[1], 0, 0))), c.sizeof(INPUT))
            self.held_buttons.discard(button)

    def copy_item(self, stop):
        return self.copy_at('装备', stop)

    def copy_at(self, name, stop):
        self.move(name)
        self.pause('hover', stop)
        sequence = u.GetClipboardSequenceNumber()
        keys = [0x11, 0x43] if self.combo == 'Ctrl+C' else [0x11, 0x12, 0x43]
        try:
            for vk in keys:
                self.key(vk)
                self.pause('key', stop)
        finally:
            for vk in reversed(keys):
                if vk in self.held_keys:
                    self.key(vk, release=True, guarded=False)
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline:
            self.wait(0.01, stop)
            if u.GetClipboardSequenceNumber() != sequence:
                text = clipboard()
                if text and text.strip():
                    return text
        raise ValueError(f'复制{name}后剪贴板没有更新；检查坐标、权限和复制组合键')

    def use_chaos(self, stop):
        if stop.is_set():
            raise Cancelled()
        self.guard()
        if any(down(vk) and vk not in self.held_keys for vk in (0x10, 0x11, 0x12)):
            raise ValueError('检测到Shift/Ctrl/Alt按下，请松开修饰键再启动')
        # Apply one bounded random pause before the next operation. This wait
        # uses the same interruptible foreground/stop checks as all other waits.
        self.wait(self.timing.random_seconds(), stop)
        # This client copies equipment only. The currency position is supplied
        # by calibration; verify success by re-reading equipment in the engine.
        if not self.continuous or not self.currency_selected:
            self.move('混沌石')
            self.pause('move', stop)
            if self.continuous:
                self.key(0x10)
                self.pause('shift', stop)
            self.click('right', stop)
            self.pause('select', stop)
            self.currency_selected = self.continuous
        elif 0x10 not in self.held_keys or not down(0x10):
            raise ValueError('连续模式的Shift状态改变，已停止，请重新启动')
        self.move('装备')
        self.pause('move', stop)
        self.click('left', stop)
        self.pause('settle', stop)

    def release(self):
        for vk in list(self.held_keys):
            self.key(vk, release=True, guarded=False)
        for button in list(self.held_buttons):
            flag = 4 if button == 'left' else 16
            u.SendInput(1, c.byref(INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, flag, 0, 0))), c.sizeof(INPUT))
        self.held_buttons.clear()
        self.currency_selected = False
