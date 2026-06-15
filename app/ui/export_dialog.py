import os
import subprocess

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt


class ExportSuccessDialog(QDialog):
    def __init__(self, file_path: str, count: int = 1, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self._count = count
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("导出成功")
        self.setFixedSize(320, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            "font-size: 48px; text-align: center;"
        )
        icon_label.setText("✓")
        layout.addWidget(icon_label)

        if self._count == 1:
            text_label = QLabel("成功导出会议记录")
        else:
            text_label = QLabel(f"成功导出 {self._count} 个会议记录")
        text_label.setStyleSheet(
            "font-size: 14px; color: rgba(0,0,0,0.9); text-align: center;"
        )
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        open_btn = QPushButton("打开文件路径")
        open_btn.setObjectName("primaryBtn")
        open_btn.clicked.connect(self._on_open_file)
        btn_layout.addWidget(open_btn)

        confirm_btn = QPushButton("确认")
        confirm_btn.setObjectName("secondaryBtn")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_open_file(self):
        subprocess.Popen(["explorer", "/select,", os.path.abspath(self._file_path)])
        self.accept()