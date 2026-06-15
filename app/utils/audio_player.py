import math
import struct
import tempfile
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


def get_sound_dir() -> Path:
    """获取Sound文件夹路径"""
    # 在应用程序目录下创建Sound文件夹
    import os
    app_dir = Path.cwd()  # 使用当前工作目录
    sound_dir = app_dir / "Sound"
    sound_dir.mkdir(exist_ok=True)
    return sound_dir


SOUND_PRESETS = {
    "none": "无",
    "soft_chime": "柔和提示音",
    "clear_bell": "清脆铃声",
    "gentle_ding": "轻柔叮咚",
    "alert_beep": "警示蜂鸣",
    "low_bass": "低沉提醒",
    "double_tap": "双击提示",
    "rising_tone": "上升音调",
    "descending": "下降音调",
}

SOUND_TYPES = {
    "warning": "剩余时间提醒",
    "timeup": "时间到",
    "overtime": "超时提醒",
}

DEFAULT_SOUND_SELECTIONS = {
    "warning": "soft_chime",
    "timeup": "clear_bell",
    "overtime": "alert_beep",
}


def _generate_wav(frequency: int = 800, duration_ms: int = 300, sample_rate: int = 44100, volume: float = 0.5, fade_ms: int = 50) -> bytes:
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * 2
    byte_rate = sample_rate * 2
    block_align = 2
    bits_per_sample = 16

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    fade_samples = int(sample_rate * fade_ms / 1000)
    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        envelope = 1.0
        if i < fade_samples:
            envelope = i / fade_samples
        elif i > num_samples - fade_samples:
            envelope = (num_samples - i) / fade_samples
        value = int(32767 * envelope * math.sin(2 * math.pi * frequency * t) * volume)
        value = max(-32768, min(32767, value))
        samples.extend(struct.pack("<h", value))

    return header + bytes(samples)


def _generate_dual_tone_wav(freq1: int, freq2: int, duration_ms: int = 400, sample_rate: int = 44100, volume: float = 0.4) -> bytes:
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * 2
    byte_rate = sample_rate * 2
    block_align = 2
    bits_per_sample = 16

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    fade_samples = min(num_samples // 10, 500)
    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        envelope = 1.0
        if i < fade_samples:
            envelope = i / fade_samples
        elif i > num_samples - fade_samples:
            envelope = (num_samples - i) / fade_samples
        value = int(32767 * envelope * (math.sin(2 * math.pi * freq1 * t) + math.sin(2 * math.pi * freq2 * t)) * volume / 2)
        value = max(-32768, min(32767, value))
        samples.extend(struct.pack("<h", value))

    return header + bytes(samples)


def _generate_rising_tone_wav(start_freq: int = 400, end_freq: int = 800, duration_ms: int = 500, sample_rate: int = 44100, volume: float = 0.4) -> bytes:
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * 2
    byte_rate = sample_rate * 2
    block_align = 2
    bits_per_sample = 16

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    fade_samples = min(num_samples // 10, 500)
    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        progress = i / num_samples
        freq = start_freq + (end_freq - start_freq) * progress
        envelope = 1.0
        if i < fade_samples:
            envelope = i / fade_samples
        elif i > num_samples - fade_samples:
            envelope = (num_samples - i) / fade_samples
        value = int(32767 * envelope * math.sin(2 * math.pi * freq * t) * volume)
        value = max(-32768, min(32767, value))
        samples.extend(struct.pack("<h", value))

    return header + bytes(samples)


def _generate_double_tap_wav(freq: int = 800, sample_rate: int = 44100, volume: float = 0.5) -> bytes:
    tap_ms = 120
    gap_ms = 80
    total_ms = tap_ms * 2 + gap_ms
    num_samples = int(sample_rate * total_ms / 1000)
    data_size = num_samples * 2
    byte_rate = sample_rate * 2
    block_align = 2
    bits_per_sample = 16

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    tap_samples = int(sample_rate * tap_ms / 1000)
    gap_samples = int(sample_rate * gap_ms / 1000)
    fade_samples = min(tap_samples // 5, 200)
    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        if i < tap_samples:
            envelope = 1.0
            if i < fade_samples:
                envelope = i / fade_samples
            elif i > tap_samples - fade_samples:
                envelope = (tap_samples - i) / fade_samples
        elif i < tap_samples + gap_samples:
            envelope = 0.0
        else:
            local_i = i - tap_samples - gap_samples
            envelope = 1.0
            if local_i < fade_samples:
                envelope = local_i / fade_samples
            elif local_i > tap_samples - fade_samples:
                envelope = (tap_samples - local_i) / fade_samples
        value = int(32767 * envelope * math.sin(2 * math.pi * freq * t) * volume)
        value = max(-32768, min(32767, value))
        samples.extend(struct.pack("<h", value))

    return header + bytes(samples)


PRESET_GENERATORS = {
    "soft_chime": lambda: _generate_dual_tone_wav(523, 659, 500, volume=0.35),
    "clear_bell": lambda: _generate_wav(1047, 350, volume=0.4),
    "gentle_ding": lambda: _generate_dual_tone_wav(880, 1320, 600, volume=0.3),
    "alert_beep": lambda: _generate_wav(880, 400, volume=0.5),
    "low_bass": lambda: _generate_wav(220, 500, volume=0.45),
    "double_tap": lambda: _generate_double_tap_wav(780, volume=0.45),
    "rising_tone": lambda: _generate_rising_tone_wav(440, 880, 500, volume=0.4),
    "descending": lambda: _generate_rising_tone_wav(880, 440, 500, volume=0.4),
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
        self._temp_dir = tempfile.mkdtemp(prefix="gac_timer_")
        self._selections = dict(DEFAULT_SOUND_SELECTIONS)
        self._init_all_sounds()

    def _init_all_sounds(self):
        # 初始化预设声音
        for preset_key, generator in PRESET_GENERATORS.items():
            wav_data = generator()
            wav_path = Path(self._temp_dir) / f"{preset_key}.wav"
            wav_path.write_bytes(wav_data)

            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(wav_path)))
            effect.setVolume(0.8)
            self._sounds[preset_key] = effect
        
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
