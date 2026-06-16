import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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

SETTING_KEY_SOUNDS = "sounds"
SETTING_KEY_DISPLAY = "display"
SETTING_KEY_DEFAULTS = "defaults"

DEFAULT_SOUNDS = {
    "warning": "custom_TPBTLOW",
    "remaining_minutes": 5,
    "timeup": "custom_over",
    "timeup_scope_qa": True,
    "timeup_scope_presentation": True,
    "overtime": "voice",
    "overtime_minutes": 5,
    "overtime_scope_qa": True,
    "overtime_scope_presentation": False,
    "overtime_voice_text": "已进行",
}

DEFAULT_DISPLAY = {
    "opacity": 85,
    "float_size": "medium",
    "show_topic_name": True,
}

DEFAULT_TIMES = {
    "presentation_minutes": 10,
    "qa_minutes": 5,
}

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


class SettingsDialog(QDialog):
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._sound_combos: dict[str, QComboBox] = {}
        self._sound_spins: dict[str, QSpinBox] = {}
        self._audio = AudioPlayer()
        self._sound_content_widget = None
        self._sound_layout = None
        self._main_layout = None
        self._is_loading = True  # 标记是否正在加载设置，提前设置为True防止初始化时播放声音
        self._audio.reload_custom_sounds()
        self._setup_ui()
        self.load_settings()
        self._is_loading = False

    def _setup_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumSize(570, 530)
        self.resize(570, 530)
        style_sheet = """
QDialog {
    background-color: #FFFFFF;
    color: rgba(0,0,0,0.95);
    font-family: 'Inter, Microsoft YaHei, Segoe UI';
}

QPushButton {
    background-color: rgba(0,0,0,0.05);
    color: rgba(0,0,0,0.95);
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    min-width: 80px;
    height: 36px;
    max-height: 36px;
}

QPushButton:hover {
    background-color: rgba(0,0,0,0.08);
}

QPushButton:pressed {
    background-color: rgba(0,0,0,0.12);
}

QPushButton#primaryBtn {
    background-color: #0075DE;
    color: #FFFFFF;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    min-width: 100px;
    height: 36px;
    max-height: 36px;
}

QPushButton#secondaryBtn {
    background-color: rgba(0,0,0,0.05);
    color: rgba(0,0,0,0.95);
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    min-width: 100px;
    height: 36px;
    max-height: 36px;
}
"""
        self.setStyleSheet(style_sheet)

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
        self._setup_defaults_section(basic_layout)
        self._setup_display_section(basic_layout)
        basic_layout.addStretch()
        tabs.addTab(basic_tab, "基础配置")

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
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._main_layout.addLayout(btn_layout)

    def _setup_defaults_section(self, layout):
        defaults_label = QLabel("议题默认时间")
        defaults_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(defaults_label)

        pres_row = QHBoxLayout()
        pres_row.setSpacing(12)
        pres_label = QLabel("汇报时间")
        pres_label.setStyleSheet(ROW_LABEL_STYLE)
        pres_label.setFixedWidth(80)
        pres_row.addWidget(pres_label)
        self._default_presentation_spin = QSpinBox()
        self._default_presentation_spin.setRange(1, 999)
        self._default_presentation_spin.setValue(DEFAULT_TIMES["presentation_minutes"])
        self._default_presentation_spin.setSuffix(" 分钟")
        self._default_presentation_spin.setStyleSheet(INPUT_STYLE)
        pres_row.addWidget(self._default_presentation_spin)
        pres_row.addStretch()
        layout.addLayout(pres_row)

        disc_row = QHBoxLayout()
        disc_row.setSpacing(12)
        disc_label = QLabel("讨论时间")
        disc_label.setStyleSheet(ROW_LABEL_STYLE)
        disc_label.setFixedWidth(80)
        disc_row.addWidget(disc_label)
        self._default_qa_spin = QSpinBox()
        self._default_qa_spin.setRange(1, 999)
        self._default_qa_spin.setValue(DEFAULT_TIMES["qa_minutes"])
        self._default_qa_spin.setSuffix(" 分钟")
        self._default_qa_spin.setStyleSheet(INPUT_STYLE)
        disc_row.addWidget(self._default_qa_spin)
        disc_row.addStretch()
        layout.addLayout(disc_row)

    def _setup_display_section(self, layout):
        display_label = QLabel("显示设置")
        display_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(display_label)

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

        self._show_topic_checkbox = QCheckBox("在悬浮窗口显示议题名")
        self._show_topic_checkbox.setChecked(True)
        self._show_topic_checkbox.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
            f"spacing: 8px;"
        )
        layout.addWidget(self._show_topic_checkbox)

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

            # 根据声音类型构建预设列表
            # warning 和 timeup 不包含 voice（语音播报）选项
            current_preset_keys = []
            current_preset_names = []
            for key, name in SOUND_PRESETS.items():
                if (sound_type in ["warning", "timeup"]) and key == "voice":
                    continue  # warning 和 timeup 不显示语音播报
                current_preset_keys.append(key)
                current_preset_names.append(name)
            
            combo = QComboBox()
            combo.addItems(current_preset_names)
            combo.setProperty("preset_keys", current_preset_keys)
            combo.setStyleSheet(INPUT_STYLE)
            combo.currentIndexChanged.connect(
                lambda idx, st=sound_type, cb=combo: self._on_sound_changed(st, cb)
            )
            # 设置默认值
            default_key = DEFAULT_SOUNDS.get(sound_type)
            if default_key and default_key in current_preset_keys:
                combo.setCurrentIndex(current_preset_keys.index(default_key))
            self._sound_combos[sound_type] = combo
            combo_row.addWidget(combo)

            preview_btn = QPushButton("试听")
            preview_btn.setObjectName("secondaryBtn")
            preview_btn.setFixedWidth(60)
            preview_btn.clicked.connect(
                lambda checked=False, cb=combo: self._on_preview_sound(cb)
            )
            combo_row.addWidget(preview_btn)

            if sound_type == "warning":
                spin_label = QLabel("提前时长")
                spin_label.setStyleSheet(ROW_LABEL_STYLE)
                spin_label.setFixedWidth(60)
                combo_row.addWidget(spin_label)

                spin = QSpinBox()
                spin.setRange(1, 30)
                spin.setValue(DEFAULT_SOUNDS.get(f"{sound_type}_minutes", 5))
                spin.setSuffix(" 分钟")
                spin.setStyleSheet(INPUT_STYLE)
                self._sound_spins[sound_type] = spin
                combo_row.addWidget(spin)

            if sound_type == "overtime":
                spin_label = QLabel("提醒间隔")
                spin_label.setStyleSheet(ROW_LABEL_STYLE)
                spin_label.setFixedWidth(60)
                combo_row.addWidget(spin_label)

                spin = QSpinBox()
                spin.setRange(1, 30)
                spin.setValue(DEFAULT_SOUNDS.get(f"{sound_type}_minutes", 5))
                spin.setSuffix(" 分钟")
                spin.setStyleSheet(INPUT_STYLE)
                self._sound_spins[sound_type] = spin
                combo_row.addWidget(spin)

            combo_row.addStretch()

            type_layout.addLayout(combo_row)

            if sound_type == "timeup":
                scope_label = QLabel("适用范围")
                scope_label.setStyleSheet(ROW_LABEL_STYLE)
                scope_label.setFixedWidth(60)

                self._timeup_scope_pres_cb = QCheckBox("汇报阶段")
                self._timeup_scope_pres_cb.setChecked(True)
                self._timeup_scope_pres_cb.setStyleSheet(
                    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
                    f"spacing: 6px;"
                )

                self._timeup_scope_qa_cb = QCheckBox("讨论阶段")
                self._timeup_scope_qa_cb.setChecked(True)
                self._timeup_scope_qa_cb.setStyleSheet(
                    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
                    f"spacing: 6px;"
                )

                scope_row = QHBoxLayout()
                scope_row.setSpacing(10)
                scope_row.addWidget(scope_label)
                scope_row.addWidget(self._timeup_scope_pres_cb)
                scope_row.addWidget(self._timeup_scope_qa_cb)
                scope_row.addStretch()
                type_layout.addLayout(scope_row)

            if sound_type == "overtime":
                scope_label = QLabel("适用范围")
                scope_label.setStyleSheet(ROW_LABEL_STYLE)
                scope_label.setFixedWidth(60)

                self._overtime_scope_pres_cb = QCheckBox("汇报阶段")
                self._overtime_scope_pres_cb.setChecked(False)
                self._overtime_scope_pres_cb.setStyleSheet(
                    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
                    f"spacing: 6px;"
                )

                self._overtime_scope_qa_cb = QCheckBox("讨论阶段")
                self._overtime_scope_qa_cb.setChecked(True)
                self._overtime_scope_qa_cb.setStyleSheet(
                    f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
                    f"spacing: 6px;"
                )

                scope_row = QHBoxLayout()
                scope_row.setSpacing(10)
                scope_row.addWidget(scope_label)
                scope_row.addWidget(self._overtime_scope_pres_cb)
                scope_row.addWidget(self._overtime_scope_qa_cb)
                scope_row.addStretch()
                type_layout.addLayout(scope_row)

                voice_row = QHBoxLayout()
                voice_row.setSpacing(10)

                voice_label = QLabel("语音播报文案")
                voice_label.setStyleSheet(ROW_LABEL_STYLE)
                voice_label.setFixedWidth(90)
                voice_row.addWidget(voice_label)

                self._overtime_voice_edit = QLineEdit(DEFAULT_SOUNDS.get("overtime_voice_text", "已进行"))
                self._overtime_voice_edit.setReadOnly(True)
                self._overtime_voice_edit.setStyleSheet(INPUT_STYLE)
                self._overtime_voice_edit.setMaximumWidth(200)
                self._overtime_voice_edit.mouseDoubleClickEvent = (
                    lambda event, e=self._overtime_voice_edit: self._on_voice_text_double_click(e)
                )
                self._overtime_voice_edit.editingFinished.connect(
                    lambda e=self._overtime_voice_edit: e.setReadOnly(True)
                )
                voice_row.addWidget(self._overtime_voice_edit)
                voice_row.addStretch()
                type_layout.addLayout(voice_row)

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
            # 根据声音类型构建预设列表
            current_preset_keys = []
            current_preset_names = []
            for key, name in SOUND_PRESETS.items():
                if (sound_type in ["warning", "timeup"]) and key == "voice":
                    continue  # warning 和 timeup 不显示语音播报
                current_preset_keys.append(key)
                current_preset_names.append(name)
            
            combo.clear()
            combo.addItems(current_preset_names)
            combo.setProperty("preset_keys", current_preset_keys)
            
            # 恢复之前的选择
            if sound_type in current_settings:
                saved_key = current_settings[sound_type]
                if saved_key in current_preset_keys:
                    idx = current_preset_keys.index(saved_key)
                    combo.setCurrentIndex(idx)
                # 如果之前选中了 voice，但该类型不支持，则使用默认值
                elif (sound_type in ["warning", "timeup"]) and saved_key == "voice":
                    default_key = DEFAULT_SOUNDS.get(sound_type)
                    if default_key and default_key in current_preset_keys:
                        combo.setCurrentIndex(current_preset_keys.index(default_key))
        
        # 恢复spin的值
        for sound_type, spin in self._sound_spins.items():
            if f"{sound_type}_minutes" in current_settings:
                spin.setValue(current_settings[f"{sound_type}_minutes"])
        
        # 刷新完成
        self._is_loading = False

        if hasattr(self, '_overtime_voice_edit'):
            combo = self._sound_combos.get("overtime")
            if combo and combo.currentIndex() >= 0:
                keys = combo.property("preset_keys")
                is_voice = keys and keys[combo.currentIndex()] == "voice"
                self._overtime_voice_edit.setReadOnly(not is_voice)
                if not is_voice:
                    self._overtime_voice_edit.setStyleSheet(INPUT_STYLE + "color: rgba(0,0,0,0.4);")
                else:
                    self._overtime_voice_edit.setStyleSheet(INPUT_STYLE)

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

        if sound_type == "overtime" and hasattr(self, '_overtime_voice_edit'):
            if combo.currentIndex() >= 0:
                keys = combo.property("preset_keys")
                is_voice = keys and keys[combo.currentIndex()] == "voice"
                self._overtime_voice_edit.setReadOnly(not is_voice)
                if not is_voice:
                    self._overtime_voice_edit.setStyleSheet(
                        INPUT_STYLE + "color: rgba(0,0,0,0.4);"
                    )
                else:
                    self._overtime_voice_edit.setStyleSheet(INPUT_STYLE)

    def _on_voice_text_double_click(self, edit: QLineEdit):
        combo = self._sound_combos.get("overtime")
        if combo is None:
            return
        keys = combo.property("preset_keys")
        if keys and combo.currentIndex() >= 0 and keys[combo.currentIndex()] == "voice":
            edit.setReadOnly(False)
            edit.setFocus()
            edit.selectAll()

    def _on_preview_sound(self, combo: QComboBox):
        idx = combo.currentIndex()
        preset_keys = combo.property("preset_keys")
        if preset_keys and 0 <= idx < len(preset_keys):
            self._audio.preview(preset_keys[idx])

    def load_settings(self):
        # 1. Load Default Times
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
                self._show_topic_checkbox.setChecked(display.get("show_topic_name", True))
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
                if hasattr(self, '_overtime_scope_qa_cb'):
                    self._overtime_scope_qa_cb.setChecked(sounds.get("overtime_scope_qa", True))
                if hasattr(self, '_overtime_scope_pres_cb'):
                    self._overtime_scope_pres_cb.setChecked(sounds.get("overtime_scope_presentation", False))
                if hasattr(self, '_timeup_scope_qa_cb'):
                    self._timeup_scope_qa_cb.setChecked(sounds.get("timeup_scope_qa", True))
                if hasattr(self, '_timeup_scope_pres_cb'):
                    self._timeup_scope_pres_cb.setChecked(sounds.get("timeup_scope_presentation", True))
                if hasattr(self, '_overtime_voice_edit'):
                    self._overtime_voice_edit.setText(sounds.get("overtime_voice_text", "已进行"))
                    combo = self._sound_combos.get("overtime")
                    if combo and combo.currentIndex() >= 0:
                        keys = combo.property("preset_keys")
                        is_voice = keys and keys[combo.currentIndex()] == "voice"
                        self._overtime_voice_edit.setReadOnly(not is_voice)
                        if not is_voice:
                            self._overtime_voice_edit.setStyleSheet(INPUT_STYLE + "color: rgba(0,0,0,0.4);")
                        else:
                            self._overtime_voice_edit.setStyleSheet(INPUT_STYLE)
            except (json.JSONDecodeError, TypeError):
                pass

    def _on_save(self):
        # 1. Save Default Times
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
            "show_topic_name": self._show_topic_checkbox.isChecked(),
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
        if hasattr(self, '_overtime_scope_qa_cb'):
            sounds["overtime_scope_qa"] = self._overtime_scope_qa_cb.isChecked()
        if hasattr(self, '_overtime_scope_pres_cb'):
            sounds["overtime_scope_presentation"] = self._overtime_scope_pres_cb.isChecked()
        if hasattr(self, '_timeup_scope_qa_cb'):
            sounds["timeup_scope_qa"] = self._timeup_scope_qa_cb.isChecked()
        if hasattr(self, '_timeup_scope_pres_cb'):
            sounds["timeup_scope_presentation"] = self._timeup_scope_pres_cb.isChecked()
        if hasattr(self, '_overtime_voice_edit'):
            sounds["overtime_voice_text"] = self._overtime_voice_edit.text()
        self._db.set_setting(SETTING_KEY_SOUNDS, json.dumps(sounds))

        self.accept()
        self.settings_changed.emit()
