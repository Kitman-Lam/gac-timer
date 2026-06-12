import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QPen
from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET, PRIMARY, FONT_FAMILY
from app.core.database import DatabaseManager


def _create_clock_icon() -> QIcon:
    size = 256
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    cx = size / 2
    cy = size / 2
    r = size / 2 - 8

    painter.setBrush(QColor(PRIMARY))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    painter.setBrush(QColor(255, 255, 255))
    painter.drawEllipse(cx - r + 12, cy - r + 12, (r - 12) * 2, (r - 12) * 2)

    painter.setBrush(Qt.NoBrush)
    pen = QPen(QColor(PRIMARY))
    pen.setWidth(8)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)

    painter.drawLine(int(cx), int(cy), int(cx + r * 0.45), int(cy - r * 0.1))

    pen.setWidth(6)
    painter.setPen(pen)
    painter.drawLine(int(cx), int(cy), int(cx + r * 0.2), int(cy + r * 0.35))

    painter.setBrush(QColor(PRIMARY))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(int(cx - 6), int(cy - 6), 12, 12)

    painter.end()

    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GAC Timer")
    app.setOrganizationName("GAC")
    app.setStyleSheet(APP_STYLESHEET)
    app.setWindowIcon(_create_clock_icon())

    font = app.font()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(10)
    app.setFont(font)

    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "gac_timer.db")
    DatabaseManager(db_path=db_path)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
