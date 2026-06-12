import math

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.ui.theme import (
    DANGER,
    FONT_FAMILY,
    FONT_SIZE_LARGE,
    FONT_SIZE_SMALL,
    PRIMARY,
    RING_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TIMER_CIRCLE_SIZE,
    WARNING,
    format_time,
)


class TimerCircle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._remaining = 0.0
        self._overtime = 0.0
        self._is_overtime = False
        self._is_paused = False
        self._phase_name = ""
        self._warning_mode = False
        self._blink_visible = True
        self._blink_counter = 0

        self.setFixedSize(TIMER_CIRCLE_SIZE, TIMER_CIRCLE_SIZE)

    def minimumSizeHint(self):
        return QSize(TIMER_CIRCLE_SIZE, TIMER_CIRCLE_SIZE)

    def sizeHint(self):
        return QSize(TIMER_CIRCLE_SIZE, TIMER_CIRCLE_SIZE)

    def set_progress(self, progress: float, remaining: float, overtime: float,
                     is_overtime: bool, is_paused: bool):
        self._progress = progress
        self._remaining = remaining
        self._overtime = overtime
        self._is_overtime = is_overtime
        self._is_paused = is_paused
        if is_overtime:
            self._blink_counter += 1
            if self._blink_counter % 10 < 5:
                self._blink_visible = True
            else:
                self._blink_visible = False
        else:
            self._blink_visible = True
            self._blink_counter = 0
        self.update()

    def set_phase_name(self, name: str):
        self._phase_name = name
        self.update()

    def set_warning_mode(self, enabled: bool):
        self._warning_mode = enabled
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 16

        self._draw_pie(painter, center_x, center_y, radius)
        self._draw_center_text(painter, center_x, center_y, radius)
        self._draw_phase_label(painter, center_x, center_y, radius)

        painter.end()

    def _draw_pie(self, painter: QPainter, cx: float, cy: float, radius: float):
        pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(RING_BG))
        painter.drawEllipse(pie_rect)

        if self._is_overtime:
            color = QColor(DANGER)
            if not self._blink_visible:
                color.setAlpha(120)
            painter.setBrush(color)
            painter.drawEllipse(pie_rect)
            return

        if self._progress <= 0:
            return

        remaining_ratio = max(0.0, 1.0 - min(self._progress, 1.0))

        if self._warning_mode:
            pie_color = QColor(WARNING)
        else:
            pie_color = QColor(PRIMARY)

        painter.setBrush(pie_color)
        span_angle = int(remaining_ratio * 360 * -16)
        painter.drawPie(pie_rect, 90 * 16, span_angle)

    def _draw_text_with_outline(self, painter: QPainter, text: str,
                                 font: QFont, fill_color: QColor,
                                 rect: QRectF, align: int):
        path = QPainterPath()
        path.addText(rect.left(), rect.center().y() + font.pixelSize() * 0.35,
                     font, text)

        path.translate((rect.width() - path.boundingRect().width()) / 2
                       + rect.left() - path.boundingRect().left(),
                       0)

        painter.setPen(QPen(QColor(0, 0, 0, 160), 2.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPath(path)

    def _draw_center_text(self, painter: QPainter, cx: float, cy: float,
                          radius: float):
        if self._is_overtime:
            time_str = format_time(self._overtime)
            font = QFont(FONT_FAMILY, FONT_SIZE_LARGE, QFont.Bold)
            fill_color = QColor(DANGER)
        else:
            time_str = format_time(self._remaining)
            font = QFont(FONT_FAMILY, FONT_SIZE_LARGE, QFont.Bold)
            fill_color = QColor(TEXT_PRIMARY)

        text_rect = QRectF(cx - radius, cy - 20, radius * 2, 40)
        self._draw_text_with_outline(painter, time_str, font, fill_color,
                                     text_rect, Qt.AlignCenter)

        if self._is_paused:
            font = QFont(FONT_FAMILY, FONT_SIZE_SMALL)
            painter.setFont(font)
            painter.setPen(QColor(TEXT_MUTED))
            paused_rect = QRectF(cx - radius, cy + 14, radius * 2, 20)
            painter.drawText(paused_rect, Qt.AlignCenter, "\u5df2\u6682\u505c")

    def _draw_phase_label(self, painter: QPainter, cx: float, cy: float,
                          radius: float):
        if not self._phase_name:
            return

        font = QFont(FONT_FAMILY, FONT_SIZE_SMALL)
        painter.setFont(font)
        painter.setPen(QColor(TEXT_SECONDARY))
        label_rect = QRectF(cx - radius, cy + 34, radius * 2, 20)
        painter.drawText(label_rect, Qt.AlignCenter, self._phase_name)