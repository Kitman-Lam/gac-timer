import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWL_STYLE = -16
GWL_EXSTYLE = -20

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

LWA_ALPHA = 0x02

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

GWLP_HWNDPARENT = -8


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.wintypes.LONG),
        ("top", ctypes.wintypes.LONG),
        ("right", ctypes.wintypes.LONG),
        ("bottom", ctypes.wintypes.LONG),
    ]


def set_window_topmost(hwnd: int, topmost: bool = True) -> bool:
    try:
        flag = HWND_TOPMOST if topmost else HWND_NOTOPMOST
        result = user32.SetWindowPos(
            hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )
        return result != 0
    except Exception:
        return False


def set_window_transparency(hwnd: int, opacity: int) -> bool:
    try:
        opacity = max(0, min(255, opacity))
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_LAYERED
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        result = user32.SetLayeredWindowAttributes(hwnd, 0, opacity, LWA_ALPHA)
        return result != 0
    except Exception:
        return False


def remove_window_frame(hwnd: int) -> bool:
    try:
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~0x00CF0000
        style |= WS_POPUP
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        return True
    except Exception:
        return False


def get_window_pos(hwnd: int) -> tuple:
    try:
        rect = RECT()
        result = user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if result == 0:
            return (0, 0)
        return (rect.left, rect.top)
    except Exception:
        return (0, 0)


def set_window_pos(hwnd: int, x: int, y: int) -> bool:
    try:
        result = user32.SetWindowPos(
            hwnd, None, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE
        )
        return result != 0
    except Exception:
        return False


def set_window_owner(hwnd: int, owner_hwnd: int) -> bool:
    """设置窗口的拥有者"""
    try:
        result = user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner_hwnd)
        return result != 0
    except Exception:
        return False


def set_window_ex_noactivate(hwnd: int) -> bool:
    """设置 WS_EX_NOACTIVATE 扩展样式，使窗口不会在点击时激活"""
    try:
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        return True
    except Exception:
        return False


def set_window_ex_toolwindow(hwnd: int) -> bool:
    """设置 WS_EX_TOOLWINDOW 扩展样式，隐藏任务栏图标"""
    try:
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        return True
    except Exception:
        return False
