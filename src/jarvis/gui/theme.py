"""Тема Jarvis в стиле кибербез-терминала (под портфолио).

Палитра: почти чёрный фон, неоново-зелёный акцент (#00ff9c), циан (#34e0ff),
моноширинный JetBrains Mono для «терминальных» элементов. Имена констант
сохранены прежними — чтобы остальной GUI не переписывать.
"""
from __future__ import annotations


class Colors:
    """Палитра «hacker terminal»: зелёный неон на чёрном."""

    # Базовый фон
    BG_DARKEST = "#04070a"        # рамки, заголовок окна
    BG_DARKER = "#070a0d"         # фон сайдбара (--bg)
    BG_DARK = "#0a1016"           # фон главного окна (--term-track)
    BG_NORMAL = "#0f1721"         # карточки, инпуты (--panel)
    BG_LIGHT = "#152232"          # hover
    BG_LIGHTER = "#1c2733"        # selected / pressed (--border)

    # Акцент — неоновый зелёный
    ACCENT = "#00ff9c"            # основной
    ACCENT_HOVER = "#5effc0"      # светлее при наведении
    ACCENT_DARK = "#00b86f"       # темнее (--accent-dim)
    ACCENT_GLOW = "#34e0ff"       # циан — вторичный акцент/подсветка

    # Текст
    TEXT_PRIMARY = "#cfe3d6"      # основной (зеленовато-белый)
    TEXT_SECONDARY = "#6f8a7d"    # приглушённый (--muted)
    TEXT_MUTED = "#4a5d54"        # ещё бледнее
    TEXT_ON_ACCENT = "#04130b"    # тёмный текст на зелёном

    # Статусы
    SUCCESS = "#00ff9c"
    WARNING = "#ffcb6b"
    ERROR = "#ff5f56"

    # Сообщения
    BUBBLE_USER = "#00b86f"       # зелёный пузырь пользователя
    BUBBLE_AGENT = "#0f1721"      # тёмный пузырь агента
    BUBBLE_SYSTEM = "#0d1318"     # системные

    # Граница
    BORDER = "#1c2733"
    BORDER_FOCUS = "#00ff9c"


# Моноширинный и основной шрифты (с фолбэками, если JetBrains Mono не установлен)
MONO = '"JetBrains Mono", "Cascadia Code", "Consolas", monospace'
SANS = '"Inter", "Segoe UI", "Roboto", sans-serif'


# QSS — глобальный стиль для всего приложения
GLOBAL_QSS = f"""
* {{
    font-family: {SANS};
    color: {Colors.TEXT_PRIMARY};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {Colors.BG_DARK};
}}

/* === Кастомный заголовок === */
#TitleBar {{
    background-color: {Colors.BG_DARKEST};
    border-bottom: 1px solid {Colors.BORDER};
}}
#TitleBar QLabel#TitleText {{
    color: {Colors.ACCENT};
    font-family: {MONO};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
#TitleBar QPushButton {{
    background-color: transparent;
    border: none;
    color: {Colors.TEXT_SECONDARY};
    font-size: 14px;
    min-width: 46px;
    max-width: 46px;
    min-height: 32px;
    max-height: 32px;
}}
#TitleBar QPushButton:hover {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.ACCENT};
}}
#TitleBar QPushButton#CloseBtn:hover {{
    background-color: {Colors.ERROR};
    color: #04070a;
}}

/* === Боковая панель === */
#Sidebar {{
    background-color: {Colors.BG_DARKER};
    border-right: 1px solid {Colors.BORDER};
}}
#SidebarLogo {{
    color: {Colors.ACCENT};
    font-family: {MONO};
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 16px;
}}
QPushButton#NavButton {{
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: {Colors.TEXT_SECONDARY};
    font-family: {MONO};
    text-align: left;
    padding: 12px 16px 12px 18px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#NavButton:hover {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.TEXT_PRIMARY};
}}
QPushButton#NavButton:checked {{
    background-color: {Colors.BG_LIGHT};
    border-left: 3px solid {Colors.ACCENT};
    color: {Colors.ACCENT};
    font-weight: 700;
}}

/* === Карточки и контейнеры === */
QFrame#Card {{
    background-color: {Colors.BG_NORMAL};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
}}

/* === Кнопки === */
QPushButton {{
    background-color: {Colors.BG_NORMAL};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-family: {MONO};
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {Colors.BG_LIGHT};
    border-color: {Colors.ACCENT};
    color: {Colors.ACCENT};
}}
QPushButton:pressed {{
    background-color: {Colors.BG_LIGHTER};
}}
QPushButton#Primary {{
    background-color: {Colors.ACCENT};
    border: 1px solid {Colors.ACCENT};
    color: {Colors.TEXT_ON_ACCENT};
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background-color: {Colors.ACCENT_HOVER};
    border-color: {Colors.ACCENT_HOVER};
    color: {Colors.TEXT_ON_ACCENT};
}}
QPushButton#Primary:pressed {{
    background-color: {Colors.ACCENT_DARK};
}}
QPushButton#Primary:disabled {{
    background-color: {Colors.BG_LIGHT};
    border-color: {Colors.BORDER};
    color: {Colors.TEXT_MUTED};
}}

/* === Поля ввода === */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    color: {Colors.TEXT_PRIMARY};
    font-family: {MONO};
    font-size: 13px;
    selection-background-color: {Colors.ACCENT};
    selection-color: {Colors.TEXT_ON_ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border: 1px solid {Colors.ACCENT};
}}
QLineEdit::placeholder {{
    color: {Colors.TEXT_MUTED};
}}

/* === Выпадающие списки (выбор модели) === */
QComboBox {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    color: {Colors.TEXT_PRIMARY};
    font-family: {MONO};
    font-size: 13px;
}}
QComboBox:hover {{
    border-color: {Colors.ACCENT};
}}
QComboBox:focus {{
    border-color: {Colors.ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {Colors.ACCENT};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_NORMAL};
    border: 1px solid {Colors.ACCENT};
    border-radius: 6px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT};
    selection-color: {Colors.TEXT_ON_ACCENT};
    outline: none;
    padding: 4px;
}}

/* === Скроллы === */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {Colors.BG_LIGHTER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Colors.ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.BG_LIGHTER};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Colors.ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* === Чекбоксы === */
QCheckBox {{
    color: {Colors.TEXT_PRIMARY};
    font-family: {MONO};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid {Colors.TEXT_MUTED};
    background-color: {Colors.BG_DARK};
}}
QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
    image: none;
}}
QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}

/* === Лейблы === */
QLabel {{
    color: {Colors.TEXT_PRIMARY};
    background: transparent;
}}
QLabel#Subtitle {{
    color: {Colors.TEXT_SECONDARY};
    font-family: {MONO};
    font-size: 12px;
}}
QLabel#Heading {{
    font-family: {MONO};
    font-size: 18px;
    font-weight: 700;
    color: {Colors.ACCENT};
}}

/* === Tooltips === */
QToolTip {{
    background-color: {Colors.BG_DARKEST};
    color: {Colors.ACCENT};
    border: 1px solid {Colors.ACCENT};
    border-radius: 4px;
    font-family: {MONO};
    padding: 4px 8px;
}}

/* === Меню === */
QMenu {{
    background-color: {Colors.BG_NORMAL};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {Colors.ACCENT};
    color: {Colors.TEXT_ON_ACCENT};
}}
"""
