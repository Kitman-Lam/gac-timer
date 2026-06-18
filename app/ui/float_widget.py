import math

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QAction, QRadialGradient
from PySide6.QtWidgets import QWidget, QApplication, QMenu

from app.ui.theme import (
    DANGER,
    FLOAT_WIDGET_SIZE,
    FONT_FAMILY,
    PRIMARY,
    TEXT_PRIMARY,
    WARNING,
    format_time,
)

BLUE_GRADIENT_CENTER = QColor("#003388")
BLUE_GRADIENT_OUTER = QColor("#3488ff")
ORANGE_GRADIENT_CENTER = QColor("#b35000")
ORANGE_GRADIENT_OUTER = QColor("#ffaa22")
RED_GRADIENT_CENTER = QColor("#88001E")
RED_GRADIENT_OUTER = QColor("#FF0000")

FLOAT_SIZE_MAP = {
    "small": 100,
    "medium": 120,
    "large": 150,
}


class FloatTimer(QWidget):
    close_clicked = Signal()
    pause_requested = Signal()
    reset_requested = Signal()
    enter_discussion_requested = Signal()
    next_topic_requested = Signal()
    add_temp_topic_requested = Signal()
    end_meeting_requested = Signal()
    start_meeting_requested = Signal()

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
        self._phase = "presentation"

        self._topic_name = ""
        self._scroll_offset = 0.0
        self._scroll_speed = 0.75
        self._show_topic_name = True
        self._actual_seconds = 0.0

        self._warning_minutes = 5
        self._overtime_minutes = 5

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.setWindowOpacity(self._opacity_percent / 100.0)
        self._apply_size()
        self._center_on_screen()

    def _opacity_alpha(self, alpha: int) -> int:
        if self._opacity_percent >= 100:
            return alpha
        return int(alpha * self._opacity_percent / 100.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 4

        # 绘制背景圆
        self._draw_background_circle(painter, cx, cy, radius)
        
        self._draw_pie(painter, cx, cy, radius)

        self._draw_center_text(painter, cx, cy, radius)

        if self._is_running:
            self._draw_top_text(painter, cx, cy, radius)
            self._draw_bottom_text(painter, cx, cy, radius)

        painter.end()

    def _draw_background_circle(self, painter: QPainter, cx: float, cy: float, radius: float):
        bg_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QColor(200, 200, 200, self._opacity_alpha(80)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(bg_rect)

    def _draw_pie(self, painter: QPainter, cx: float, cy: float, radius: float):
        pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        if self._is_overtime:
            gradient = QRadialGradient(cx, cy, radius)
            gradient.setColorAt(0, QColor(RED_GRADIENT_OUTER))
            gradient.setColorAt(1, QColor(RED_GRADIENT_CENTER))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(0, 0, 0, self._opacity_alpha(30)), 1))
            painter.drawEllipse(pie_rect)
            return

        if not self._is_running:
            gradient = QRadialGradient(cx, cy, radius)
            gradient.setColorAt(0, QColor(BLUE_GRADIENT_OUTER))
            gradient.setColorAt(1, QColor(BLUE_GRADIENT_CENTER))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(0, 0, 0, self._opacity_alpha(30)), 1))
            painter.drawEllipse(pie_rect)
            return

        if self._progress <= 0:
            return

        if self._phase == "qa" and not self._is_overtime:
            gradient = QRadialGradient(cx, cy, radius)
            if self._warning_mode:
                gradient.setColorAt(0, QColor(ORANGE_GRADIENT_OUTER))
                gradient.setColorAt(1, QColor(ORANGE_GRADIENT_CENTER))
            else:
                gradient.setColorAt(0, QColor(BLUE_GRADIENT_OUTER))
                gradient.setColorAt(1, QColor(BLUE_GRADIENT_CENTER))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(0, 0, 0, self._opacity_alpha(30)), 1))
            painter.drawEllipse(pie_rect)
            return

        remaining_ratio = max(0.0, 1.0 - min(self._progress, 1.0))

        gradient = QRadialGradient(cx, cy, radius)
        if self._warning_mode:
            gradient.setColorAt(0, QColor(ORANGE_GRADIENT_OUTER))
            gradient.setColorAt(1, QColor(ORANGE_GRADIENT_CENTER))
        else:
            gradient.setColorAt(0, QColor(BLUE_GRADIENT_OUTER))
            gradient.setColorAt(1, QColor(BLUE_GRADIENT_CENTER))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(0, 0, 0, self._opacity_alpha(30)), 1))
        span_angle = int(remaining_ratio * 360 * -16)
        painter.drawPie(pie_rect, 90 * 16, span_angle)

    def _draw_glow_text(self, painter: QPainter, text: str,
                        font: QFont, fill_color: QColor,
                        cx: float, cy: float, line2: str = None,
                        fixed_width: float = None,
                        stroke_color: QColor = None):
        lines = [text]
        if line2:
            lines.append(line2)

        full_path = QPainterPath()
        for i, line in enumerate(lines):
            path = QPainterPath()
            path.addText(0, 0, font, line)
            br = path.boundingRect()
            width = fixed_width if fixed_width is not None else br.width()
            y_offset = -br.y() + cy - (len(lines) * br.height() / 2) + i * (br.height() + 12)
            path.translate(-br.x() + cx - width / 2, y_offset)
            full_path.addPath(path)

        stroke_width = max(1.5, self._current_size * 0.015)
        if stroke_color is None:
            stroke_color = QColor(0, 0, 0, self._opacity_alpha(255))
        painter.setPen(QPen(stroke_color, stroke_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(full_path)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPath(full_path)

    def _draw_top_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        if not self._show_topic_name:
            return

        text = self._topic_name if self._topic_name else "等待开始"

        font_size = max(8, int(radius * 0.18))
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)

        max_width = int(radius * 1.4)
        y = cy - radius * 0.45
        fill_color = QColor(255, 255, 255)

        if self._show_topic_name and text_width > max_width:
            clip_rect = QRectF(cx - max_width / 2, y - font_size, max_width, font_size * 2)
            painter.save()
            painter.setClipRect(clip_rect)

            x1 = cx + max_width / 2 - self._scroll_offset
            x2 = x1 + text_width + 40
            self._draw_glow_text(painter, text, font, fill_color, x1, y)
            self._draw_glow_text(painter, text, font, fill_color, x2, y)

            painter.restore()
        else:
            self._draw_glow_text(painter, text, font, fill_color, cx, y)

    def _draw_bottom_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        if self._phase == "qa":
            text = "讨论暂停" if self._is_paused else "讨论中"
        else:
            if self._is_paused:
                text = "汇报暂停"
            elif self._is_overtime:
                text = "汇报超时"
            else:
                text = "汇报中"

        font_size = max(8, int(radius * 0.18))
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        painter.setFont(font)

        y = cy + radius * 0.45

        if self._is_paused:
            fill_color = QColor(0xEB, 0x09, 0x1F)
            stroke_color = QColor(255, 255, 255)
        else:
            fill_color = QColor(255, 255, 255)
            stroke_color = None
        self._draw_glow_text(painter, text, font, fill_color, cx, y, stroke_color=stroke_color)

    def _draw_center_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        max_text_width = int(radius * 2 * 0.85)

        if not self._is_running:
            time_str = "会帮手"
        elif self._phase == "qa":
            time_str = format_time(self._actual_seconds)
        elif self._is_overtime:
            time_str = format_time(self._overtime)
        else:
            time_str = format_time(self._remaining)

        font_size = int(radius * 0.45) if self._is_running else int(radius * 0.35)
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(time_str) > max_text_width and font_size > 8:
            font_size -= 1
            font = QFont(FONT_FAMILY, font_size, QFont.Bold)
            fm = QFontMetrics(font)

        ref_str = "00:00" if self._is_running else "会帮手"
        ref_width = fm.horizontalAdvance(ref_str)
        painter.setFont(font)
        fill_color = QColor(255, 255, 255)
        self._draw_glow_text(painter, time_str, font, fill_color, cx, cy, fixed_width=ref_width)

    def showEvent(self, event):
        super().showEvent(event)
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
            else:
                self._center_on_screen()
        except (ValueError, TypeError):
            self._center_on_screen()

    def _center_on_screen(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = 100
        self.move(x, y)

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
        if event.modifiers() & Qt.ControlModifier:
            self._show_topic_name = not self._show_topic_name
            self._scroll_offset = 0.0
            self.update()
        else:
            self.pause_requested.emit()

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
        self._actual_seconds = tick_data.get("actual_seconds", 0.0)
        self._is_overtime = is_overtime
        self._is_paused = is_paused
        self._is_running = state != "idle"

        self._warning_mode = is_countdown and not is_overtime and 0 < remaining <= self._warning_minutes * 60

        if self._is_running and self._show_topic_name:
            self._scroll_offset += self._scroll_speed
            font_size = max(8, int(self._current_size / 2 * 0.18))
            fm = QFontMetrics(QFont(FONT_FAMILY, font_size, QFont.Bold))
            text = self._topic_name if self._topic_name else "等待开始"
            text_width = fm.horizontalAdvance(text)
            if self._scroll_offset > text_width + 40:
                self._scroll_offset = 0.0

        self.update()

    def set_topic_info(self, topic_name: str, phase: str):
        self._topic_name = topic_name or ""
        self._phase = phase
        self._scroll_offset = 0.0
        self.update()

    def set_reminder_config(self, remaining_minutes: int, overtime_minutes: int):
        self._warning_minutes = remaining_minutes
        self._overtime_minutes = overtime_minutes

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        action_text = "开始" if self._is_paused else "暂停"
        pause_action = QAction(action_text, self)
        pause_action.triggered.connect(self.pause_requested.emit)
        menu.addAction(pause_action)

        reset_action = QAction("重置", self)
        reset_action.triggered.connect(self.reset_requested.emit)
        menu.addAction(reset_action)

        menu.addSeparator()

        enter_discussion_action = QAction("进入讨论", self)
        enter_discussion_action.triggered.connect(self.enter_discussion_requested.emit)
        menu.addAction(enter_discussion_action)

        next_topic_action = QAction("下一议题", self)
        next_topic_action.triggered.connect(self.next_topic_requested.emit)
        menu.addAction(next_topic_action)

        menu.addSeparator()

        add_temp_topic_action = QAction("+ 临时议题", self)
        add_temp_topic_action.triggered.connect(self.add_temp_topic_requested.emit)
        menu.addAction(add_temp_topic_action)

        end_meeting_action = QAction("结束会议" if self._is_running else "开始会议", self)
        if self._is_running:
            end_meeting_action.triggered.connect(self.end_meeting_requested.emit)
        else:
            end_meeting_action.triggered.connect(self.start_meeting_requested.emit)
        menu.addAction(end_meeting_action)

        menu.exec_(event.globalPos())

    def set_opacity(self, opacity: int):
        self._opacity_percent = max(10, min(100, opacity))
        self.setWindowOpacity(self._opacity_percent / 100.0)
        self.update()

    def set_size(self, size_key: str):
        if size_key in FLOAT_SIZE_MAP:
            self._float_size = size_key
            self._current_size = FLOAT_SIZE_MAP[size_key]
            self._apply_size()

    def set_show_topic_name(self, show: bool):
        self._show_topic_name = show
        self._scroll_offset = 0.0
        self.update()

    def _apply_size(self):
        self.setFixedSize(self._current_size, self._current_size)