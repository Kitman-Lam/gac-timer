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

        self._pulse_active = False
        self._pulse_frame = 0
        self._last_5min_block = 0
        self._blink_counter = 0

        self._warning_minutes = 5
        self._overtime_minutes = 5

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.setWindowOpacity(self._opacity_percent / 100.0)
        self._apply_size()

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

        if self._is_running:
            self._draw_top_text(painter, cx, cy, radius)
            self._draw_bottom_text(painter, cx, cy, radius)
            if self._is_paused:
                self._draw_paused_text(painter, cx, cy, radius)
        self._draw_center_text(painter, cx, cy, radius)

        painter.end()

    def _draw_background_circle(self, painter: QPainter, cx: float, cy: float, radius: float):
        bg_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QColor(200, 200, 200, self._opacity_alpha(80)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(bg_rect)

    def _draw_pie(self, painter: QPainter, cx: float, cy: float, radius: float):
        pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        if self._is_overtime:
            if self._pulse_active:
                # 闪烁效果：快速闪烁，约 0.3 秒一次，持续 1 秒
                cycle = 20  # 更快的闪烁周期
                phase = self._pulse_frame % cycle
                if phase < 10:
                    alpha = 255
                else:
                    alpha = 100

                gradient = QRadialGradient(cx, cy, radius)
                gradient.setColorAt(0, QColor(RED_GRADIENT_OUTER))
                gradient.setColorAt(1, QColor(RED_GRADIENT_CENTER))
                
                # 手动设置渐变透明度
                if alpha < 255:
                    gradient.setColorAt(0, QColor(RED_GRADIENT_OUTER.red(), RED_GRADIENT_OUTER.green(), RED_GRADIENT_OUTER.blue(), self._opacity_alpha(alpha)))
                    gradient.setColorAt(1, QColor(RED_GRADIENT_CENTER.red(), RED_GRADIENT_CENTER.green(), RED_GRADIENT_CENTER.blue(), self._opacity_alpha(alpha)))
                
                painter.setBrush(gradient)
            else:
                # 不闪烁时正常显示红色
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
                        cx: float, cy: float, line2: str = None):
        lines = [text]
        if line2:
            lines.append(line2)

        full_path = QPainterPath()
        for i, line in enumerate(lines):
            path = QPainterPath()
            path.addText(0, 0, font, line)
            br = path.boundingRect()
            y_offset = -br.y() + cy - (len(lines) * br.height() / 2) + i * (br.height() + 12)
            path.translate(-br.x() + cx - br.width() / 2, y_offset)
            full_path.addPath(path)

        stroke_width = max(1.5, self._current_size * 0.015)
        painter.setPen(QPen(QColor(0, 0, 0, self._opacity_alpha(255)), stroke_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(full_path)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPath(full_path)

    def _draw_top_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        if self._is_overtime:
            text = "超时"
        elif not self._is_running:
            text = "会议未开始"
        else:
            text = "剩余时间"

        font_size = max(8, int(radius * 0.18))
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        painter.setFont(font)

        y = cy - radius * 0.45

        fill_color = QColor(255, 255, 255)
        self._draw_glow_text(painter, text, font, fill_color, cx, y)

    def _draw_bottom_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        if self._is_overtime and self._is_paused:
            text = "暂停"
        elif self._phase == "qa":
            text = "讨论中"
        else:
            text = "汇报中"

        font_size = max(8, int(radius * 0.18))
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        painter.setFont(font)

        y = cy + radius * 0.45

        fill_color = QColor(255, 255, 255)
        self._draw_glow_text(painter, text, font, fill_color, cx, y)

    def _draw_center_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        max_text_width = int(radius * 2 * 0.85)

        if self._is_overtime and self._is_paused:
            time_str = "-" + format_time(self._overtime)
        elif self._is_overtime:
            time_str = format_time(self._overtime)
        elif not self._is_running:
            time_str = "--:--"
        else:
            time_str = format_time(self._remaining)

        font_size = int(radius * 0.45)
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(time_str) > max_text_width and font_size > 8:
            font_size -= 1
            font = QFont(FONT_FAMILY, font_size, QFont.Bold)
            fm = QFontMetrics(font)

        painter.setFont(font)
        fill_color = QColor(255, 255, 255)
        self._draw_glow_text(painter, time_str, font, fill_color, cx, cy)

    def _draw_paused_text(self, painter: QPainter, cx: float, cy: float, radius: float):
        if self._is_overtime and self._is_paused:
            blinking = self._blink_counter % 40 < 20
            if not blinking:
                return

        text = "暂停"
        font_size = max(8, int(radius * 0.18))
        font = QFont(FONT_FAMILY, font_size, QFont.Bold)
        painter.setFont(font)

        y = cy + radius * 0.75

        fill_color = QColor(DANGER)
        self._draw_glow_text(painter, text, font, fill_color, cx, y)

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

        self._warning_mode = is_countdown and not is_overtime and 0 < remaining <= self._warning_minutes * 60

        if is_overtime:
            overtime_seconds = max(0, int(overtime))
            current_interval_block = overtime_seconds // (self._overtime_minutes * 60) if self._overtime_minutes > 0 else 0
            if current_interval_block > self._last_5min_block:
                self._pulse_active = True
                self._pulse_frame = 0
                self._last_5min_block = current_interval_block

            if self._pulse_active:
                self._pulse_frame += 1
                # 持续 1 秒（约 60 帧）
                if self._pulse_frame > 60:
                    self._pulse_active = False
        else:
            self._pulse_active = False
            self._pulse_frame = 0
            self._last_5min_block = 0

        if self._is_paused:
            self._blink_counter = (self._blink_counter + 1) % 40

        self.update()

    def set_topic_info(self, topic_name: str, phase: str):
        self._phase = phase
        self.update()

    def set_reminder_config(self, warning_minutes: int, overtime_minutes: int):
        self._warning_minutes = warning_minutes
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

        end_meeting_action = QAction("结束会议", self)
        end_meeting_action.triggered.connect(self.end_meeting_requested.emit)
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

    def _apply_size(self):
        self.setFixedSize(self._current_size, self._current_size)