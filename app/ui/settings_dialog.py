import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.ui.theme import (
    BG_BASE,
    BORDER_DEFAULT,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from app.utils.audio_player import (
    DEFAULT_SOUND_SELECTIONS,
    SOUND_PRESETS,
    SOUND_TYPES,
    AudioPlayer,
)

SETTING_KEY_HOTKEYS = "hotkeys"
SETTING_KEY_SOUNDS = "sounds"
SETTING_KEY_DISPLAY = "display"
SETTING_KEY_DEFAULTS = "defaults"

DEFAULT_HOTKEYS = {
    "start_pause": "",
    "reset": "",
    "next_phase": "",
    "prev_phase": "",
}

DEFAULT_SOUNDS = {
    "warning_selection": "soft_chime",
    "remaining_minutes": 5,
    "timeup_selection": "clear_bell",
    "overtime_selection": "alert_beep",
    "overtime_minutes": 5,
}

DEFAULT_DISPLAY = {
    "opacity": 85,
    "float_size": "medium",
}

DEFAULT_TIMES = {
    "presentation_minutes": 10,
    "qa_minutes": 5,
}

HOTKEY_ACTIONS = [
    ("start_pause", "开始/暂停"),
    ("reset", "重置"),
    ("next_phase", "下一阶段"),
    ("prev_phase", "上一阶段"),
]

SOUND_REMAINING = "remaining"
SOUND_TIMEUP = "timeup"
SOUND_OVERTIME = "overtime"

SECTION_LABEL_STYLE = (
    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
    f"font-weight: bold; font-family: '{FONT_FAMILY}'; "
    f"background: transparent; border: none;"
)

ROW_LABEL_STYLE = (
    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
)

SUB_LABEL_STYLE = (
    f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SMALL}px; "
    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
)

INPUT_STYLE = (
    f"background-color: #FFFFFF; color: rgba(0,0,0,0.9); "
    f"border: 1px solid #DDDDDD; border-radius: 4px; "
    f"padding: 6px 8px; font-size: {FONT_SIZE_MEDIUM}px; "
    f"font-family: '{FONT_FAMILY}';"
)


class _HotkeyButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._listening = False
        self.setObjectName("secondaryBtn")
        self.setMinimumWidth(80)
        self.clicked.connect(self._start_listening)
        self.setFocusPolicy(Qt.StrongFocus)

    def _start_listening(self):
        self._listening = True
        self.setText("按下新快捷键...")
        self.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {PRIMARY}; border-radius: 8px; "
            f"padding: 8px 20px; min-width: 80px; "
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MEDIUM}px; }}"
        )
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._listening:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key_Backspace, Qt.Key_Escape):
            self._cancel_listening()
            return

        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return

        parts = []
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")

        key_name = _key_to_string(key)
        if key_name:
            parts.append(key_name)

        if parts:
            combo = "+".join(parts)
            self.setText(combo)
            self._listening = False
            self.setStyleSheet("")

    def focusOutEvent(self, event):
        if self._listening:
            self._cancel_listening()
        super().focusOutEvent(event)

    def _cancel_listening(self):
        self._listening = False
        self.setStyleSheet("")

    @property
    def is_listening(self) -> bool:
        return self._listening


def _key_to_string(key: int) -> str:
    special = {
        Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
        Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
        Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
        Qt.Key_Space: "Space", Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter",
        Qt.Key_Tab: "Tab", Qt.Key_Backspace: "Backspace",
        Qt.Key_Insert: "Insert", Qt.Key_Delete: "Delete",
        Qt.Key_Home: "Home", Qt.Key_End: "End",
        Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown",
        Qt.Key_Up: "Up", Qt.Key_Down: "Down",
        Qt.Key_Left: "Left", Qt.Key_Right: "Right",
    }
    if key in special:
        return special[key]
    if 0x30 <= key <= 0x39:
        return chr(key)
    if 0x41 <= key <= 0x5A:
        return chr(key)
    return ""


