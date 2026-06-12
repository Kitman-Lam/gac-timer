import math

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget, QApplication

from app.ui.theme import (
    DANGER,
    FLOAT_WIDGET_SIZE,
    FONT_FAMILY,
    PRIMARY,
    TEXT_PRIMARY,
    WARNING,
    format_time,
)
from app.utils.win32_api import set_window_topmost

ALERT_ORANGE = "#FF6B35"


FLOAT_SIZE_MAP = {
    "small": 100,
    "medium": 120,
    "large": 150,
}


class FloatTimer(QWidget):
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset = QPoint()
        self._opacity_percent = 85
        self._float_size = "medium"
        self._current_size = FLOAT_SIZE_MAP["medium"]

        self._progress = 0.0
        self._remaining = 0.0
        self._overtime = 0.0
        self._is_overtime = False
        self._is_paused = False
        self._is_running = False
        self._warning_mode = False
        self._blink_visible = True
        self._blink_counter = 0
        self._blink_phase = "idle"
        self._was_overtime = False
        self._last_flash_5min = 0
        self._seesaw_frame = 0
        self._seesaw_active = False
        self._seesaw_text = ""
        self._alert_text = ""

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._apply_size()

    def _opacity_alpha(self, alpha: int) -> int:
        return int(alpha * self._opacity_percent / 100.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 12

        self._draw_pie(painter, cx, cy, radius)
        self._draw_center_text(painter, cx, cy, radius)

        if self._seesaw_active:
            self._draw_seesaw_text(painter, cx, cy + radius + 14)

        painter.end()

    def _draw_pie(self, painter: QPainter, cx: float, cy: float, radius: float):
        pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(Qt.NoPen)

        if self._is_overtime:
            if self._alert_text:
                bright = QColor(ALERT_ORANGE)
                bright.setAlpha(self._opacity_alpha(255))
                light = QColor(ALERT_ORANGE)
                light.setAlpha(self._opacity_alpha(140))
                painter.setBrush(bright if self._blink_visible else light)
            elif self._blink_visible:
                c = QColor(DANGER)
                c.setAlpha(self._opacity_alpha(255))
                painter.setBrush(c)
            else:
                light_red = QColor(DANGER)
                light_red.setAlpha(self._opacity_alpha(140))
                painter.setBrush(light_red)
            painter.drawEllipse(pie_rect)
            return

        if not self._is_running:
            idle_bg = QColor(0, 0, 0, 128)
            idle_bg.setAlpha(self._opacity_alpha(128))
            painter.setBrush(idle_bg)
            painter.drawEllipse(pie_rect)
            return

        if self._progress <= 0:
            return

        remaining_ratio = max(0.0, 1.0 - min(self._progress, 1.0))

        if self._warning_mode:
            pie_color = QColor(WARNING)
        else:
            pie_color = QColor(PRIMARY)

        pie_color.setAlpha(self._opacity_alpha(255))
        painter.setBrush(pie_color)
        span_angle = int(remaining_ratio * 360 * -16)
        painter.drawPie(pie_rect, 90 * 16, span_angle)

    def _draw_text_with_outline(self, painter: QPainter, text: str,
                                 font: QFont, fill_color: QColor,
                                 cx: float, cy: float, line2: str = None):
        lines = [text]
        if line2:
            lines.append(line2)

        full_path = QPainterPath()
        for i, line in enumerate(lines):
            path = QPainterPath()
            path.addText(0, 0, font, line)
            br = path.boundingRect()
            y_offset = -br.y() + cy - (len(lines) * br.height() / 2) + i * (br.height() + 4)
            path.translate(-br.x() + cx - br.width() / 2, y_offset)
            full_path.addPath(path)

        painter.setPen(QPen(QColor(255, 255, 255, self._opacity_alpha(200)), 1.8))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(full_path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPath(full_path)

    def _draw_center_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        max_text_width = int(radius * 2 * 0.95)

        if self._alert_text:
            parts = self._alert_text.split("\n")
            line1 = parts[0] if len(parts) > 0 else ""
            line2 = parts[1] if len(parts) > 1 else None
            font = QFont(FONT_FAMILY, 11, QFont.Bold)
            fm = QFontMetrics(font)
            while fm.horizontalAdvance(line1) > max_text_width and font.pointSize() > 6:
                font.setPointSize(font.pointSize() - 1)
                fm = QFontMetrics(font)
            self._draw_text_with_outline(painter, line1, font,
                                         QColor(255, 255, 255), cx, cy, line2)
        elif self._is_overtime:
            time_str = format_time(self._overtime)
            font = QFont(FONT_FAMILY, 11, QFont.Bold)
            fm = QFontMetrics(font)
            while fm.horizontalAdvance(time_str) > max_text_width and font.pointSize() > 6:
                font.setPointSize(font.pointSize() - 1)
                fm = QFontMetrics(font)
            fill_color = QColor(255, 255, 255)
            self._draw_text_with_outline(painter, time_str, font, fill_color, cx, cy)
        elif not self._is_running:
            time_str = "--:--"
            font = QFont(FONT_FAMILY, 11, QFont.Bold)
            fm = QFontMetrics(font)
            while fm.horizontalAdvance(time_str) > max_text_width and font.pointSize() > 6:
                font.setPointSize(font.pointSize() - 1)
                fm = QFontMetrics(font)
            self._draw_text_with_outline(painter, time_str, font, QColor(TEXT_PRIMARY), cx, cy)
        else:
            time_str = format_time(self._remaining)
            font = QFont(FONT_FAMILY, 11, QFont.Bold)
            fm = QFontMetrics(font)
            while fm.horizontalAdvance(time_str) > max_text_width and font.pointSize() > 6:
                font.setPointSize(font.pointSize() - 1)
                fm = QFontMetrics(font)
            self._draw_text_with_outline(painter, time_str,
                                         font, QColor(TEXT_PRIMARY), cx, cy)

    def _draw_seesaw_text(self, painter: QPainter, cx: float, y: float):
        font = QFont(FONT_FAMILY, 9)
        path = QPainterPath()
        path.addText(0, 0, font, self._seesaw_text)
        br = path.boundingRect()

        cycle = 30
        phase = (self._seesaw_frame % cycle) / cycle
        offset_x = math.sin(phase * math.pi * 4) * 6

        path.translate(-br.x() + cx - br.width() / 2 + offset_x,
                       -br.y() + y)

        painter.setPen(QPen(QColor(255, 255, 255, self._opacity_alpha(180)), 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ALERT_ORANGE))
        painter.drawPath(path)

    def showEvent(self, event):
        super().showEvent(event)
        hwnd = int(self.winId())
        set_window_topmost(hwnd, True)
        self._restore_position()

    def hideEvent(self, event):
        self._save_position()
        super().hideEvent(event)

    def _save_position(self):
        from app.core.database import DatabaseManager
        db = DatabaseManager()
        pos = self.pos()
        db.set_setting("float_pos_x", str(pos.x()))
        db.set_setting("float_pos_y", str(pos.y()))

    def _restore_position(self):
        from app.core.database import DatabaseManager
        db = DatabaseManager()
        try:
            x = int(db.get_setting("float_pos_x", "-1"))
            y = int(db.get_setting("float_pos_y", "-1"))
            if x >= 0 and y >= 0:
                self.move(x, y)
        except (ValueError, TypeError):
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            screen = QApplication.primaryScreen().geometry()
            w = self.width()
            h = self.height()
            new_pos.setX(max(screen.left(), min(new_pos.x(), screen.right() - w)))
            new_pos.setY(max(screen.top(), min(new_pos.y(), screen.bottom() - h)))
            self.move(new_pos)

    def mouseDoubleClickEvent(self, event):
        self.close_clicked.emit()

    def update_display(self, tick_data: dict):
        progress = tick_data.get("progress", 0.0)
        remaining = tick_data.get("remaining_seconds", 0.0)
        overtime = tick_data.get("overtime_seconds", 0.0)
        is_overtime = tick_data.get("is_overtime", False)
        is_paused = tick_data.get("is_paused", False)
        is_countdown = tick_data.get("is_countdown", False)
        state = tick_data.get("state", "idle")

        self._progress = progress
        self._remaining = remaining
        self._overtime = overtime
        self._is_overtime = is_overtime
        self._is_paused = is_paused
        self._is_running = state != "idle"

        self._warning_mode = is_countdown and not is_overtime and 0 < remaining <= 30

        if is_overtime:
            if not self._was_overtime:
                self._blink_phase = "initial"
                self._blink_counter = 0
                self._last_flash_5min = 0
                self._seesaw_active = False
                self._alert_text = ""
            else:
                self._blink_counter += 1

            current_5min_block = int(overtime // 300) if overtime > 0 else 0

            if self._blink_phase == "initial":
                if self._blink_counter < 30:
                    self._blink_visible = (self._blink_counter // 5) % 2 == 0
                else:
                    self._blink_phase = "idle"
                    self._blink_visible = False
            elif self._blink_phase == "idle":
                if current_5min_block > self._last_flash_5min:
                    self._blink_phase = "5min"
                    self._blink_counter = 0
                    self._blink_visible = True
                    minutes = current_5min_block * 5
                    self._alert_text = f"超时\n{minutes}分钟"
                else:
                    self._blink_visible = False
            elif self._blink_phase == "5min":
                if self._blink_counter < 50:
                    self._blink_visible = (self._blink_counter // 5) % 2 == 0
                    if self._blink_counter == 49:
                        self._last_flash_5min = current_5min_block
                        self._seesaw_text = self._alert_text.replace("\n", "")
                        self._seesaw_frame = 0
                        self._seesaw_active = True
                else:
                    self._blink_phase = "idle"
                    self._blink_visible = False
                    self._alert_text = ""

            self._was_overtime = True
        else:
            self._blink_visible = True
            self._blink_counter = 0
            self._blink_phase = "idle"
            self._was_overtime = False
            self._last_flash_5min = 0
            self._seesaw_active = False
            self._alert_text = ""

        if self._seesaw_active:
            self._seesaw_frame += 1
            if self._seesaw_frame > 90:
                self._seesaw_active = False

        self.update()

    def set_topic_info(self, topic_name: str, phase: str):
        pass

    def set_opacity(self, opacity: int):
        self._opacity_percent = max(10, min(100, opacity))
        self.update()

    def set_size(self, size_key: str):
        if size_key in FLOAT_SIZE_MAP:
            self._float_size = size_key
            self._current_size = FLOAT_SIZE_MAP[size_key]
            self._apply_size()

    def _apply_size(self):
        self.setFixedSize(self._current_size, self._current_size)