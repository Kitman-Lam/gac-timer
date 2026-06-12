import ctypes
import ctypes.wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77

WM_HOTKEY = 0x0312

HOTKEY_START_PAUSE = 1
HOTKEY_RESET = 2
HOTKEY_NEXT_PHASE = 3
HOTKEY_PREV_PHASE = 4

DEFAULT_HOTKEYS = {
    HOTKEY_START_PAUSE: (0, VK_F5),
    HOTKEY_RESET: (0, VK_F6),
    HOTKEY_NEXT_PHASE: (0, VK_F7),
    HOTKEY_PREV_PHASE: (0, VK_F8),
}


class _NativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self._callback(msg.wParam)
                return True
        return False


class HotkeyManager(QObject):
    hotkey_pressed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered: dict = {}
        self._filter = _NativeEventFilter(self._on_hotkey)
        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(self._filter)

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