class SettingsDialog(QDialog):
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._hotkey_buttons: dict[str, _HotkeyButton] = {}
        self._sound_combos: dict[str, QComboBox] = {}
        self._sound_spins: dict[str, QSpinBox] = {}
        self._audio = AudioPlayer()
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self):
        self.setWindowTitle("设置")
        self.setFixedSize(500, 600)
        self.setStyleSheet(
            f"background-color: {BG_BASE}; color: {TEXT_PRIMARY}; "
            f"font-family: '{FONT_FAMILY}';"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_hotkey_tab(), "默认配置")
        self._tabs.addTab(self._create_sound_tab(), "提示音设置")
        self._tabs.addTab(self._create_display_tab(), "显示设置")
        layout.addWidget(self._tabs, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _create_hotkey_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel("点击快捷键按钮后，按下新的按键组合即可重新绑定")
        hint.setStyleSheet(SUB_LABEL_STYLE)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        for action_key, action_label in HOTKEY_ACTIONS:
            row = QHBoxLayout()
            row.setSpacing(12)

            label = QLabel(action_label)
            label.setStyleSheet(ROW_LABEL_STYLE)
            label.setFixedWidth(100)
            row.addWidget(label)

            btn = _HotkeyButton(DEFAULT_HOTKEYS.get(action_key, ""))
            btn.setFixedWidth(150)
            self._hotkey_buttons[action_key] = btn
            row.addWidget(btn)

            row.addStretch()
            layout.addLayout(row)

        layout.addSpacing(16)

        defaults_label = QLabel("新建议题默认时间")
        defaults_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(defaults_label)

        defaults_row = QHBoxLayout()
        defaults_row.setSpacing(12)

        pres_label = QLabel("汇报")
        pres_label.setStyleSheet(ROW_LABEL_STYLE)
        defaults_row.addWidget(pres_label)
        self._default_presentation_spin = QSpinBox()
        self._default_presentation_spin.setRange(1, 999)
        self._default_presentation_spin.setValue(DEFAULT_TIMES["presentation_minutes"])
        self._default_presentation_spin.setSuffix(" 分钟")
        self._default_presentation_spin.setStyleSheet(INPUT_STYLE)
        defaults_row.addWidget(self._default_presentation_spin)

        disc_label = QLabel("讨论")
        disc_label.setStyleSheet(ROW_LABEL_STYLE)
        defaults_row.addWidget(disc_label)
        self._default_qa_spin = QSpinBox()
        self._default_qa_spin.setRange(1, 999)
        self._default_qa_spin.setValue(DEFAULT_TIMES["qa_minutes"])
        self._default_qa_spin.setSuffix(" 分钟")
        self._default_qa_spin.setStyleSheet(INPUT_STYLE)
        defaults_row.addWidget(self._default_qa_spin)

        defaults_row.addStretch()
        layout.addLayout(defaults_row)

        layout.addStretch()
        return widget

    def _create_sound_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        preset_keys = list(SOUND_PRESETS.keys())
        preset_names = list(SOUND_PRESETS.values())

        for sound_type, type_label in SOUND_TYPES.items():
            type_layout = QVBoxLayout()
            type_layout.setSpacing(8)

            type_header = QLabel(type_label)
            type_header.setStyleSheet(SECTION_LABEL_STYLE)
            type_layout.addWidget(type_header)

            combo_row = QHBoxLayout()
            combo_row.setSpacing(10)

            sound_label = QLabel("提示音")
            sound_label.setStyleSheet(ROW_LABEL_STYLE)
            sound_label.setFixedWidth(60)
            combo_row.addWidget(sound_label)

            combo = QComboBox()
            combo.addItems(preset_names)
            combo.setProperty("preset_keys", preset_keys)
            combo.setStyleSheet(
                f"QComboBox {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
                f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
                f"padding: 6px 12px; font-family: '{FONT_FAMILY}'; "
                f"font-size: {FONT_SIZE_MEDIUM}px; min-width: 160px; }}"
                f"QComboBox::drop-down {{ border: none; width: 24px; }}"
                f"QComboBox QAbstractItemView {{ background-color: #FFFFFF; "
                f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; "
                f"selection-background-color: {PRIMARY_LIGHT}; "
                f"font-family: '{FONT_FAMILY}'; }}"
            )
            combo.currentIndexChanged.connect(
                lambda idx, st=sound_type, cb=combo: self._on_sound_changed(st, cb)
            )
            self._sound_combos[sound_type] = combo
            combo_row.addWidget(combo)

            preview_btn = QPushButton("试听")
            preview_btn.setObjectName("secondaryBtn")
            preview_btn.setFixedWidth(60)
            preview_btn.clicked.connect(
                lambda checked, cb=combo: self._on_preview_sound(cb)
            )
            combo_row.addWidget(preview_btn)

            combo_row.addStretch()
            type_layout.addLayout(combo_row)

            if sound_type in ("warning", "overtime"):
                spin_row = QHBoxLayout()
                spin_row.setSpacing(10)

                if sound_type == "warning":
                    spin_label_text = "提醒时机"
                    spin_suffix = " 分钟前提醒"
                else:
                    spin_label_text = "提醒间隔"
                    spin_suffix = " 分钟提醒一次"

                spin_label = QLabel(spin_label_text)
                spin_label.setStyleSheet(ROW_LABEL_STYLE)
                spin_label.setFixedWidth(60)
                spin_row.addWidget(spin_label)

                spin = QSpinBox()
                spin.setRange(1, 60)
                spin.setValue(5)
                spin.setSuffix(spin_suffix)
                spin.setStyleSheet(
                    f"QSpinBox {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
                    f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
                    f"padding: 4px 8px; font-family: '{FONT_FAMILY}'; "
                    f"font-size: {FONT_SIZE_MEDIUM}px; min-width: 180px; }}"
                )
                self._sound_spins[sound_type] = spin
                spin_row.addWidget(spin)
                spin_row.addStretch()
                type_layout.addLayout(spin_row)

            layout.addLayout(type_layout)

        layout.addStretch()
        return widget

    def _on_sound_changed(self, sound_type: str, combo: QComboBox):
        idx = combo.currentIndex()
        preset_keys = combo.property("preset_keys")
        if preset_keys and 0 <= idx < len(preset_keys):
            selected_key = preset_keys[idx]
            self._audio.preview(selected_key)

    def _on_preview_sound(self, combo: QComboBox):
        idx = combo.currentIndex()
        preset_keys = combo.property("preset_keys")
        if preset_keys and 0 <= idx < len(preset_keys):
            self._audio.preview(preset_keys[idx])

    def _create_display_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        opacity_label = QLabel("透明度")
        opacity_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(opacity_label)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(10)

        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(85)
        self._opacity_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background-color: {BORDER_DEFAULT}; "
            f"height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background-color: {PRIMARY}; "
            f"width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}"
            f"QSlider::sub-page:horizontal {{ background-color: {PRIMARY}; "
            f"border-radius: 3px; }}"
        )
        opacity_row.addWidget(self._opacity_slider, 1)

        self._opacity_value_label = QLabel("85%")
        self._opacity_value_label.setStyleSheet(ROW_LABEL_STYLE)
        self._opacity_value_label.setFixedWidth(50)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_value_label.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_value_label)

        layout.addLayout(opacity_row)

        size_label = QLabel("悬浮窗口大小")
        size_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(size_label)

        size_row = QHBoxLayout()
        size_row.setSpacing(10)

        self._size_combo = QComboBox()
        self._size_combo.addItems(["小", "中", "大"])
        self._size_combo.setCurrentIndex(1)
        self._size_combo.setStyleSheet(
            f"QComboBox {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
            f"padding: 6px 12px; font-family: '{FONT_FAMILY}'; "
            f"font-size: {FONT_SIZE_MEDIUM}px; min-width: 120px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background-color: #FFFFFF; "
            f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; "
            f"selection-background-color: {PRIMARY_LIGHT}; }}"
        )
        size_row.addWidget(self._size_combo)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addStretch()
        return widget

    def load_settings(self):
        hotkeys_raw = self._db.get_setting(SETTING_KEY_HOTKEYS)
        if hotkeys_raw:
            try:
                hotkeys = json.loads(hotkeys_raw)
            except (json.JSONDecodeError, TypeError):
                hotkeys = dict(DEFAULT_HOTKEYS)
        else:
            hotkeys = dict(DEFAULT_HOTKEYS)

        for action_key, btn in self._hotkey_buttons.items():
            combo = hotkeys.get(action_key, DEFAULT_HOTKEYS.get(action_key, ""))
            btn.setText(combo)

        sounds_raw = self._db.get_setting(SETTING_KEY_SOUNDS)
        if sounds_raw:
            try:
                sounds = json.loads(sounds_raw)
            except (json.JSONDecodeError, TypeError):
                sounds = dict(DEFAULT_SOUNDS)
        else:
            sounds = dict(DEFAULT_SOUNDS)

        preset_keys = list(SOUND_PRESETS.keys())
        for sound_type, combo in self._sound_combos.items():
            selection_key = f"{sound_type}_selection"
            selected = sounds.get(selection_key, "none")
            if selected in preset_keys:
                idx = preset_keys.index(selected)
            else:
                idx = 0
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        for sound_type, spin in self._sound_spins.items():
            spin.setValue(sounds.get(f"{sound_type}_minutes", 5))

        display_raw = self._db.get_setting(SETTING_KEY_DISPLAY)
        if display_raw:
            try:
                display = json.loads(display_raw)
            except (json.JSONDecodeError, TypeError):
                display = dict(DEFAULT_DISPLAY)
        else:
            display = dict(DEFAULT_DISPLAY)

        self._opacity_slider.setValue(
            display.get("opacity", DEFAULT_DISPLAY["opacity"])
        )

        size_map = {"small": 0, "medium": 1, "large": 2}
        size_key = display.get("float_size", DEFAULT_DISPLAY["float_size"])
        self._size_combo.setCurrentIndex(size_map.get(size_key, 1))

        defaults_raw = self._db.get_setting(SETTING_KEY_DEFAULTS)
        if defaults_raw:
            try:
                defaults = json.loads(defaults_raw)
            except (json.JSONDecodeError, TypeError):
                defaults = dict(DEFAULT_TIMES)
        else:
            defaults = dict(DEFAULT_TIMES)
        self._default_presentation_spin.setValue(
            defaults.get("presentation_minutes", DEFAULT_TIMES["presentation_minutes"])
        )
        self._default_qa_spin.setValue(
            defaults.get("qa_minutes", DEFAULT_TIMES["qa_minutes"])
        )

    def save_settings(self):
        hotkeys = {}
        for action_key, btn in self._hotkey_buttons.items():
            hotkeys[action_key] = btn.text()
        self._db.set_setting(SETTING_KEY_HOTKEYS, json.dumps(hotkeys, ensure_ascii=False))

        sounds = dict(DEFAULT_SOUNDS)
        preset_keys = list(SOUND_PRESETS.keys())
        for sound_type, combo in self._sound_combos.items():
            idx = combo.currentIndex()
            if 0 <= idx < len(preset_keys):
                sounds[f"{sound_type}_selection"] = preset_keys[idx]
            else:
                sounds[f"{sound_type}_selection"] = "none"

        for sound_type, spin in self._sound_spins.items():
            sounds[f"{sound_type}_minutes"] = spin.value()

        self._db.set_setting(SETTING_KEY_SOUNDS, json.dumps(sounds, ensure_ascii=False))

        self._audio.set_selection("warning", sounds.get("warning_selection", "none"))
        self._audio.set_selection("timeup", sounds.get("timeup_selection", "none"))
        self._audio.set_selection("overtime", sounds.get("overtime_selection", "none"))

        size_keys = ["small", "medium", "large"]
        display = {
            "opacity": self._opacity_slider.value(),
            "float_size": size_keys[self._size_combo.currentIndex()],
        }
        self._db.set_setting(SETTING_KEY_DISPLAY, json.dumps(display, ensure_ascii=False))

        defaults = {
            "presentation_minutes": self._default_presentation_spin.value(),
            "qa_minutes": self._default_qa_spin.value(),
        }
        self._db.set_setting(SETTING_KEY_DEFAULTS, json.dumps(defaults, ensure_ascii=False))

    def _on_save(self):
        self.save_settings()
        self.settings_changed.emit()
        self.accept()
