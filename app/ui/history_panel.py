from datetime import datetime
import os

from PySide6.QtCore import Signal, Qt, QRect
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from PySide6.QtGui import QPainter

class CheckableHeaderView(QHeaderView):
    checkbox_clicked = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._is_checked = False
        self.setSectionsClickable(True)
        
    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex == 0:
            # 计算和表格单元格中复选框相同的位置
            y_offset = 10 + 4  # 往下移4px
            x_offset = 5  # 往右移5px
            opt = QStyleOptionButton()
            opt.rect = QRect(rect.x() + (rect.width() - 16) // 2 + x_offset, rect.y() + y_offset, 16, 16)
            opt.state = QStyle.State_Enabled | (QStyle.State_On if self._is_checked else QStyle.State_Off)
            self.style().drawControl(QStyle.CE_CheckBox, opt, painter)
            
    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index == 0:
            self._is_checked = not self._is_checked
            self.checkbox_clicked.emit(self._is_checked)
            self.updateSection(0)
        else:
            super().mousePressEvent(event)
            
    def is_all_checked(self):
        return self._is_checked
        
    def set_all_checked(self, checked):
        if self._is_checked != checked:
            self._is_checked = checked
            self.updateSection(0)

from app.core.database import DatabaseManager
from app.ui.theme import (
    BG_SURFACE,
    BORDER_DEFAULT,
    DANGER,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_time,
)
from app.utils.export import export_to_csv, export_to_excel


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

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索会议名称或日期...")
        self._search_edit.setStyleSheet(
            f"QLineEdit {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
            f"padding: 8px 12px; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; }}"
            f"QLineEdit:focus {{ border: 2px solid {PRIMARY}; }}"
        )
        self._search_edit.textChanged.connect(self._on_search_changed)
        main_layout.addWidget(self._search_edit)

        self._meeting_table = QTableWidget()
        self._meeting_table.setColumnCount(4)
        self._meeting_table.setHorizontalHeaderLabels(["", "会议名称", "日期", "议题数"])
        self._checkable_header = CheckableHeaderView(self._meeting_table)
        self._meeting_table.setHorizontalHeader(self._checkable_header)
        self._checkable_header.checkbox_clicked.connect(self._on_check_all_clicked)
        self._meeting_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._meeting_table.setColumnWidth(0, 36)
        self._meeting_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._meeting_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._meeting_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._meeting_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._meeting_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._meeting_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._meeting_table.verticalHeader().setVisible(False)
        self._meeting_table.verticalHeader().setDefaultSectionSize(50)
        self._meeting_table.setAlternatingRowColors(True)
        self._meeting_table.setStyleSheet(
            f"QTableWidget {{ background-color: transparent; border: none; "
            f"gridline-color: transparent; outline: none; }}"
            f"QTableWidget::item {{ padding: 10px 12px; border-bottom: 1px solid {BORDER_DEFAULT}; "
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; background-color: #FFFFFF; }}"
            f"QTableWidget::item:alternate {{ background-color: {BG_SURFACE}; }}"
            f"QTableWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; }}"
            f"QHeaderView::section {{ background-color: #FFFFFF; color: {TEXT_SECONDARY}; "
            f"border: none; border-bottom: 2px solid {BORDER_DEFAULT}; "
            f"padding: 10px 12px; font-size: {FONT_SIZE_SMALL}px; "
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

        self._batch_export_btn = QPushButton("\u5bfc\u51fa")
        self._batch_export_btn.setObjectName("secondaryBtn")
        self._batch_export_btn.clicked.connect(self._on_batch_export)
        btn_layout.addWidget(self._batch_export_btn)

        self._batch_delete_btn = QPushButton("\u6279\u91cf\u5220\u9664")
        self._batch_delete_btn.setObjectName("dangerBtn")
        self._batch_delete_btn.clicked.connect(self._on_batch_delete)
        btn_layout.addWidget(self._batch_delete_btn)

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
        self._meetings = self._db.list_meetings()

        self._meeting_table.setRowCount(0)
        for row, meeting in enumerate(self._meetings):
            self._meeting_table.insertRow(row)

            topics = self._db.get_topics_by_meeting(meeting.id)

            try:
                dt = datetime.fromisoformat(meeting.created_at)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = meeting.created_at

            chk_item = QTableWidgetItem()
            chk_item.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
            )
            chk_item.setCheckState(Qt.Unchecked)
            self._meeting_table.setItem(row, 0, chk_item)

            name_item = QTableWidgetItem(meeting.name)
            name_item.setData(Qt.UserRole, meeting.id)
            self._meeting_table.setItem(row, 1, name_item)

            date_item = QTableWidgetItem(date_str)
            self._meeting_table.setItem(row, 2, date_item)

            count_item = QTableWidgetItem(str(len(topics)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._meeting_table.setItem(row, 3, count_item)

    def get_selected_meeting(self):
        row = self._meeting_table.currentRow()
        if row < 0:
            return None
        name_item = self._meeting_table.item(row, 1)
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

    def _on_search_changed(self):
        search_text = self._search_edit.text().strip().lower()
        for row in range(self._meeting_table.rowCount()):
            name_item = self._meeting_table.item(row, 1)
            date_item = self._meeting_table.item(row, 2)
            if name_item and date_item:
                name = name_item.text().lower()
                date = date_item.text().lower()
                match = search_text in name or search_text in date
                self._meeting_table.setRowHidden(row, not match)

    def _on_check_all_clicked(self, checked):
        check_state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self._meeting_table.rowCount()):
            chk_item = self._meeting_table.item(row, 0)
            if chk_item:
                chk_item.setCheckState(check_state)

    def _has_checked_rows(self):
        for row in range(self._meeting_table.rowCount()):
            chk_item = self._meeting_table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                return True
        return False

    def _on_selection_changed(self, row: int, col: int, prev_row: int, prev_col: int):
        if self._has_checked_rows():
            self._detail_frame.hide()
            self._stats_btn.setEnabled(False)
        else:
            has_selection = row >= 0
            self._stats_btn.setEnabled(has_selection)

            if has_selection:
                name_item = self._meeting_table.item(row, 1)
                if name_item:
                    meeting_id = name_item.data(Qt.UserRole)
                    if meeting_id is not None:
                        self.meeting_selected.emit(meeting_id)
                        self._show_detail(meeting_id)
                        return
            self._detail_frame.hide()

    def _on_item_double_clicked(self, row: int, col: int):
        name_item = self._meeting_table.item(row, 1)
        if name_item is None:
            return
        meeting_id = name_item.data(Qt.UserRole)
        if meeting_id is not None:
            meeting_data = self.build_meeting_data(meeting_id)
            self.view_stats_requested.emit(meeting_data)

    def _on_view_stats(self):
        meeting_data = self.get_selected_meeting()
        if meeting_data:
            self.view_stats_requested.emit(meeting_data)

    def _on_batch_export(self):
        checked_ids = self._get_checked_meeting_ids()
        if not checked_ids:
            QMessageBox.warning(self, "提示", "请先勾选要导出的会议")
            return

        dir_path = QFileDialog.getExistingDirectory(self, "\u9009\u62e9\u4fdd\u5b58\u8def\u5f84", os.path.expanduser("~"))
        if not dir_path:
            return

        # 确保目录路径存在且可访问
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "\u9009\u62e9\u8def\u5f84\u65e0\u6548", f"\u65e0\u6cd5\u521b\u5efa\u8be5\u76ee\u5f55: {str(e)}")
                return

        # 检查目录写入权限
        import tempfile
        try:
            # 规范化路径，解决混合斜杠问题
            dir_path = os.path.normpath(dir_path)
            test_file = os.path.join(dir_path, f"temp_test_{os.getpid()}.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "\u6743\u9650\u4e0d\u8db3", f"\u65e0\u6cd5\u5199\u5165\u8be5\u76ee\u5f55: {str(e)}\n\n{traceback.format_exc()}\n\n\u8bf7\u9009\u62e9\u5176\u4ed6\u8def\u5f84\uff0c\u5982\u684c\u9762")
            return

        meetings_data = [self.build_meeting_data(meeting_id) for meeting_id in checked_ids]
        meetings_data = [d for d in meetings_data if d]
        if not meetings_data:
            return

        errors = []
        for meeting_data in meetings_data:
            date_str = meeting_data.get("meeting_date", "")
            name = meeting_data.get("meeting_name", "")
            date_part = date_str.replace("-", "").replace("/", "").replace(" ", "")[:8]
            safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
            if not safe_name:
                safe_name = "meeting"
            default_name = f"{date_part}_{safe_name}.xlsx"
            file_path = os.path.join(dir_path, default_name)
            file_path = os.path.normpath(file_path)

            try:
                export_to_excel(meeting_data, file_path)
            except Exception as e:
                import traceback
                errors.append(f"{meeting_data.get('meeting_name', 'unknown')}: {str(e)}\n{traceback.format_exc()}")

        if errors:
            error_msg = "\n".join(errors)
            QMessageBox.warning(
                self, "\u90e8\u5206\u5bfc\u51fa\u5931\u8d25",
                f"\u4ee5\u4e0b\u4f1a\u8bae\u5bfc\u51fa\u5931\u8d25:\n\n{error_msg}"
            )
        elif len(meetings_data) == 1:
            QMessageBox.information(self, "\u5bfc\u51fa\u6210\u529f", "\u4f1a\u8bae\u8bb0\u5f55\u5df2\u5bfc\u51fa")
        else:
            QMessageBox.information(self, "\u5bfc\u51fa\u6210\u529f", f"{len(meetings_data)} \u4e2a\u4f1a\u8bae\u8bb0\u5f55\u5df2\u5bfc\u51fa\u5230\u6307\u5b9a\u76ee\u5f55")

    def _on_batch_delete(self):
        checked_ids = self._get_checked_meeting_ids()
        if not checked_ids:
            QMessageBox.warning(self, "提示", "请先勾选要删除的会议")
            return

        count = len(checked_ids)
        reply = QMessageBox.question(
            self,
            "\u5220\u9664\u4f1a\u8bae",
            f"\u786e\u5b9a\u5220\u9664\u9009\u4e2d\u7684 {count} \u4e2a\u4f1a\u8bae\u8bb0\u5f55\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d\u3002",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for meeting_id in checked_ids:
                self._db.delete_meeting(meeting_id)
            self.refresh_list()
            self._detail_frame.hide()

    def _get_checked_meeting_ids(self):
        checked_ids = []
        for row in range(self._meeting_table.rowCount()):
            chk_item = self._meeting_table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                name_item = self._meeting_table.item(row, 1)
                if name_item:
                    meeting_id = name_item.data(Qt.UserRole)
                    if meeting_id is not None:
                        checked_ids.append(meeting_id)
        return checked_ids



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
