"""剪贴板操作模块 - 读取游戏物品信息"""

import sys
import time
from typing import Optional

# 根据平台选择剪贴板库
if sys.platform == 'win32':
    try:
        import win32clipboard
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


class ClipboardManager:
    """剪贴板管理器"""
    
    def __init__(self):
        """初始化剪贴板管理器"""
        self.platform = sys.platform
        self._original_content = None
        
        # 检查可用的剪贴板库
        if self.platform == 'win32' and WIN32_AVAILABLE:
            self.method = 'win32'
        elif PYPERCLIP_AVAILABLE:
            self.method = 'pyperclip'
        else:
            self.method = 'fallback'
            print("[剪贴板] 警告: 无可用的剪贴板库，将使用备用方法")
    
    def get_text(self) -> Optional[str]:
        """从剪贴板获取文本
        
        Returns:
            剪贴板文本，失败返回None
        """
        try:
            if self.method == 'win32':
                return self._get_text_win32()
            elif self.method == 'pyperclip':
                return self._get_text_pyperclip()
            else:
                return self._get_text_fallback()
        except Exception as e:
            print(f"[剪贴板] 读取失败: {e}")
            return None
    
    def set_text(self, text: str) -> bool:
        """设置剪贴板文本
        
        Args:
            text: 要设置的文本
        
        Returns:
            是否成功
        """
        try:
            if self.method == 'win32':
                return self._set_text_win32(text)
            elif self.method == 'pyperclip':
                return self._set_text_pyperclip(text)
            else:
                return self._set_text_fallback(text)
        except Exception as e:
            print(f"[剪贴板] 设置失败: {e}")
            return False
    
    def save(self):
        """保存当前剪贴板内容"""
        self._original_content = self.get_text()
    
    def restore(self):
        """恢复之前保存的剪贴板内容"""
        if self._original_content is not None:
            self.set_text(self._original_content)
    
    def clear(self):
        """清空剪贴板"""
        self.set_text("")
    
    def _get_text_win32(self) -> Optional[str]:
        """使用win32clipboard获取文本"""
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return text
        except:
            return None
        finally:
            win32clipboard.CloseClipboard()
    
    def _set_text_win32(self, text: str) -> bool:
        """使用win32clipboard设置文本"""
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            return True
        except:
            return False
        finally:
            win32clipboard.CloseClipboard()
    
    def _get_text_pyperclip(self) -> Optional[str]:
        """使用pyperclip获取文本"""
        return pyperclip.paste()
    
    def _set_text_pyperclip(self, text: str) -> bool:
        """使用pyperclip设置文本"""
        pyperclip.copy(text)
        return True
    
    def _get_text_fallback(self) -> Optional[str]:
        """备用方法获取文本（使用tkinter）"""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return text
        except:
            return None
    
    def _set_text_fallback(self, text: str) -> bool:
        """备用方法设置文本（使用tkinter）"""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return True
        except:
            return False


# 测试代码
if __name__ == "__main__":
    print("剪贴板模块测试")
    print("=" * 40)
    
    cm = ClipboardManager()
    print(f"使用方法: {cm.method}")
    print(f"平台: {cm.platform}")
    
    # 测试读取
    text = cm.get_text()
    print(f"\n当前剪贴板内容: {text[:100] if text else '空'}")
    
    # 测试写入
    test_text = "测试文本 Hello World"
    if cm.set_text(test_text):
        print(f"写入成功: {test_text}")
        
        # 验证
        verify = cm.get_text()
        print(f"验证读取: {verify}")
