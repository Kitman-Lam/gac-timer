PRIMARY = "#0075DE"
PRIMARY_HOVER = "#005BAB"
PRIMARY_LIGHT = "#F2F9FF"
PRIMARY_DARK = "#005BAB"
WARNING = "#DD5B00"
DANGER = "#D92B2B"
DANGER_HOVER = "#B91C1C"
DANGER_LIGHT = "#FEF2F2"
SUCCESS = "#1AAE39"
BG_BASE = "#FFFFFF"
BG_SURFACE = "#F6F5F4"
BG_ELEVATED = "#EDECEB"
BG_INPUT = "#FFFFFF"
BG_DARK = "#FFFFFF"
BG_CARD = "#FFFFFF"
BORDER_DEFAULT = "rgba(0,0,0,0.1)"
BORDER_FOCUS = "#097FE8"
TEXT_PRIMARY = "rgba(0,0,0,0.95)"
TEXT_SECONDARY = "#615D59"
TEXT_MUTED = "#A39E98"
TEXT_DANGER = "#D92B2B"
RING_BG = "#EDECEB"
TRANSPARENT_BG = "#FFFFFF"
FONT_FAMILY = "Inter, Microsoft YaHei, Segoe UI"
FONT_SIZE_LARGE = 36
FONT_SIZE_MEDIUM = 15
FONT_SIZE_SMALL = 12
TIMER_CIRCLE_SIZE = 220
FLOAT_WIDGET_SIZE = 100

APP_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "{FONT_FAMILY}";
}}

QLabel {{
    color: {TEXT_PRIMARY};
}}

QPushButton {{
    background-color: rgba(0,0,0,0.05);
    color: {TEXT_PRIMARY};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    outline: none;
    height: 36px;
    max-height: 36px;
}}

QPushButton:hover {{
    background-color: rgba(0,0,0,0.08);
}}

QPushButton:pressed {{
    background-color: rgba(0,0,0,0.12);
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: rgba(0,0,0,0.03);
    cursor: not-allowed;
}}

QPushButton#primaryBtn {{
    background-color: {PRIMARY};
    color: #FFFFFF;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    min-width: 100px;
    height: 34px;
    max-height: 34px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {PRIMARY_HOVER};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {PRIMARY_DARK};
}}

QPushButton#primaryBtn:disabled {{
    color: rgba(255,255,255,0.5);
    background-color: rgba(0,0,0,0.15);
}}

QPushButton#dangerBtn {{
    background-color: transparent;
    color: {DANGER};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 14px;
    font-weight: 500;
    min-width: 80px;
    height: 32px;
    max-height: 32px;
}}

QPushButton#dangerBtn:hover {{
    background-color: {DANGER_LIGHT};
}}

QPushButton#dangerBtn:pressed {{
    background-color: rgba(217,43,43,0.15);
}}

QPushButton#dangerBtn:disabled {{
    color: {TEXT_MUTED};
    background-color: rgba(0,0,0,0.03);
    border-color: {BORDER_DEFAULT};
}}

QPushButton#secondaryBtn {{
    background-color: rgba(0,0,0,0.05);
    color: {TEXT_PRIMARY};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px 8px;
    font-size: 14px;
    font-weight: 600;
    min-width: 80px;
    height: 36px;
    max-height: 36px;
}}

QPushButton#secondaryBtn:hover {{
    background-color: rgba(0,0,0,0.08);
}}

QPushButton#secondaryBtn:pressed {{
    background-color: rgba(0,0,0,0.12);
}}

QPushButton#secondaryBtn:disabled {{
    color: {TEXT_MUTED};
    background-color: rgba(0,0,0,0.03);
}}

QLineEdit, QSpinBox {{
    background-color: {BG_INPUT};
    color: rgba(0,0,0,0.9);
    border: 1px solid #DDDDDD;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: {FONT_SIZE_MEDIUM}px;
}}

QLineEdit:focus, QSpinBox:focus {{
    border: 2px solid {BORDER_FOCUS};
    padding: 5px 7px;
}}

QLineEdit::placeholder {{
    color: {TEXT_MUTED};
}}

QListWidget {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(0,0,0,0.05);
}}

QListWidget::item:selected {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}

QListWidget::item:hover {{
    background-color: {BG_SURFACE};
}}

QTableWidget {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 8px;
    gridline-color: rgba(0,0,0,0.05);
}}

QHeaderView::section {{
    background-color: {BG_SURFACE};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER_DEFAULT};
    padding: 8px 12px;
    font-weight: 600;
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 8px 12px;
}}

QTableWidget::item:selected {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background-color: rgba(0,0,0,0.15);
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: rgba(0,0,0,0.25);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal {{
    background-color: rgba(0,0,0,0.15);
    border-radius: 3px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: rgba(0,0,0,0.25);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 8px;
    background-color: #FFFFFF;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {PRIMARY};
}}

QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}

QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #DDDDDD;
    border-radius: 4px;
    padding: 6px 12px;
    color: rgba(0,0,0,0.9);
}}

QComboBox:focus {{
    border: 2px solid {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_DEFAULT};
    selection-background-color: {PRIMARY_LIGHT};
}}

QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #DDDDDD;
    border-radius: 3px;
    background-color: #FFFFFF;
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background-color: {BG_ELEVATED};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background-color: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.15);
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {BG_SURFACE};
}}

QDialog {{
    background-color: #FFFFFF;
    color: {TEXT_PRIMARY};
}}

QToolTip {{
    background-color: #31302E;
    color: #FFFFFF;
    border: none;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13px;
}}

QMenu {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {BG_SURFACE};
}}

QToolBar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid {BORDER_DEFAULT};
    spacing: 4px;
    padding: 4px 8px;
}}
"""


def format_time(seconds: float) -> str:
    total = int(max(0, seconds))
    minutes = total // 60
    secs = total % 60
    return f"{minutes:02d}:{secs:02d}"
