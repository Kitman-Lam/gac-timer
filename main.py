import sys
import os
import atexit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QSharedMemory
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


def _check_single_instance():
    import tempfile
    import os
    import ctypes
    
    lock_dir = os.path.join(tempfile.gettempdir(), "MeetTimer")
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = os.path.join(lock_dir, "instance.lock")
    
    try:
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    pid = int(f.read().strip())
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x0400, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return False
            except Exception:
                pass
        
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


def _cleanup_lock():
    import tempfile
    import os
    lock_file = os.path.join(tempfile.gettempdir(), "MeetTimer", "instance.lock")
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception:
        pass


def _set_windows_process_name():
    try:
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("会帮手")
            # 这是为任务管理器显示设置正确的进程名
            try:
                # 使用psutil库（如果可用）
                import psutil
                current_process = psutil.Process()
                current_process.name = "会帮手"
            except ImportError:
                # 如果psutil不可用，使用更底层的方法
                try:
                    # 使用SetProcessNameW（需要调用SetConsoleTitleA/W）
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    kernel32.SetConsoleTitleW("会帮手")
                except Exception:
                    pass
    except Exception:
        pass


def main():
    # 先设置Windows进程名称
    _set_windows_process_name()
    
    atexit.register(_cleanup_lock)
    if not _check_single_instance():
        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("提示")
        msg_box.setText("会帮手 已经在运行中！")
        msg_box.exec()
        return
    
    app = QApplication(sys.argv)
    app.setApplicationName("会帮手")
    app.setApplicationDisplayName("MeetTimer")
    app.setOrganizationName("GAC")
    app.setStyleSheet(APP_STYLESHEET)

    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, 'icon.png')
    else:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.png')
    app.setWindowIcon(QIcon(icon_path))

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
    window.activateWindow()
    window.raise_()
    window._register_hotkeys()

    def delayed_init():
        window._create_float_timer()
        window._recover_in_progress_meeting()

    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, delayed_init)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
