import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


def get_sound_dir() -> Path:
    import sys
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "Sound"
    return Path(__file__).parent.parent.parent / "Sound"


SOUND_PRESETS = {
    "none": "无",
    "voice": "语音播报",
}

SOUND_TYPES = {
    "warning": "剩余时间提醒",
    "timeup": "时间到",
    "overtime": "超时提醒",
}

DEFAULT_SOUND_SELECTIONS = {
    "warning": "custom_TPBTLOW",
    "timeup": "custom_over",
    "overtime": "voice",
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
        self._active_players = []
        self._init_all_sounds()

    def _init_all_sounds(self):
        self._load_custom_sounds()

    def _load_custom_sounds(self):
        sound_dir = get_sound_dir()
        if not sound_dir.exists():
            return

        wav_files = list(sound_dir.glob("*.wav"))
        for wav_file in wav_files:
            try:
                file_key = f"custom_{wav_file.stem}"
                if file_key in self._sounds:
                    continue

                self._sounds[file_key] = str(wav_file)
                SOUND_PRESETS[file_key] = wav_file.stem
            except Exception as e:
                print(f"[AudioPlayer] Failed to load sound {wav_file}: {e}")

    def reload_custom_sounds(self):
        keys_to_remove = [k for k in SOUND_PRESETS if k.startswith("custom_")]
        for key in keys_to_remove:
            if key in self._sounds:
                del self._sounds[key]
            del SOUND_PRESETS[key]

        self._load_custom_sounds()

    def _play_file(self, file_path: str):
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        audio_output.setVolume(0.8)
        player.setAudioOutput(audio_output)
        player.setSource(QUrl.fromLocalFile(file_path))

        self._active_players.append(player)
        player.mediaStatusChanged.connect(
            lambda status, p=player, ao=audio_output:
            self._on_player_finished(status, p, ao)
        )
        player.play()

    def _on_player_finished(self, status, player, audio_output):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            player.stop()
            if player in self._active_players:
                self._active_players.remove(player)

    def play(self, sound_type: str):
        selection = self._selections.get(sound_type, "none")
        if selection == "none":
            return
        if selection == "voice":
            return
        file_path = self._sounds.get(selection)
        if file_path is not None:
            self._play_file(file_path)

    def play_overtime_voice(self, minutes: int, phase: str = ""):
        if self._selections.get("overtime", "none") != "voice":
            return
        from app.utils.tts import speak_async
        phase_name = "汇报" if phase == "presentation" else "讨论"
        speak_async(f"{phase_name}已延时{minutes}分钟")

    def preview(self, preset_key: str):
        if preset_key == "none":
            return
        if preset_key == "voice":
            from app.utils.tts import speak_async
            speak_async("语音播报测试")
            return
        file_path = self._sounds.get(preset_key)
        if file_path is not None:
            self._play_file(file_path)

    def set_selection(self, sound_type: str, preset_key: str):
        self._selections[sound_type] = preset_key

    def get_selection(self, sound_type: str) -> str:
        return self._selections.get(sound_type, "none")

    def is_enabled(self, sound_type: str) -> bool:
        return self._selections.get(sound_type, "none") != "none"