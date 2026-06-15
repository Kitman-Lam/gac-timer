import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.core.timer_engine import MeetingTimerController, TimerEngine
from app.ui.config_panel import ConfigPanel
from app.ui.float_widget import FloatTimer
from app.ui.history_panel import HistoryPanel
from app.ui.settings_dialog import (
    DEFAULT_DISPLAY,
    DEFAULT_SOUNDS,
    SETTING_KEY_DEFAULTS,
    SETTING_KEY_DISPLAY,
    SETTING_KEY_SOUNDS,
    SettingsDialog,
)
from app.utils.hotkey_manager import DEFAULT_HOTKEYS

SETTING_KEY_HOTKEYS = "hotkeys"
from app.ui.stats_dialog import StatsDialog
from app.ui.theme import (
    BG_BASE,
    BORDER_DEFAULT,
    DANGER,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    PRIMARY,
    PRIMARY_LIGHT,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
    format_time,
)
from app.ui.timer_circle import TimerCircle
from app.utils.audio_player import AudioPlayer
from app.utils.hotkey_manager import (
    HOTKEY_TOGGLE_FLOAT,
    HOTKEY_FLOAT_SMALL,
    HOTKEY_FLOAT_MEDIUM,
    HOTKEY_FLOAT_LARGE,
    HotkeyManager,
)


class _TopicTable(QTableWidget):
    topic_order_changed = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.topic_order_changed.emit()


