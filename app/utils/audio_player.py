import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


def get_sound_dir() -> Path:
    """获取Sound文件夹路径"""
    import sys
    # 在PyInstaller打包后的环境中，使用sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        # 打包后的临时目录
        return Path(sys._MEIPASS) / "Sound"
    # 开发环境中，使用当前脚本所在目录的上级目录
    return Path(__file__).parent.parent.parent / "Sound"


SOUND_PRESETS = {
    "none": "无",
}

SOUND_TYPES = {
    "warning": "剩余时间提醒",
    "timeup": "时间到",
    "overtime": "超时提醒",
}

DEFAULT_SOUND_SELECTIONS = {
    "warning": "custom_TPBTLOW",
    "timeup": "custom_over",
    "overtime": "custom_001",
}


class AudioPlayer:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._sounds: dict = {}
        self._selections = dict(DEFAULT_SOUND_SELECTIONS)
        self._init_all_sounds()

    def _init_all_sounds(self):
        # 加载Sound文件夹中的自定义声音
        self._load_custom_sounds()

    def _load_custom_sounds(self):
        """加载Sound文件夹中的自定义WAV文件"""
        sound_dir = get_sound_dir()
        if not sound_dir.exists():
            return

        wav_files = list(sound_dir.glob("*.wav"))
        for wav_file in wav_files:
            try:
                file_key = f"custom_{wav_file.stem}"
                if file_key in self._sounds:
                    continue

                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(wav_file)))
                effect.setVolume(0.8)
                self._sounds[file_key] = effect
                SOUND_PRESETS[file_key] = wav_file.stem
            except Exception as e:
                print(f"[AudioPlayer] Failed to load sound {wav_file}: {e}")

    def reload_custom_sounds(self):
        """重新加载自定义声音"""
        # 清除现有的自定义声音
        keys_to_remove = [k for k in SOUND_PRESETS if k.startswith("custom_")]
        for key in keys_to_remove:
            if key in self._sounds:
                del self._sounds[key]
            del SOUND_PRESETS[key]
        
        # 重新加载
        self._load_custom_sounds()

    def play(self, sound_type: str):
        selection = self._selections.get(sound_type, "none")
        if selection == "none":
            return
        sound = self._sounds.get(selection)
        if sound is not None:
            sound.play()

    def preview(self, preset_key: str):
        if preset_key == "none":
            return
        sound = self._sounds.get(preset_key)
        if sound is not None:
            sound.play()

    def set_selection(self, sound_type: str, preset_key: str):
        self._selections[sound_type] = preset_key

    def get_selection(self, sound_type: str) -> str:
        return self._selections.get(sound_type, "none")

    def is_enabled(self, sound_type: str) -> bool:
        return self._selections.get(sound_type, "none") != "none"
