from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.ui.theme import (
    BG_BASE,
    BG_SURFACE,
    BORDER_DEFAULT,
    DANGER,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_time,
)
from app.utils.export import export_to_csv, export_to_excel


class StatsDialog(QDialog):
    def __init__(self, meeting_data: dict, parent=None):
        super().__init__(parent)
        self._meeting_data = meeting_data
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("会议统计")
        self.setFixedSize(700, 500)
        self.setStyleSheet(
            f"background-color: {BG_BASE}; color: {TEXT_PRIMARY}; "
            f"font-family: '{FONT_FAMILY}';"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        name_label = QLabel(self._meeting_data.get("meeting_name", ""))
        name_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: bold; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        header_layout.addWidget(name_label)

        date_label = QLabel(self._meeting_data.get("meeting_date", ""))
        date_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        header_layout.addWidget(date_label)

        layout.addLayout(header_layout)

        self._table = QTableWidget()
        self._table.setStyleSheet(
            f"QTableWidget {{ background-color: #FFFFFF; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 4px; "
            f"font-size: {FONT_SIZE_MEDIUM}px; font-family: '{FONT_FAMILY}'; "
            f"gridline-color: {BORDER_DEFAULT}; }}"
            f"QTableWidget::item {{ padding: 6px; }}"
            f"QTableWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; }}"
            f"QHeaderView::section {{ background-color: {BG_SURFACE}; "
            f"color: {TEXT_SECONDARY}; border: 1px solid {BORDER_DEFAULT}; "
            f"padding: 6px; font-weight: bold; "
            f"font-family: '{FONT_FAMILY}'; }}"
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._populate_table()
        layout.addWidget(self._table, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        excel_btn = QPushButton("导出 Excel")
        excel_btn.setObjectName("secondaryBtn")
        excel_btn.clicked.connect(self._on_export_excel)
        btn_layout.addWidget(excel_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _populate_table(self):
        topics = self._meeting_data.get("topics", [])
        total_actual = self._meeting_data.get("total_actual_seconds", 0.0)
        total_overtime = self._meeting_data.get("total_overtime_seconds", 0.0)
        total_planned = self._meeting_data.get("total_planned_minutes", 0)

        data_rows = len(topics) * 2
        total_rows = data_rows + 1

        columns = ["议题名称", "阶段", "计划时长(分钟)", "实际用时", "超时时长", "占比"]
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.setRowCount(total_rows)

        danger_color = QColor(DANGER)
        bold_font = QFont(FONT_FAMILY)
        bold_font.setBold(True)

        row = 0
        for topic in topics:
            for phase_key, phase_label in [("presentation", "汇报"), ("qa", "\u8ba8\u8bba")]:
                phase = topic.get(phase_key, {})
                planned = phase.get("planned_minutes", 0)
                actual = phase.get("actual_seconds", 0.0)
                overtime = phase.get("overtime_seconds", 0.0)

                if total_actual > 0:
                    percentage = f"{actual / total_actual * 100:.1f}%"
                else:
                    percentage = "0.0%"

                name_item = QTableWidgetItem(topic.get("name", ""))
                name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self._table.setItem(row, 0, name_item)

                phase_item = QTableWidgetItem(phase_label)
                phase_item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 1, phase_item)

                planned_item = QTableWidgetItem(str(planned))
                planned_item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 2, planned_item)

                actual_item = QTableWidgetItem(format_time(actual))
                actual_item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 3, actual_item)

                overtime_item = QTableWidgetItem(format_time(overtime))
                overtime_item.setTextAlignment(Qt.AlignCenter)
                if overtime > 0:
                    overtime_item.setForeground(danger_color)
                self._table.setItem(row, 4, overtime_item)

                pct_item = QTableWidgetItem(percentage)
                pct_item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 5, pct_item)

                row += 1

        summary_name = QTableWidgetItem("合计")
        summary_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        summary_name.setFont(bold_font)
        self._table.setItem(row, 0, summary_name)

        self._table.setItem(row, 1, QTableWidgetItem(""))

        planned_total_item = QTableWidgetItem(str(total_planned))
        planned_total_item.setTextAlignment(Qt.AlignCenter)
        planned_total_item.setFont(bold_font)
        self._table.setItem(row, 2, planned_total_item)

        actual_total_item = QTableWidgetItem(format_time(total_actual))
        actual_total_item.setTextAlignment(Qt.AlignCenter)
        actual_total_item.setFont(bold_font)
        self._table.setItem(row, 3, actual_total_item)

        overtime_total_item = QTableWidgetItem(format_time(total_overtime))
        overtime_total_item.setTextAlignment(Qt.AlignCenter)
        overtime_total_item.setFont(bold_font)
        if total_overtime > 0:
            overtime_total_item.setForeground(danger_color)
        self._table.setItem(row, 4, overtime_total_item)

        pct_total_item = QTableWidgetItem("100.0%")
        pct_total_item.setTextAlignment(Qt.AlignCenter)
        pct_total_item.setFont(bold_font)
        self._table.setItem(row, 5, pct_total_item)

    def _get_default_filename(self, ext: str) -> str:
        date_str = self._meeting_data.get("meeting_date", "")
        name = self._meeting_data.get("meeting_name", "")
        date_part = date_str.replace("-", "").replace("/", "").replace(" ", "")[:8]
        safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
        if not safe_name:
            safe_name = "meeting"
        return f"{date_part}_{safe_name}{ext}"

    def _on_export_csv(self):
        default_name = self._get_default_filename(".csv")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", default_name, "CSV 文件 (*.csv)"
        )
        if file_path:
            try:
                export_to_csv(self._meeting_data, file_path)
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))

    def _on_export_excel(self):
        default_name = self._get_default_filename(".xlsx")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", default_name, "Excel 文件 (*.xlsx)"
        )
        if file_path:
            try:
                export_to_excel(self._meeting_data, file_path)
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))
