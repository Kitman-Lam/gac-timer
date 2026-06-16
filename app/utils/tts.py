import ctypes
from ctypes import wintypes, byref, POINTER, c_void_p, c_ulong, c_wchar_p
import threading

CLSID_SpVoice = "{96749377-3391-11D2-9EE3-00C04F797396}"
IID_ISpVoice = "{6C44DF74-72B9-4992-A1EC-EF996E0422D4}"
SVSFlagsAsync = 1


def _guid_from_string(s):
    buf = ctypes.create_unicode_buffer(s)
    guid = ctypes.create_string_buffer(16)
    ctypes.windll.ole32.CLSIDFromString(buf, guid)
    return guid.raw


class _VoiceNotifier:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._available = False
            cls._instance._pVoice = None
            cls._instance._vtbl = None
            cls._instance._init()
        return cls._instance

    def _init(self):
        try:
            ctypes.windll.ole32.CoInitialize(None)

            pVoice = c_void_p()
            clsid_bytes = _guid_from_string(CLSID_SpVoice)
            iid_bytes = _guid_from_string(IID_ISpVoice)

            hr = ctypes.windll.ole32.CoCreateInstance(
                clsid_bytes, None, 0x17,
                iid_bytes, byref(pVoice)
            )
            if hr < 0 or not pVoice:
                return

            self._pVoice = pVoice
            pvtbl_ptr = ctypes.cast(pVoice, POINTER(c_void_p)).contents
            self._vtbl = ctypes.cast(pvtbl_ptr, POINTER(c_void_p))

            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self):
        return self._available

    def speak(self, text):
        if not self._available:
            return
        try:
            self._speak_impl(text)
        except Exception:
            pass

    def _speak_impl(self, text):
        WINFUNCTYPE = ctypes.WINFUNCTYPE
        SpeakProto = WINFUNCTYPE(
            ctypes.c_long,
            c_void_p, c_wchar_p, c_ulong, POINTER(c_ulong)
        )
        speak_func = SpeakProto(self._vtbl[20])
        pwcs = c_wchar_p(text)
        pul_stream = c_ulong(0)
        speak_func(self._pVoice, pwcs, SVSFlagsAsync, byref(pul_stream))


def get_voice_notifier():
    return _VoiceNotifier()


def speak_async(text):
    notifier = get_voice_notifier()
    if notifier.available:
        threading.Thread(target=notifier.speak, args=(text,), daemon=True).start()