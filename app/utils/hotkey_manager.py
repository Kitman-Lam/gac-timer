import ctypes
import ctypes.wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

WM_HOTKEY = 0x0312

HOTKEY_TOGGLE_FLOAT = 1
HOTKEY_FLOAT_SMALL = 2
HOTKEY_FLOAT_MEDIUM = 3
HOTKEY_FLOAT_LARGE = 4

DEFAULT_HOTKEYS = {
    HOTKEY_FLOAT_SMALL: (MOD_CONTROL, VK_F9),
    HOTKEY_FLOAT_MEDIUM: (MOD_CONTROL, VK_F10),
    HOTKEY_FLOAT_LARGE: (MOD_CONTROL, VK_F11),
    HOTKEY_TOGGLE_FLOAT: (MOD_CONTROL, VK_F12),
}


class _NativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._callback(msg.wParam)
                    return True
            except Exception:
                pass
        return False


class HotkeyManager(QObject):
    hotkey_pressed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered: dict = {}
        self._filter = _NativeEventFilter(self._on_hotkey)
        self._install_filter()

    def _install_filter(self):
        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(self._filter)
        else:
            import sys
            for obj in sys.modules.values():
                if hasattr(obj, '__class__') and obj.__class__.__name__ == 'QApplication':
                    obj.installNativeEventFilter(self._filter)
                    break

    def _on_hotkey(self, hotkey_id: int):
        self.hotkey_pressed.emit(hotkey_id)

    def register_hotkey(self, hotkey_id: int, modifier: int, key: int) -> bool:
        try:
            if hotkey_id in self._registered:
                self.unregister_hotkey(hotkey_id)
            result = user32.RegisterHotKey(None, hotkey_id, modifier, key)
            if result:
                self._registered[hotkey_id] = (modifier, key)
                return True
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, "热键注册失败",
                f"热键已被其他程序占用（ID: {hotkey_id}），请在设置中更换热键。"
            )
            return False
        except Exception:
            return False

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        try:
            if hotkey_id not in self._registered:
                return False
            result = user32.UnregisterHotKey(None, hotkey_id)
            if result:
                del self._registered[hotkey_id]
                return True
            return False
        except Exception:
            return False

    def unregister_all(self):
        for hotkey_id in list(self._registered.keys()):
            self.unregister_hotkey(hotkey_id)

    def register_defaults(self):
        for hotkey_id, (modifier, key) in DEFAULT_HOTKEYS.items():
            self.register_hotkey(hotkey_id, modifier, key)

    def __del__(self):
        self.unregister_all()
        app = QApplication.instance()
        if app and self._filter:
            app.removeNativeEventFilter(self._filter)
