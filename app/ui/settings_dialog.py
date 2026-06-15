import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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
    "toggle_float": "",
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
    ("toggle_float", "显示/隐藏悬浮窗口"),
]

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
    f"border: 1px solid {BORDER_DEFAULT}; border-radius: 4px; "
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
        self.setText("按下新的按键组合")
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
        self._sound_content_widget = None
        self._sound_layout = None
        self._main_layout = None
        self._is_loading = False  # 标记是否正在加载设置
        self._audio.reload_custom_sounds()
        self._setup_ui()
        self._is_loading = True
        self.load_settings()
        self._is_loading = False

    def _setup_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumSize(500, 520)
        self.resize(500, 520)
        self.setStyleSheet(
            f"background-color: {BG_BASE}; color: {TEXT_PRIMARY}; "
            f"font-family: '{FONT_FAMILY}';"
        )

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 16, 16, 16)
        self._main_layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
            f"background-color: {BG_BASE}; padding: 12px; }}"
            f"QTabBar::tab {{ background-color: transparent; color: {TEXT_SECONDARY}; "
            f"padding: 8px 16px; border: none; border-bottom: 2px solid transparent; "
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MEDIUM}px; }}"
            f"QTabBar::tab:selected {{ color: {PRIMARY}; border-bottom: 2px solid {PRIMARY}; }}"
            f"QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}"
        )

        # 基础配置
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setContentsMargins(8, 8, 8, 8)
        basic_layout.setSpacing(12)
        self._setup_hotkey_section(basic_layout)
        self._setup_defaults_section(basic_layout)
        basic_layout.addStretch()
        tabs.addTab(basic_tab, "基础配置")

        # 悬浮窗口设置
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)
        display_layout.setContentsMargins(8, 8, 8, 8)
        display_layout.setSpacing(12)
        self._setup_display_section(display_layout)
        display_layout.addStretch()
        tabs.addTab(display_tab, "悬浮窗口设置")

        # 提示设置
        sound_tab = QWidget()
        sound_scroll = QScrollArea()
        sound_scroll.setWidgetResizable(True)
        sound_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: transparent; }} "
            f"QScrollBar:vertical {{ background-color: transparent; width: 10px; }} "
            f"QScrollBar::handle:vertical {{ background-color: rgba(0, 0, 0, 0.15); border-radius: 5px; min-height: 24px; }} "
            f"QScrollBar::add-line:vertical {{ height: 0px; }} "
            f"QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )
        sound_content = QWidget()
        self._sound_layout = QVBoxLayout(sound_content)
        self._sound_layout.setContentsMargins(8, 8, 8, 8)
        self._sound_layout.setSpacing(12)
        self._setup_sound_section(self._sound_layout)
        self._sound_layout.addStretch()
        sound_scroll.setWidget(sound_content)
        sound_tab_layout = QVBoxLayout(sound_tab)
        sound_tab_layout.setContentsMargins(0, 0, 0, 0)
        sound_tab_layout.addWidget(sound_scroll)
        tabs.addTab(sound_tab, "提示设置")

        self._main_layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._main_layout.addLayout(btn_layout)

    def _setup_hotkey_section(self, layout):
        hotkey_section = QLabel("快捷键设置")
        hotkey_section.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(hotkey_section)

        hotkey_hint = QLabel("点击快捷键按钮后，按下新的按键组合即可重新绑定")
        hotkey_hint.setStyleSheet(SUB_LABEL_STYLE)
        hotkey_hint.setWordWrap(True)
        layout.addWidget(hotkey_hint)

        for action_key, action_label in HOTKEY_ACTIONS:
            row = QHBoxLayout()
            row.setSpacing(12)

            label = QLabel(action_label)
            label.setStyleSheet(ROW_LABEL_STYLE)
            label.setFixedWidth(140)
            row.addWidget(label)

            btn = _HotkeyButton(DEFAULT_HOTKEYS.get(action_key, "按下配置快捷键"))
            btn.setFixedWidth(150)
            self._hotkey_buttons[action_key] = btn
            row.addWidget(btn)

            row.addStretch()
            layout.addLayout(row)

        layout.addSpacing(16)

    def _setup_defaults_section(self, layout):
        defaults_label = QLabel("新建议题默认时间")
        defaults_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(defaults_label)

        defaults_row = QHBoxLayout()
        defaults_row.setSpacing(12)

        pres_label = QLabel("汇报时间")
        pres_label.setStyleSheet(ROW_LABEL_STYLE)
        defaults_row.addWidget(pres_label)
        self._default_presentation_spin = QSpinBox()
        self._default_presentation_spin.setRange(1, 999)
        self._default_presentation_spin.setValue(DEFAULT_TIMES["presentation_minutes"])
        self._default_presentation_spin.setSuffix(" 分钟")
        self._default_presentation_spin.setStyleSheet(INPUT_STYLE)
        defaults_row.addWidget(self._default_presentation_spin)

        disc_label = QLabel("讨论时间")
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

    def _setup_display_section(self, layout):
        display_label = QLabel("显示设置")
        display_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(display_label)

        display_hint = QLabel("透明度、悬浮窗口大小效果需要点击「保存」后生效")
        display_hint.setStyleSheet(SUB_LABEL_STYLE)
        display_hint.setWordWrap(True)
        layout.addWidget(display_hint)

        opacity_label = QLabel("透明度")
        opacity_label.setStyleSheet(ROW_LABEL_STYLE)
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
        self._opacity_value_label.setText(f"{self._opacity_slider.value()}%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_value_label.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_value_label)
        layout.addLayout(opacity_row)

        size_label = QLabel("悬浮窗口大小")
        size_label.setStyleSheet(ROW_LABEL_STYLE)
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
            f"selection-background-color: {PRIMARY_LIGHT}; "
            f"font-family: '{FONT_FAMILY}'; }}"
        )
        size_row.addWidget(self._size_combo)
        size_row.addStretch()
        layout.addLayout(size_row)

    def _setup_sound_section(self, parent_layout):
        """设置声音部分的UI"""
        # 清除旧的声音控件
        self._sound_combos.clear()
        self._sound_spins.clear()

        # 提示音设置标题
        sound_section_layout = QHBoxLayout()
        sound_section_layout.setSpacing(10)
        
        sound_label = QLabel("提示音设置")
        sound_label.setStyleSheet(SECTION_LABEL_STYLE)
        sound_section_layout.addWidget(sound_label)
        sound_section_layout.addStretch()
        
        refresh_sound_btn = QPushButton("刷新声音列表")
        refresh_sound_btn.setObjectName("secondaryBtn")
        refresh_sound_btn.clicked.connect(self._on_refresh_sounds)
        sound_section_layout.addWidget(refresh_sound_btn)
        
        parent_layout.addLayout(sound_section_layout)

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

            sound_label_row = QLabel("提示音")
            sound_label_row.setStyleSheet(ROW_LABEL_STYLE)
            sound_label_row.setFixedWidth(60)
            combo_row.addWidget(sound_label_row)

            # 使用当前的声音预设列表（包含自定义声音）
            current_preset_keys = list(SOUND_PRESETS.keys())
            current_preset_names = list(SOUND_PRESETS.values())
            
            combo = QComboBox()
            combo.addItems(current_preset_names)
            combo.setProperty("preset_keys", current_preset_keys)
            combo.setStyleSheet(INPUT_STYLE)
            combo.currentIndexChanged.connect(
                lambda idx, st=sound_type, cb=combo: self._on_sound_changed(st, cb)
            )
            self._sound_combos[sound_type] = combo
            combo_row.addWidget(combo)

            preview_btn = QPushButton("试听")
            preview_btn.setObjectName("secondaryBtn")
            preview_btn.setFixedWidth(60)
            preview_btn.clicked.connect(
                lambda checked=False, cb=combo: self._on_preview_sound(cb)
            )
            combo_row.addWidget(preview_btn)
            combo_row.addStretch()

            type_layout.addLayout(combo_row)

            if sound_type != "timeup":
                spin_row = QHBoxLayout()
                spin_row.setSpacing(10)

                spin_label_text = "提醒间隔" if sound_type == "overtime" else "提前时长"
                spin_label = QLabel(spin_label_text)
                spin_label.setStyleSheet(ROW_LABEL_STYLE)
                spin_label.setFixedWidth(60)
                spin_row.addWidget(spin_label)

                spin = QSpinBox()
                spin.setRange(1, 30)
                spin.setValue(5)
                spin.setSuffix(" 分钟")
                spin.setStyleSheet(INPUT_STYLE)
                self._sound_spins[sound_type] = spin
                spin_row.addWidget(spin)
                spin_row.addStretch()
                type_layout.addLayout(spin_row)

            parent_layout.addLayout(type_layout)

    def _on_refresh_sounds(self):
        """刷新声音列表"""
        self._audio.reload_custom_sounds()

        # 先保存当前的设置值
        current_settings = {}
        for sound_type, combo in self._sound_combos.items():
            preset_keys = combo.property("preset_keys")
            if preset_keys:
                idx = combo.currentIndex()
                if 0 <= idx < len(preset_keys):
                    current_settings[sound_type] = preset_keys[idx]
        for sound_type, spin in self._sound_spins.items():
            current_settings[f"{sound_type}_minutes"] = spin.value()
        
        # 标记正在刷新，避免触发声音播放
        self._is_loading = True
        
        # 现在更新所有的下拉列表
        for sound_type, combo in self._sound_combos.items():
            current_preset_keys = list(SOUND_PRESETS.keys())
            current_preset_names = list(SOUND_PRESETS.values())
            combo.clear()
            combo.addItems(current_preset_names)
            combo.setProperty("preset_keys", current_preset_keys)
            
            # 恢复之前的选择
            if sound_type in current_settings:
                saved_key = current_settings[sound_type]
                if saved_key in current_preset_keys:
                    idx = current_preset_keys.index(saved_key)
                    combo.setCurrentIndex(idx)
        
        # 恢复spin的值
        for sound_type, spin in self._sound_spins.items():
            if f"{sound_type}_minutes" in current_settings:
                spin.setValue(current_settings[f"{sound_type}_minutes"])
        
        # 刷新完成
        self._is_loading = False
        
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, 
            "刷新完成", 
            "声音列表已刷新！"
        )

    def _on_sound_changed(self, sound_type: str, combo: QComboBox):
        if self._is_loading:
            return  # 加载设置期间不播放声音
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

    def load_settings(self):
        # 1. Load Hotkeys
        hotkeys_raw = self._db.get_setting(SETTING_KEY_HOTKEYS)
        if hotkeys_raw:
            try:
                hotkeys = json.loads(hotkeys_raw)
                for action_key, btn in self._hotkey_buttons.items():
                    saved_value = hotkeys.get(action_key, DEFAULT_HOTKEYS.get(action_key, "按下配置快捷键"))
                    btn.setText(saved_value if saved_value else "按下配置快捷键")
            except (json.JSONDecodeError, TypeError):
                pass

        # 2. Load Default Times
        defaults_raw = self._db.get_setting(SETTING_KEY_DEFAULTS)
        if defaults_raw:
            try:
                defaults = json.loads(defaults_raw)
                self._default_presentation_spin.setValue(
                    defaults.get("presentation_minutes", DEFAULT_TIMES["presentation_minutes"])
                )
                self._default_qa_spin.setValue(
                    defaults.get("qa_minutes", DEFAULT_TIMES["qa_minutes"])
                )
            except (json.JSONDecodeError, TypeError):
                pass

        # 3. Load Display Settings
        display_raw = self._db.get_setting(SETTING_KEY_DISPLAY)
        if display_raw:
            try:
                display = json.loads(display_raw)
                self._opacity_slider.setValue(display.get("opacity", DEFAULT_DISPLAY["opacity"]))
                size = display.get("float_size", DEFAULT_DISPLAY["float_size"])
                size_map = {"small": 0, "medium": 1, "large": 2}
                self._size_combo.setCurrentIndex(size_map.get(size, 1))
            except (json.JSONDecodeError, TypeError):
                pass

        # 4. Load Sound Settings
        sounds_raw = self._db.get_setting(SETTING_KEY_SOUNDS)
        if sounds_raw:
            try:
                sounds = json.loads(sounds_raw)
                for sound_type, combo in self._sound_combos.items():
                    preset_key = sounds.get(sound_type, DEFAULT_SOUNDS.get(sound_type))
                    # 使用当前的声音预设列表
                    current_preset_keys = combo.property("preset_keys")
                    if current_preset_keys:
                        preset_idx = current_preset_keys.index(preset_key) if preset_key in current_preset_keys else 0
                        combo.setCurrentIndex(preset_idx)
                for sound_type, spin in self._sound_spins.items():
                    spin.setValue(sounds.get(f"{sound_type}_minutes", DEFAULT_SOUNDS.get(f"{sound_type}_minutes", 5)))
            except (json.JSONDecodeError, TypeError):
                pass

    def _on_save(self):
        # 1. Save Hotkeys
        hotkeys = {}
        for action_key, btn in self._hotkey_buttons.items():
            value = btn.text()
            hotkeys[action_key] = value if value != "按下配置快捷键" else ""
        self._db.set_setting(SETTING_KEY_HOTKEYS, json.dumps(hotkeys))

        # 2. Save Default Times
        defaults = {
            "presentation_minutes": self._default_presentation_spin.value(),
            "qa_minutes": self._default_qa_spin.value(),
        }
        self._db.set_setting(SETTING_KEY_DEFAULTS, json.dumps(defaults))

        # 3. Save Display Settings
        size_map = {0: "small", 1: "medium", 2: "large"}
        display = {
            "opacity": self._opacity_slider.value(),
            "float_size": size_map[self._size_combo.currentIndex()],
        }
        self._db.set_setting(SETTING_KEY_DISPLAY, json.dumps(display))

        # 4. Save Sound Settings
        sounds = {}
        for sound_type, combo in self._sound_combos.items():
            current_preset_keys = combo.property("preset_keys")
            if current_preset_keys:
                sounds[sound_type] = current_preset_keys[combo.currentIndex()]
        for sound_type, spin in self._sound_spins.items():
            sounds[f"{sound_type}_minutes"] = spin.value()
        self._db.set_setting(SETTING_KEY_SOUNDS, json.dumps(sounds))

        self.accept()
        self.settings_changed.emit()
