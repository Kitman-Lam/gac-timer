from datetime import datetime

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.database import DatabaseManager
from app.ui.stats_dialog import StatsDialog
from app.ui.theme import (
    BG_ELEVATED,
    BG_SURFACE,
    BORDER_DEFAULT,
    DANGER,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    PRIMARY,
    PRIMARY_LIGHT,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_time,
)
from app.utils.export import export_to_csv, export_to_excel


_STATUS_LABELS = {
    "draft": "\u8349\u7a3f",
    "in_progress": "\u8fdb\u884c\u4e2d",
    "completed": "\u5df2\u5b8c\u6210",
}

_STATUS_COLORS = {
    "draft": (BG_ELEVATED, TEXT_MUTED),
    "in_progress": (PRIMARY_LIGHT, PRIMARY),
    "completed": ("#E8F8EC", SUCCESS),
}

_FILTER_MAP = {
    0: None,
    1: "completed",
    2: "in_progress",
}


class HistoryPanel(QWidget):
    meeting_selected = Signal(int)
    view_stats_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._meetings = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        header = QLabel("历史会议记录")
        header.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
            f"font-weight: bold; font-family: '{FONT_FAMILY}'; "
            f"background: transparent; border: none;"
        )
        main_layout.addWidget(header)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_label = QLabel("筛选：")
        filter_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        filter_layout.addWidget(filter_label)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "已完成", "进行中"])
        self._filter_combo.setStyleSheet(
            f"QComboBox {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 4px; "
            f"padding: 6px 10px; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; min-width: 100px; }}"
            f"QComboBox::drop-down {{ border: none; width: 20px; }}"
            f"QComboBox::down-arrow {{ image: none; border: none; }}"
            f"QComboBox QAbstractItemView {{ background-color: #FFFFFF; "
            f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; "
            f"selection-background-color: {PRIMARY_LIGHT}; }}"
        )
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._filter_combo)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        self._meeting_table = QTableWidget()
        self._meeting_table.setColumnCount(4)
        self._meeting_table.setHorizontalHeaderLabels(["会议名称", "日期", "议题数", "状态"])
        self._meeting_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._meeting_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._meeting_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._meeting_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._meeting_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._meeting_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._meeting_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._meeting_table.verticalHeader().setVisible(False)
        self._meeting_table.setAlternatingRowColors(True)
        self._meeting_table.setStyleSheet(
            f"QTableWidget {{ background-color: transparent; border: none; "
            f"gridline-color: transparent; outline: none; }}"
            f"QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {BORDER_DEFAULT}; "
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; background-color: #FFFFFF; }}"
            f"QTableWidget::item:alternate {{ background-color: {BG_SURFACE}; }}"
            f"QTableWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; }}"
            f"QHeaderView::section {{ background-color: #FFFFFF; color: {TEXT_SECONDARY}; "
            f"border: none; border-bottom: 2px solid {BORDER_DEFAULT}; "
            f"padding: 8px 12px; font-size: {FONT_SIZE_SMALL}px; "
            f"font-weight: bold; font-family: '{FONT_FAMILY}'; }}"
        )
        self._meeting_table.currentCellChanged.connect(self._on_selection_changed)
        self._meeting_table.cellDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self._meeting_table, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._stats_btn = QPushButton("\u67e5\u770b\u7edf\u8ba1")
        self._stats_btn.setObjectName("primaryBtn")
        self._stats_btn.setEnabled(False)
        self._stats_btn.clicked.connect(self._on_view_stats)
        btn_layout.addWidget(self._stats_btn)

        self._export_btn = QPushButton("\u5bfc\u51fa")
        self._export_btn.setObjectName("secondaryBtn")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self._export_btn)

        self._delete_btn = QPushButton("\u5220\u9664")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        main_layout.addLayout(btn_layout)

        self._detail_frame = QFrame()
        self._detail_frame.setStyleSheet(
            f"QFrame {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_DEFAULT}; "
            f"border-radius: 8px; }}"
        )
        self._detail_layout = QVBoxLayout(self._detail_frame)
        self._detail_layout.setContentsMargins(12, 10, 12, 10)
        self._detail_layout.setSpacing(6)
        self._detail_frame.hide()
        main_layout.addWidget(self._detail_frame)

    def refresh_list(self):
        filter_index = self._filter_combo.currentIndex()
        status = _FILTER_MAP.get(filter_index)
        self._meetings = self._db.list_meetings(status)

        self._meeting_table.setRowCount(0)
        for row, meeting in enumerate(self._meetings):
            self._meeting_table.insertRow(row)

            topics = self._db.get_topics_by_meeting(meeting.id)

            try:
                dt = datetime.fromisoformat(meeting.created_at)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = meeting.created_at

            status_text = _STATUS_LABELS.get(meeting.status, meeting.status)
            badge_bg, badge_fg = _STATUS_COLORS.get(meeting.status, (BG_ELEVATED, TEXT_MUTED))

            name_item = QTableWidgetItem(meeting.name)
            name_item.setData(Qt.UserRole, meeting.id)
            self._meeting_table.setItem(row, 0, name_item)

            date_item = QTableWidgetItem(date_str)
            self._meeting_table.setItem(row, 1, date_item)

            count_item = QTableWidgetItem(str(len(topics)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._meeting_table.setItem(row, 2, count_item)

            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor(badge_fg))
            status_item.setBackground(QColor(badge_bg))
            self._meeting_table.setItem(row, 3, status_item)

    def get_selected_meeting(self):
        row = self._meeting_table.currentRow()
        if row < 0:
            return None
        name_item = self._meeting_table.item(row, 0)
        if name_item is None:
            return None
        meeting_id = name_item.data(Qt.UserRole)
        if meeting_id is None:
            return None
        return self.build_meeting_data(meeting_id)

    def build_meeting_data(self, meeting_id: int) -> dict:
        meeting = self._db.get_meeting(meeting_id)
        if meeting is None:
            return {}

        topics = self._db.get_topics_by_meeting(meeting_id)
        phase_records = self._db.get_phase_records_by_meeting(meeting_id)

        records_by_topic = {}
        for pr in phase_records:
            records_by_topic.setdefault(pr.topic_id, []).append(pr)

        topics_data = []
        total_planned_minutes = 0
        total_actual_seconds = 0.0
        total_overtime_seconds = 0.0

        for topic in topics:
            topic_records = records_by_topic.get(topic.id, [])
            presentation = {
                "planned_minutes": topic.presentation_minutes,
                "actual_seconds": 0.0,
                "overtime_seconds": 0.0,
            }
            qa = {
                "planned_minutes": topic.qa_minutes,
                "actual_seconds": 0.0,
                "overtime_seconds": 0.0,
            }

            for pr in topic_records:
                if pr.phase == "presentation":
                    presentation["actual_seconds"] = pr.actual_seconds
                    presentation["overtime_seconds"] = pr.overtime_seconds
                elif pr.phase == "qa":
                    qa["actual_seconds"] = pr.actual_seconds
                    qa["overtime_seconds"] = pr.overtime_seconds

            topics_data.append({
                "name": topic.name,
                "presentation": presentation,
                "qa": qa,
            })

            total_planned_minutes += topic.presentation_minutes + topic.qa_minutes
            total_actual_seconds += presentation["actual_seconds"] + qa["actual_seconds"]
            total_overtime_seconds += presentation["overtime_seconds"] + qa["overtime_seconds"]

        try:
            dt = datetime.fromisoformat(meeting.created_at)
            formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            formatted_date = meeting.created_at

        return {
            "meeting_name": meeting.name,
            "meeting_date": formatted_date,
            "topics": topics_data,
            "total_planned_minutes": total_planned_minutes,
            "total_actual_seconds": total_actual_seconds,
            "total_overtime_seconds": total_overtime_seconds,
        }

    def _on_filter_changed(self):
        self.refresh_list()

    def _on_selection_changed(self, row: int, col: int, prev_row: int, prev_col: int):
        has_selection = row >= 0
        self._stats_btn.setEnabled(has_selection)
        self._export_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

        if has_selection:
            name_item = self._meeting_table.item(row, 0)
            if name_item:
                meeting_id = name_item.data(Qt.UserRole)
                if meeting_id is not None:
                    self.meeting_selected.emit(meeting_id)
                    self._show_detail(meeting_id)
                    return
        self._detail_frame.hide()

    def _on_item_double_clicked(self, row: int, col: int):
        name_item = self._meeting_table.item(row, 0)
        if name_item is None:
            return
        meeting_id = name_item.data(Qt.UserRole)
        if meeting_id is not None:
            meeting_data = self.build_meeting_data(meeting_id)
            self.view_stats_requested.emit(meeting_data)
            self._open_stats_dialog(meeting_data)

    def _on_view_stats(self):
        meeting_data = self.get_selected_meeting()
        if meeting_data:
            self.view_stats_requested.emit(meeting_data)
            self._open_stats_dialog(meeting_data)

    def _on_export(self):
        row = self._meeting_table.currentRow()
        if row < 0:
            return
        name_item = self._meeting_table.item(row, 0)
        if name_item is None:
            return
        meeting_id = name_item.data(Qt.UserRole)
        if meeting_id is None:
            return
        meeting_data = self.build_meeting_data(meeting_id)
        if not meeting_data:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 8px; "
            f"padding: 4px; font-family: '{FONT_FAMILY}'; }}"
            f"QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}"
            f"QMenu::item:selected {{ background-color: {BG_SURFACE}; }}"
        )
        csv_action = menu.addAction("\u5bfc\u51fa CSV")
        excel_action = menu.addAction("\u5bfc\u51fa Excel")

        action = menu.exec(
            self._export_btn.mapToGlobal(self._export_btn.rect().bottomLeft())
        )

        if action == csv_action:
            self._export_csv(meeting_data)
        elif action == excel_action:
            self._export_excel(meeting_data)

    def _on_delete(self):
        row = self._meeting_table.currentRow()
        if row < 0:
            return
        name_item = self._meeting_table.item(row, 0)
        if name_item is None:
            return
        meeting_id = name_item.data(Qt.UserRole)
        if meeting_id is None:
            return

        reply = QMessageBox.question(
            self,
            "\u5220\u9664\u4f1a\u8bae",
            "\u786e\u5b9a\u5220\u9664\u8be5\u4f1a\u8bae\u8bb0\u5f55\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d\u3002",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._db.delete_meeting(meeting_id)
            self.refresh_list()
            self._detail_frame.hide()

    def _open_stats_dialog(self, meeting_data: dict):
        dialog = StatsDialog(meeting_data, self)
        dialog.exec()

    def _export_csv(self, meeting_data: dict):
        date_str = meeting_data.get("meeting_date", "")
        name = meeting_data.get("meeting_name", "")
        date_part = date_str.replace("-", "").replace("/", "").replace(" ", "")[:8]
        safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
        if not safe_name:
            safe_name = "meeting"
        default_name = f"{date_part}_{safe_name}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "\u5bfc\u51fa CSV", default_name, "CSV \u6587\u4ef6 (*.csv)"
        )
        if file_path:
            try:
                export_to_csv(meeting_data, file_path)
            except Exception as e:
                QMessageBox.critical(self, "\u5bfc\u51fa\u5931\u8d25", str(e))

    def _export_excel(self, meeting_data: dict):
        date_str = meeting_data.get("meeting_date", "")
        name = meeting_data.get("meeting_name", "")
        date_part = date_str.replace("-", "").replace("/", "").replace(" ", "")[:8]
        safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
        if not safe_name:
            safe_name = "meeting"
        default_name = f"{date_part}_{safe_name}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "\u5bfc\u51fa Excel", default_name, "Excel \u6587\u4ef6 (*.xlsx)"
        )
        if file_path:
            try:
                export_to_excel(meeting_data, file_path)
            except Exception as e:
                QMessageBox.critical(self, "\u5bfc\u51fa\u5931\u8d25", str(e))

    def _show_detail(self, meeting_id: int):
        meeting_data = self.build_meeting_data(meeting_id)
        if not meeting_data:
            self._detail_frame.hide()
            return

        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        name_label = QLabel(meeting_data["meeting_name"])
        name_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_MEDIUM}px; "
            f"font-weight: bold; font-family: '{FONT_FAMILY}'; "
            f"background: transparent; border: none;"
        )
        self._detail_layout.addWidget(name_label)

        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)

        total_planned = meeting_data["total_planned_minutes"]
        total_actual = meeting_data["total_actual_seconds"]
        total_overtime = meeting_data["total_overtime_seconds"]

        summary_items = [
            ("\u65e5\u671f", meeting_data["meeting_date"], TEXT_SECONDARY),
            ("\u8ba1\u5212", f"{total_planned} \u5206\u949f", TEXT_SECONDARY),
            ("\u5b9e\u9645", format_time(total_actual), TEXT_SECONDARY),
            ("\u8d85\u65f6", format_time(total_overtime), DANGER if total_overtime > 0 else TEXT_SECONDARY),
        ]

        for label_text, value, color in summary_items:
            lbl = QLabel(f"{label_text}: {value}")
            lbl.setStyleSheet(
                f"color: {color}; font-size: {FONT_SIZE_SMALL}px; "
                f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
            )
            summary_layout.addWidget(lbl)

        summary_layout.addStretch()
        self._detail_layout.addLayout(summary_layout)

        for topic in meeting_data["topics"]:
            topic_layout = QHBoxLayout()
            topic_layout.setSpacing(8)

            topic_name = QLabel(topic["name"])
            topic_name.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SMALL}px; "
                f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
            )
            topic_layout.addWidget(topic_name)
            topic_layout.addStretch()

            for phase_key, phase_label in [("presentation", "\u6c47\u62a5"), ("qa", "\u8ba8\u8bba")]:
                phase = topic[phase_key]
                actual = format_time(phase["actual_seconds"])
                overtime = phase["overtime_seconds"]

                text = f"{phase_label}: {actual}"
                color = TEXT_SECONDARY
                if overtime > 0:
                    text += f" (\u8d85\u65f6 {format_time(overtime)})"
                    color = DANGER

                phase_lbl = QLabel(text)
                phase_lbl.setStyleSheet(
                    f"color: {color}; font-size: {FONT_SIZE_SMALL}px; "
                    f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
                )
                topic_layout.addWidget(phase_lbl)

            self._detail_layout.addLayout(topic_layout)

        self._detail_frame.show()