class _NavBar(QWidget):
    nav_changed = Signal(int)
    settings_clicked = Signal()
    float_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navBar")
        self.setFixedHeight(48)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._active_index = -1
        self._nav_buttons = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(4)

        brand = QLabel()
        import sys
        import os
        if hasattr(sys, '_MEIPASS'):
            logo_path = os.path.join(sys._MEIPASS, 'LOGO.png')
        else:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'LOGO.png')
        brand_pixmap = QPixmap(logo_path)
        brand_pixmap = brand_pixmap.scaledToHeight(32, Qt.SmoothTransformation)
        brand.setPixmap(brand_pixmap)
        brand.setFixedHeight(32)
        brand.setAlignment(Qt.AlignVCenter)
        brand.setStyleSheet(
            "background: transparent; border: none;"
        )
        layout.addWidget(brand)
        layout.addStretch()

        for text, idx in [("会议安排", 0), ("当前会议", 1), ("历史记录", 2)]:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            layout.addWidget(btn)
            self._nav_buttons.append((btn, idx))
            if idx == 1:
                btn.setVisible(False)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_btn)

        self._float_btn = QPushButton("悬浮窗口")
        self._float_btn.setObjectName("primaryBtn")
        self._float_btn.setCheckable(True)
        self._float_btn.setCursor(Qt.PointingHandCursor)
        self._float_btn.setVisible(True)
        self._float_btn.setChecked(True)
        self._float_btn.clicked.connect(lambda checked: self.float_toggled.emit(checked))
        layout.addWidget(self._float_btn)

        self._update_nav_styles()

    def _on_nav_clicked(self, index):
        self.nav_changed.emit(index)

    def set_active(self, index):
        self._active_index = index
        self._update_nav_styles()

    def set_float_visible(self, visible):
        self._float_btn.setVisible(visible)

    def set_meeting_nav_visible(self, visible: bool):
        for btn, idx in self._nav_buttons:
            if idx == 1:
                btn.setVisible(visible)

    def set_float_checked(self, checked):
        self._float_btn.setChecked(checked)

    def is_float_checked(self):
        return self._float_btn.isChecked()

    def _update_nav_styles(self):
        for btn, idx in self._nav_buttons:
            if idx == self._active_index:
                btn.setStyleSheet(
                    f"QPushButton {{ color: {TEXT_PRIMARY}; border: none; "
                    f"border-bottom: 2px solid {PRIMARY}; "
                    f"padding: 12px 16px; font-size: 14px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; }}"
                    f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ color: {TEXT_SECONDARY}; border: none; "
                    f"border-bottom: 2px solid transparent; "
                    f"padding: 12px 16px; font-size: 14px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; }}"
                    f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
                )
        self._settings_btn.setStyleSheet(
            f"QPushButton {{ color: {TEXT_SECONDARY}; border: none; "
            f"border-bottom: 2px solid transparent; "
            f"padding: 12px 16px; font-size: 14px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
        )


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._db = DatabaseManager()
        self._controller = MeetingTimerController(self._db, self)
        self._hotkey_manager = HotkeyManager(self)
        self._audio = AudioPlayer()
        self._float_timer = None
        self._current_meeting_id = None
        self._warning_triggered = False
        self._overtime_triggered = False
        self._remaining_minutes_triggered = False
        self._last_overtime_minute = 0

        self._setup_ui()
        self._connect_signals()
        self._load_audio_settings()

        self.setWindowTitle("会帮手")
        self.setMinimumSize(900, 650)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._navbar = _NavBar()
        self._navbar.nav_changed.connect(self._on_nav_changed)
        self._navbar.settings_clicked.connect(self._on_open_settings)
        self._navbar.float_toggled.connect(self._on_toggle_float)
        main_layout.addWidget(self._navbar)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {BORDER_DEFAULT};")
        main_layout.addWidget(separator)

        self._stacked = QStackedWidget()
        main_layout.addWidget(self._stacked, 1)

        self._config_panel = ConfigPanel()
        self._stacked.addWidget(self._config_panel)

        self._timer_page = self._create_timer_page()
        self._stacked.addWidget(self._timer_page)

        self._history_panel = HistoryPanel()
        self._stacked.addWidget(self._history_panel)

    def _create_timer_page(self) -> QWidget:
        page = QWidget()
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(24)

        left_widget = QWidget()
        left_widget.setMaximumWidth(600)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.setAlignment(Qt.AlignCenter)

        self._meeting_name_label = QLabel()
        self._meeting_name_label.setAlignment(Qt.AlignCenter)
        self._meeting_name_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 500; "
            f"background: transparent; border: none;"
        )
        left_layout.addWidget(self._meeting_name_label)

        self._topic_name_label = QLabel()
        self._topic_name_label.setAlignment(Qt.AlignCenter)
        self._topic_name_label.setWordWrap(True)
        self._topic_name_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 600; "
            f"line-height: 1.40; letter-spacing: -0.125px; "
            f"background: transparent; border: none;"
        )
        left_layout.addWidget(self._topic_name_label)

        self._phase_name_label = QLabel()
        self._phase_name_label.setAlignment(Qt.AlignCenter)
        self._phase_name_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 16px; font-weight: 400; "
            f"background: transparent; border: none;"
        )
        left_layout.addWidget(self._phase_name_label)

        self._time_display_label = QLabel("00:00")
        self._time_display_label.setAlignment(Qt.AlignCenter)
        self._time_display_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 40px; font-weight: 700; "
            f"line-height: 1.50; background: transparent; border: none;"
        )
        left_layout.addWidget(self._time_display_label)

        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 8, 0, 8)
        stats_layout.setSpacing(64)

        for title_text, value_init, label_attr in [
            ("计划时间", "--:--", "_planned_time_label"),
            ("状态", "待开始", "_status_label"),
        ]:
            col = QWidget()
            col_lyt = QVBoxLayout(col)
            col_lyt.setContentsMargins(0, 0, 0, 0)
            col_lyt.setSpacing(4)
            col_lyt.setAlignment(Qt.AlignCenter)

            t = QLabel(title_text)
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 500; "
                f"background: transparent; border: none;"
            )

            v = QLabel(value_init)
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 400; "
                f"background: transparent; border: none;"
            )

            col_lyt.addWidget(t)
            col_lyt.addWidget(v)
            stats_layout.addWidget(col)
            setattr(self, label_attr, v)

        left_layout.addWidget(stats_container)

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(10)
        btn_row1.setAlignment(Qt.AlignCenter)

        secondary_style = (
            "QPushButton {"
            "  background-color: rgba(0, 0, 0, 0.05);"
            "  color: rgba(0, 0, 0, 0.95);"
            "  border: 1px solid transparent;"
            "  padding: 6px 8px;"
            "  border-radius: 6px;"
            "  font-size: 14px;"
            "  font-weight: 500;"
            "  min-width: 80px;"
            "  height: 32px;"
            "  max-height: 32px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(0, 0, 0, 0.08);"
            "}"
            "QPushButton:pressed {"
            "  background-color: rgba(0, 0, 0, 0.12);"
            "}"
        )

        self._enter_discussion_btn = QPushButton("进入讨论")
        self._enter_discussion_btn.setStyleSheet(secondary_style)
        self._enter_discussion_btn.clicked.connect(self._on_enter_discussion)
        btn_row1.addWidget(self._enter_discussion_btn)

        self._pause_resume_btn = QPushButton("暂停")
        self._pause_resume_btn.setStyleSheet(secondary_style)
        self._pause_resume_btn.clicked.connect(self._on_pause_resume)
        btn_row1.addWidget(self._pause_resume_btn)

        self._reset_phase_btn = QPushButton("重置")
        self._reset_phase_btn.setStyleSheet(secondary_style)
        self._reset_phase_btn.clicked.connect(self._on_reset_phase)
        btn_row1.addWidget(self._reset_phase_btn)

        self._next_topic_btn = QPushButton("下一议题")
        self._next_topic_btn.setStyleSheet(secondary_style)
        self._next_topic_btn.clicked.connect(self._on_next_topic)
        btn_row1.addWidget(self._next_topic_btn)

        left_layout.addLayout(btn_row1)

        self._add_temp_topic_btn = QPushButton("+ 临时议题")
        self._add_temp_topic_btn.setStyleSheet(secondary_style)
        self._add_temp_topic_btn.clicked.connect(self._on_add_temp_topic)
        left_layout.addWidget(self._add_temp_topic_btn)

        self._end_meeting_btn = QPushButton("结束会议")
        self._end_meeting_btn.setObjectName("primaryBtn")
        self._end_meeting_btn.clicked.connect(self._on_end_meeting)
        left_layout.addWidget(self._end_meeting_btn)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        topic_header = QLabel("议题计划")
        topic_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        right_layout.addWidget(topic_header)

        self._topic_table = _TopicTable()
        self._topic_table.setColumnCount(5)
        self._topic_table.setHorizontalHeaderLabels(["序号", "议题", "汇报时间", "讨论时间", "操作"])
        self._topic_table.horizontalHeader().setStretchLastSection(False)
        self._topic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._topic_table.setColumnWidth(0, 50)
        self._topic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._topic_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._topic_table.setColumnWidth(2, 50)
        self._topic_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._topic_table.setColumnWidth(3, 50)
        self._topic_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._topic_table.setColumnWidth(4, 80)
        self._topic_table.verticalHeader().setVisible(False)
        self._topic_table.verticalHeader().setDefaultSectionSize(50)
        self._topic_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._topic_table.setSelectionBehavior(QTableWidget.SelectRows)
        right_layout.addWidget(self._topic_table, 1)

        page_layout.addWidget(left_widget, 1)
        page_layout.addWidget(right_widget, 1)

        return page

    def _connect_signals(self):
        self._config_panel.meeting_ready.connect(self._on_meeting_ready)
        self._history_panel.view_stats_requested.connect(self._on_view_stats)

        self._controller.timer_updated.connect(self._on_timer_updated)
        self._controller.phase_changed.connect(self._on_phase_changed)
        self._controller.meeting_completed.connect(self._on_meeting_completed)

        self._hotkey_manager.hotkey_pressed.connect(self._on_hotkey)
        self._register_hotkeys()

    def _register_hotkeys(self):
        self._hotkey_manager.unregister_all()

        for hotkey_id, (modifier, key) in DEFAULT_HOTKEYS.items():
            self._hotkey_manager.register_hotkey(hotkey_id, modifier, key)

    def _parse_key(self, key_str: str) -> int:
        key_map = {
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
            "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
            "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
            "space": 0x20, "tab": 0x09, "enter": 0x0D, "escape": 0x1B,
            "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
            "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
            "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
            "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
            "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
            "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
            "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
            "z": 0x5A,
        }
        return key_map.get(key_str, 0)

    def _load_audio_settings(self):
        raw = self._db.get_setting(SETTING_KEY_SOUNDS)
        if raw:
            try:
                sounds = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                sounds = dict(DEFAULT_SOUNDS)
        else:
            sounds = dict(DEFAULT_SOUNDS)

        self._audio.set_selection("warning", sounds.get("warning", "soft_chime"))
        self._audio.set_selection("timeup", sounds.get("timeup", "clear_bell"))
        self._audio.set_selection("overtime", sounds.get("overtime", "alert_beep"))

    def _on_nav_changed(self, index):
        self._navbar.set_active(index)
        if index == 0:
            self._stacked.setCurrentIndex(0)
        elif index == 1:
            self._stacked.setCurrentIndex(1)
        elif index == 2:
            self._history_panel.refresh_list()
            self._stacked.setCurrentIndex(2)

    def _on_new_meeting(self):
        self._navbar.set_active(0)
        self._stacked.setCurrentIndex(0)

    def _on_show_history(self):
        self._history_panel.refresh_list()
        self._navbar.set_active(2)
        self._stacked.setCurrentIndex(2)

    def _on_open_settings(self):
        try:
            dialog = SettingsDialog(self)
            dialog.settings_changed.connect(self._on_settings_changed)
            self._settings_dialog = dialog
            dialog.finished.connect(lambda: setattr(self, '_settings_dialog', None))
            dialog.open()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开设置窗口：{e}")

    def _on_meeting_ready(self, config: dict):
        meeting = self._db.create_meeting(config["name"], status="draft")
        self._current_meeting_id = meeting.id

        for i, topic_data in enumerate(config["topics"]):
            self._db.create_topic(
                meeting.id,
                i,
                topic_data["name"],
                topic_data["presentation_minutes"],
                topic_data["qa_minutes"],
            )

        topics = self._db.get_topics_by_meeting(meeting.id)
        for topic in topics:
            for phase in ("presentation", "qa"):
                if phase == "presentation":
                    planned = topic.presentation_minutes * 60
                else:
                    planned = topic.qa_minutes * 60
                self._db.create_phase_record(topic.id, phase, planned)

        self._meeting_name_label.setText(config["name"])
        self._warning_triggered = False
        self._overtime_triggered = False
        self._remaining_minutes_triggered = False
        self._last_overtime_minute = 0
        self._navbar.set_float_checked(True)

        self._controller.start_meeting(meeting.id)
        self._controller.start_current_phase()
        self._pause_resume_btn.setText("暂停")
        self.activateWindow()
        self.raise_()

        info = self._controller.get_current_info()
        self._topic_name_label.setText(info.get("topic_name", ""))
        phase_display = "汇报时间" if info.get("phase") == "presentation" else "讨论时间"
        self._phase_name_label.setText(phase_display)

        self._refresh_topic_table()
        self._controller.refresh_topics()

        self._stacked.setCurrentIndex(1)
        self._navbar.set_active(1)
        self._navbar.set_meeting_nav_visible(True)
        if self._float_timer:
            self._float_timer.set_topic_info(info.get("topic_name", ""), info.get("phase", "presentation"))
            self._float_timer.show()
            self._navbar.set_float_checked(True)

    def _on_timer_updated(self, tick_data: dict):
        progress = tick_data.get("progress", 0.0)
        remaining = tick_data.get("remaining_seconds", 0.0)
        overtime = tick_data.get("overtime_seconds", 0.0)
        is_overtime = tick_data.get("is_overtime", False)
        is_paused = tick_data.get("is_paused", False)
        is_countdown = tick_data.get("is_countdown", False)

        if is_overtime:
            display_text = format_time(overtime)
            self._time_display_label.setStyleSheet(
                f"color: {DANGER}; font-size: 40px; font-weight: 700; "
                f"line-height: 1.50; background: transparent; border: none;"
            )
        elif is_paused:
            display_text = format_time(remaining)
            self._time_display_label.setStyleSheet(
                f"color: {WARNING}; font-size: 40px; font-weight: 700; "
                f"line-height: 1.50; background: transparent; border: none;"
            )
        else:
            display_text = format_time(remaining)
            self._time_display_label.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 40px; font-weight: 700; "
                f"line-height: 1.50; background: transparent; border: none;"
            )
        self._time_display_label.setText(display_text)

        planned_seconds = tick_data.get("planned_seconds", 0)
        self._planned_time_label.setText(format_time(planned_seconds))

        if is_overtime:
            self._status_label.setStyleSheet(
                f"color: {DANGER}; font-size: 16px; font-weight: 400; "
                f"background: transparent; border: none;"
            )
            self._status_label.setText("超时")
        elif is_paused:
            self._status_label.setStyleSheet(
                f"color: {WARNING}; font-size: 16px; font-weight: 400; "
                f"background: transparent; border: none;"
            )
            self._status_label.setText("暂停")
        elif is_countdown:
            info = self._controller.get_current_info()
            current_phase = info.get("phase", "presentation")
            if current_phase == "qa":
                self._status_label.setStyleSheet(
                    f"color: {PRIMARY}; font-size: 16px; font-weight: 400; "
                    f"background: transparent; border: none;"
                )
                self._status_label.setText("讨论中")
            else:
                self._status_label.setStyleSheet(
                    f"color: {PRIMARY}; font-size: 16px; font-weight: 400; "
                    f"background: transparent; border: none;"
                )
                self._status_label.setText("汇报中")
        else:
            self._status_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 400; "
                f"background: transparent; border: none;"
            )
            self._status_label.setText("待开始")

        if self._float_timer and self._float_timer.isVisible():
            self._float_timer.update_display(tick_data)

        if is_countdown and not is_overtime and 0 < remaining <= 30 and not self._warning_triggered:
            self._warning_triggered = True

        if is_overtime and not self._overtime_triggered:
            self._overtime_triggered = True
            self._audio.play("timeup")

        if is_countdown and not is_overtime and not self._remaining_minutes_triggered:
            raw = self._db.get_setting(SETTING_KEY_SOUNDS)
            remaining_minutes = 5
            if raw:
                try:
                    sounds = json.loads(raw)
                    remaining_minutes = sounds.get("remaining_minutes", 5)
                except (json.JSONDecodeError, TypeError):
                    pass
            if self._audio.is_enabled("warning") and 0 < remaining <= remaining_minutes * 60:
                self._remaining_minutes_triggered = True
                self._audio.play("warning")

        if is_overtime:
            raw = self._db.get_setting(SETTING_KEY_SOUNDS)
            overtime_minutes = 5
            if raw:
                try:
                    sounds = json.loads(raw)
                    overtime_minutes = sounds.get("overtime_minutes", 5)
                except (json.JSONDecodeError, TypeError):
                    pass
            if self._audio.is_enabled("overtime"):
                current_overtime_minute = int(overtime) // 60
                if current_overtime_minute > 0 and current_overtime_minute > self._last_overtime_minute and current_overtime_minute % overtime_minutes == 0:
                    self._last_overtime_minute = current_overtime_minute
                    self._audio.play("overtime")

        self._update_topic_table_status()

    def _on_phase_changed(self, topic_index: int, phase: str):
        info = self._controller.get_current_info()
        self._topic_name_label.setText(info.get("topic_name", ""))
        phase_display = "汇报时间" if phase == "presentation" else "讨论时间"
        self._phase_name_label.setText(phase_display)

        # Sync enter discussion button state
        self._enter_discussion_btn.setEnabled(phase != "qa")

        self._warning_triggered = False
        self._overtime_triggered = False
        self._remaining_minutes_triggered = False
        self._last_overtime_minute = 0

        self._refresh_topic_table()

        if self._float_timer and self._float_timer.isVisible():
            self._float_timer.set_topic_info(info.get("topic_name", ""), phase)

    def _on_meeting_completed(self):
        self._navbar.set_meeting_nav_visible(False)

        if self._float_timer:
            self._float_timer.update_display({
                "progress": 0.0,
                "remaining_seconds": 0.0,
                "overtime_seconds": 0.0,
                "is_overtime": False,
                "is_paused": False,
                "is_countdown": False,
                "state": "idle",
            })

        meeting_data = self._build_current_meeting_data()
        self._current_meeting_id = None
        self._on_view_stats(meeting_data)

    def _on_pause_resume(self):
        engine = self._controller.engine
        if engine.state == TimerEngine.IDLE:
            self._controller.start_current_phase()
            self._pause_resume_btn.setText("暂停")
            return
        self._controller.pause_resume()
        info = self._controller.get_current_info()
        is_paused = engine.state in (TimerEngine.PAUSED_CD, TimerEngine.PAUSED_OT)
        self._pause_resume_btn.setText("继续" if is_paused else "暂停")

        if self._float_timer and self._float_timer.isVisible():
            tick = engine.tick()
            self._float_timer.update_display(tick)

    def _on_enter_discussion(self):
        info = self._controller.get_current_info()
        if info.get("phase") == "qa":
            return
        self._controller.next_phase()
        self._enter_discussion_btn.setEnabled(False)
        self._pause_resume_btn.setText("暂停")

    def _on_next_topic(self):
        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)
        topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        if info.get("phase") == "qa":
            if current_index >= len(topics) - 1:
                return
            self._controller.next_phase()
        else:
            self._controller.next_phase()
            if current_index >= len(topics) - 1:
                return
            self._controller.next_phase()
        self._pause_resume_btn.setText("暂停")

    def _show_detached_message_box(self, title, message):
        """显示不依附主窗口的消息框，防止主窗口被带到前面"""
        from PySide6.QtWidgets import QMessageBox
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置窗口标志，防止它影响主窗口
        msg_box.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        return msg_box.exec()

    def _on_reset_phase(self):
        reply = self._show_detached_message_box(
            "重置阶段", "确定重置当前阶段计时？"
        )
        if reply == QMessageBox.Yes:
            self._controller.reset_current_phase()
            self._warning_triggered = False
            self._overtime_triggered = False
            self._remaining_minutes_triggered = False
            self._last_overtime_minute = 0
            # 重置后立即开始计时
            self._controller.start_current_phase()
            self._pause_resume_btn.setText("暂停")

    def _on_start_phase(self):
        self._controller.start_current_phase()
        self._pause_resume_btn.setText("暂停")

    def _on_end_meeting(self):
        reply = self._show_detached_message_box(
            "结束会议", "确定结束会议？未完成的阶段将标记为已完成。"
        )
        if reply == QMessageBox.Yes:
            self._controller.complete_meeting()

    def _create_float_timer(self):
        self._float_timer = FloatTimer()
        self._float_timer.close_clicked.connect(self._on_float_close)
        self._float_timer.pause_requested.connect(self._on_pause_resume)
        self._float_timer.reset_requested.connect(self._on_reset_phase)
        self._float_timer.enter_discussion_requested.connect(self._on_enter_discussion)
        self._float_timer.next_topic_requested.connect(self._on_next_topic)
        self._float_timer.add_temp_topic_requested.connect(self._on_add_temp_topic)
        self._float_timer.end_meeting_requested.connect(self._on_end_meeting)

        self._apply_float_display_settings()
        self._float_timer.show()

    def _on_toggle_float(self, checked: bool):
        if self._float_timer:
            if checked:
                self._float_timer.show()
            else:
                self._float_timer.hide()

    def _on_float_close(self):
        self._navbar.set_float_checked(False)
        if self._float_timer:
            self._float_timer.hide()

    def _on_hotkey(self, hotkey_id: int):
        if hotkey_id == HOTKEY_TOGGLE_FLOAT:
            if self._float_timer:
                if self._float_timer.isVisible():
                    self._float_timer.hide()
                    self._navbar.set_float_checked(False)
                else:
                    self._float_timer.show()
        elif hotkey_id == HOTKEY_FLOAT_SMALL:
            if self._float_timer:
                self._float_timer.set_size("small")
                if not self._float_timer.isVisible():
                    self._float_timer.show()
        elif hotkey_id == HOTKEY_FLOAT_MEDIUM:
            if self._float_timer:
                self._float_timer.set_size("medium")
                if not self._float_timer.isVisible():
                    self._float_timer.show()
        elif hotkey_id == HOTKEY_FLOAT_LARGE:
            if self._float_timer:
                self._float_timer.set_size("large")
                if not self._float_timer.isVisible():
                    self._float_timer.show()
                    self._navbar.set_float_checked(True)

    def _on_view_stats(self, meeting_data: dict):
        dialog = StatsDialog(meeting_data, self)
        dialog.exec()
        if self._stacked.currentIndex() == 1:
            self._stacked.setCurrentIndex(0)
            self._navbar.set_active(0)
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_settings_changed(self):
        self._register_hotkeys()
        self._load_audio_settings()
        self._apply_float_display_settings()
        self._config_panel.reload_defaults()

    def _apply_float_display_settings(self):
        if self._float_timer is None:
            return
        raw = self._db.get_setting(SETTING_KEY_DISPLAY)
        if raw:
            try:
                display = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                display = dict(DEFAULT_DISPLAY)
        else:
            display = dict(DEFAULT_DISPLAY)
        self._float_timer.set_opacity(display.get("opacity", 85))
        self._float_timer.set_size(display.get("float_size", "medium"))

        raw_sounds = self._db.get_setting(SETTING_KEY_SOUNDS)
        if raw_sounds:
            try:
                sounds = json.loads(raw_sounds)
            except (json.JSONDecodeError, TypeError):
                sounds = dict(DEFAULT_SOUNDS)
        else:
            sounds = dict(DEFAULT_SOUNDS)
        self._float_timer.set_reminder_config(
            sounds.get("remaining_minutes", 5),
            sounds.get("overtime_minutes", 5),
        )

    def _recover_in_progress_meeting(self):
        meetings = self._db.list_meetings(status="in_progress")
        if not meetings:
            return

        meeting = meetings[0]
        # 使用非模态对话框，不阻塞主窗口事件循环
        msg_box = QMessageBox()
        msg_box.setWindowTitle("恢复会议")
        msg_box.setText(f"检测到未完成的会议：{meeting.name}，是否恢复？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        msg_box.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        msg_box.setModal(False)

        def on_finished(result):
            if result == QMessageBox.Yes:
                self._current_meeting_id = meeting.id
                self._meeting_name_label.setText(meeting.name)
                self._warning_triggered = False
                self._overtime_triggered = False
                self._navbar.set_float_checked(True)

                self._controller.recover_meeting(meeting.id)

                engine = self._controller.engine
                is_paused = engine.state in (TimerEngine.PAUSED_CD, TimerEngine.PAUSED_OT)
                self._pause_resume_btn.setText("继续" if is_paused else "暂停")

                info = self._controller.get_current_info()
                self._topic_name_label.setText(info.get("topic_name", ""))
                phase_display = "汇报时间" if info.get("phase") == "presentation" else "讨论时间"
                self._phase_name_label.setText(phase_display)

                self._refresh_topic_table()

                self._stacked.setCurrentIndex(1)
                self._navbar.set_active(1)
                self._navbar.set_meeting_nav_visible(True)
                if self._float_timer:
                    self._float_timer.set_topic_info(info.get("topic_name", ""), info.get("phase", "presentation"))
                    self._float_timer.show()
                    self._navbar.set_float_checked(True)

        msg_box.finished.connect(on_finished)
        msg_box.show()

    def _refresh_topic_table(self):
        if self._current_meeting_id is None:
            return

        topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)
        current_phase = info.get("phase", "presentation")

        self._topic_table.setRowCount(len(topics))

        for row, topic in enumerate(topics):
            seq_item = QTableWidgetItem(str(topic.sort_order + 1))
            seq_item.setTextAlignment(Qt.AlignCenter)
            seq_item.setForeground(QColor(TEXT_MUTED))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemIsSelectable)
            self._topic_table.setItem(row, 0, seq_item)

            name_item = QTableWidgetItem(topic.name)
            name_item.setForeground(self._get_topic_color(row, current_index))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsSelectable)
            self._topic_table.setItem(row, 1, name_item)

            pres_status = self._get_phase_status(topic.id, "presentation", row, current_index, current_phase)
            pres_item = QTableWidgetItem(pres_status)
            pres_item.setTextAlignment(Qt.AlignCenter)
            pres_item.setForeground(self._get_status_color(pres_status))
            pres_item.setFlags(pres_item.flags() & ~Qt.ItemIsSelectable)
            self._topic_table.setItem(row, 2, pres_item)

            qa_status = self._get_phase_status(topic.id, "qa", row, current_index, current_phase)
            qa_item = QTableWidgetItem(qa_status)
            qa_item.setTextAlignment(Qt.AlignCenter)
            qa_item.setForeground(self._get_status_color(qa_status))
            qa_item.setFlags(qa_item.flags() & ~Qt.ItemIsSelectable)
            self._topic_table.setItem(row, 3, qa_item)

            arrow_widget = self._create_arrow_buttons(row, len(topics), current_index)
            self._topic_table.setCellWidget(row, 4, arrow_widget)

    def _create_arrow_buttons(self, row: int, total: int, current_index: int) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        arrow_style = (
            "QPushButton {"
            "  background: transparent;"
            "  color: #615D59;"
            "  border: none;"
            "  padding: 0px 0px;"
            "  font-size: 12px;"
            "  font-family: 'Inter, Microsoft YaHei, Segoe UI';"
            "  font-weight: normal;"
            "}"
            "QPushButton:hover {"
            "  color: #3B82F6;"
            "}"
            "QPushButton:pressed {"
            "  color: #2563EB;"
            "}"
            "QPushButton:disabled {"
            "  color: #ccc;"
            "}"
        )

        up_btn = QPushButton("上移")
        up_btn.setStyleSheet(arrow_style)
        up_btn.setEnabled(row > current_index)
        up_btn.clicked.connect(lambda checked=False, r=row: self._move_topic(r, r - 1))
        layout.addWidget(up_btn)

        down_btn = QPushButton("下移")
        down_btn.setStyleSheet(arrow_style)
        down_btn.setEnabled(row < total - 1 and row > current_index)
        down_btn.clicked.connect(lambda checked=False, r=row: self._move_topic(r, r + 1))
        layout.addWidget(down_btn)

        return widget

    def _move_topic(self, from_row: int, to_row: int):
        if self._current_meeting_id is None:
            return

        topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        if from_row < 0 or from_row >= len(topics):
            return
        if to_row < 0 or to_row >= len(topics):
            return

        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)

        if from_row <= current_index or to_row <= current_index:
            return

        topics[from_row], topics[to_row] = topics[to_row], topics[from_row]
        topic_ids = [t.id for t in topics]
        self._db.reorder_topics(self._current_meeting_id, topic_ids)
        self._controller.refresh_topics()
        self._refresh_topic_table()

    def _update_topic_table_status(self):
        if self._current_meeting_id is None:
            return

        topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)
        current_phase = info.get("phase", "presentation")

        for row, topic in enumerate(topics):
            if row >= self._topic_table.rowCount():
                break

            pres_status = self._get_phase_status(topic.id, "presentation", row, current_index, current_phase)
            pres_item = self._topic_table.item(row, 2)
            if pres_item:
                pres_item.setText(pres_status)
                pres_item.setForeground(self._get_status_color(pres_status))

            qa_status = self._get_phase_status(topic.id, "qa", row, current_index, current_phase)
            qa_item = self._topic_table.item(row, 3)
            if qa_item:
                qa_item.setText(qa_status)
                qa_item.setForeground(self._get_status_color(qa_status))

    def _get_phase_status(self, topic_id: int, phase: str, row: int,
                          current_index: int, current_phase: str) -> str:
        records = self._db.get_phase_records_by_topic(topic_id)
        record = None
        for r in records:
            if r.phase == phase:
                record = r
                break

        if record is None:
            return "○"

        if record.status == "completed":
            return "✓"

        is_current = (row == current_index and phase == current_phase)
        if is_current:
            return "⏱"

        if record.status in ("in_progress", "paused"):
            return "⏱"

        return "○"

    def _get_status_color(self, status: str):
        if status == "✓":
            return self._color_from_hex(SUCCESS)
        elif status == "⏱":
            return self._color_from_hex(WARNING)
        return self._color_from_hex(TEXT_MUTED)

    def _on_topic_rows_reordered(self):
        if self._current_meeting_id is None:
            return
        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)

        topic_ids = []
        for row in range(self._topic_table.rowCount()):
            item = self._topic_table.item(row, 1)
            if item is None:
                continue
            if row <= current_index:
                continue
            topics = self._db.get_topics_by_meeting(self._current_meeting_id)
            if row < len(topics):
                topic_ids.append(topics[row].id)

        if topic_ids:
            self._db.reorder_topics(self._current_meeting_id, topic_ids)

        self._controller.refresh_topics()
        self._refresh_topic_table()

    def _get_default_times(self):
        """从设置中读取默认汇报时间和讨论时间"""
        raw = self._db.get_setting(SETTING_KEY_DEFAULTS)
        if raw:
            try:
                defaults = json.loads(raw)
                return (
                    defaults.get("presentation_minutes", 10),
                    defaults.get("qa_minutes", 5),
                )
            except (json.JSONDecodeError, TypeError):
                pass
        return 10, 5

    def _on_add_temp_topic(self):
        if self._current_meeting_id is None:
            return

        from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit,
                                       QSpinBox, QComboBox, QDialogButtonBox)

        # 从设置中读取默认时间
        default_pres, default_qa = self._get_default_times()

        # 创建不依附主窗口的对话框
        dialog = QDialog()
        dialog.setWindowTitle("添加临时议题")
        dialog.setFixedSize(360, 280)
        # 设置窗口标志，保持在前面但不影响主窗口
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)

        name_input = QLineEdit()
        name_input.setPlaceholderText("输入议题名称")
        form.addRow("议题名称：", name_input)

        pres_spin = QSpinBox()
        pres_spin.setRange(1, 999)
        pres_spin.setValue(default_pres)
        pres_spin.setSuffix(" 分钟")
        form.addRow("汇报时间：", pres_spin)

        qa_spin = QSpinBox()
        qa_spin.setRange(1, 999)
        qa_spin.setValue(default_qa)
        qa_spin.setSuffix(" 分钟")
        form.addRow("讨论时间：", qa_spin)

        pos_combo = QComboBox()
        pos_combo.addItems(["放在当前议题之后", "放在末位"])
        form.addRow("位置：", pos_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        name = name_input.text().strip()
        if not name:
            # 使用独立的消息框
            msg_box = QMessageBox()
            msg_box.setWindowTitle("提示")
            msg_box.setText("请输入议题名称")
            msg_box.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
            msg_box.exec()
            return

        topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        info = self._controller.get_current_info()
        current_index = info.get("topic_index", 0)

        if pos_combo.currentIndex() == 0:
            sort_order = current_index + 1
        else:
            sort_order = len(topics)

        temp_name = f"{name} | 临时增加"
        new_topic = self._db.create_topic(
            self._current_meeting_id,
            sort_order,
            temp_name,
            pres_spin.value(),
            qa_spin.value(),
        )

        all_topics = self._db.get_topics_by_meeting(self._current_meeting_id)
        topic_ids = [t.id for t in all_topics]
        self._db.reorder_topics(self._current_meeting_id, topic_ids)

        for phase in ("presentation", "qa"):
            planned = (pres_spin.value() if phase == "presentation"
                       else qa_spin.value()) * 60
            self._db.create_phase_record(new_topic.id, phase, planned)

        self._refresh_topic_table()
        self._controller.refresh_topics()

    def _get_topic_color(self, row: int, current_index: int):
        if row == current_index:
            return self._color_from_hex(PRIMARY)
        if row < current_index:
            return self._color_from_hex(TEXT_SECONDARY)
        return self._color_from_hex(TEXT_MUTED)

    @staticmethod
    def _color_from_hex(hex_color: str):
        from PySide6.QtGui import QColor
        return QColor(hex_color)

    def _build_current_meeting_data(self) -> dict:
        if self._current_meeting_id is None:
            return {}

        meeting = self._db.get_meeting(self._current_meeting_id)
        if meeting is None:
            return {}

        return self._history_panel.build_meeting_data(self._current_meeting_id)

    def closeEvent(self, event):
        if self._current_meeting_id is not None:
            self._controller.auto_save()

        self._hotkey_manager.unregister_all()

        if self._float_timer:
            self._float_timer.close()

        event.accept()
