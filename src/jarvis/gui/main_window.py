"""Главное окно с боковой навигацией и кастомным заголовком."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from jarvis.gui.app_icon import make_icon
from jarvis.gui.bridge import bridge
from jarvis.gui.hotkey import HotkeyManager
from jarvis.gui.pages.chat_page import ChatPage
from jarvis.gui.pages.screen_page import ScreenPage
from jarvis.gui.pages.settings_page import SettingsPage
from jarvis.gui.widgets.sidebar import Sidebar
from jarvis.gui.widgets.title_bar import TitleBar


class _UpdateWorker(QThread):
    """Фоновая проверка обновлений на GitHub Releases."""

    found = Signal(object)

    def run(self) -> None:
        try:
            from jarvis.core.updater import check_for_update

            info = check_for_update()
            if info is not None:
                self.found.emit(info)
        except Exception:  # noqa: BLE001
            pass


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.setWindowIcon(make_icon(64))
        self.setMinimumSize(QSize(960, 640))
        self.resize(1200, 760)

        # Frameless: убираем стандартный заголовок Windows
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # --- Корневой контейнер ---
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Кастомный title-bar ---
        self.title_bar = TitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_toggled.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self._minimize_to_tray)
        outer.addWidget(self.title_bar)

        # --- Тело: sidebar + страницы ---
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(self._on_nav)
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.chat_page = ChatPage()
        self.screen_page = ScreenPage()
        self.settings_page = SettingsPage()
        self.pages.addWidget(self.chat_page)
        self.pages.addWidget(self.screen_page)
        self.pages.addWidget(self.settings_page)
        body.addWidget(self.pages, stretch=1)

        outer.addLayout(body, stretch=1)

        # --- Системный трей ---
        self._setup_tray()

        # --- Глобальный хоткей и wake-word ---
        self._setup_hotkey_and_wake()

        # --- Проверка обновлений (в фоне) ---
        self._update_info = None
        self._update_worker = _UpdateWorker()
        self._update_worker.found.connect(self._on_update)
        self._update_worker.start()

        # --- Изначальный статус ---
        self.title_bar.set_connection_status("connecting", "инициализация...")
        bridge.agent_replied.connect(self._on_agent_alive)
        bridge.agent_error.connect(self._on_agent_error)

    def _on_nav(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.title_bar.btn_max.setText("□")
        else:
            self.showMaximized()
            self.title_bar.btn_max.setText("❐")

    def _setup_hotkey_and_wake(self) -> None:
        # Глобальный хоткей: показать/скрыть окно
        self._hotkey = HotkeyManager()
        self._hotkey.triggered.connect(self._toggle_window)
        self._hotkey.start()

        # Wake-word: «джарвис» -> показать окно и начать голосовой ввод
        try:
            from jarvis.voice.wake import wake_word

            self._wake = wake_word
            self._wake.detected.connect(self._on_wake)
            self._wake.start()
        except Exception:  # noqa: BLE001
            self._wake = None

    def _toggle_window(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self._minimize_to_tray()
        else:
            self._restore_from_tray()

    def _on_wake(self) -> None:
        self._restore_from_tray()
        self.pages.setCurrentIndex(0)
        self.sidebar.select(0)
        try:
            self.chat_page._on_mic()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            pass

    def _on_update(self, info: object) -> None:
        """Показывает уведомление о доступном обновлении."""
        self._update_info = info
        version = getattr(info, "version", "?")
        url = getattr(info, "url", "")
        if self._tray is not None:
            self._tray.showMessage(
                "Доступно обновление Jarvis",
                f"Версия {version}. Нажмите, чтобы открыть страницу загрузки.",
                QSystemTrayIcon.MessageIcon.Information,
                6000,
            )
            try:
                self._tray.messageClicked.connect(self._open_update_page)
            except Exception:  # noqa: BLE001
                pass
        try:
            from jarvis.gui.widgets.message_bubble import Role

            self.chat_page._add_message(  # noqa: SLF001
                f"🔄 Доступна новая версия Jarvis {version}. Скачать: {url}",
                Role.SYSTEM,
            )
        except Exception:  # noqa: BLE001
            pass

    def _open_update_page(self) -> None:
        if self._update_info is not None:
            url = getattr(self._update_info, "url", "")
            if url:
                QDesktopServices.openUrl(QUrl(url))

    def _on_agent_alive(self, _text: str) -> None:
        self.title_bar.set_connection_status("online", "агент готов")

    def _on_agent_error(self, _msg: str) -> None:
        self.title_bar.set_connection_status("error", "ошибка подключения")

    # --- Системный трей ---

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return

        self._tray = QSystemTrayIcon(make_icon(64), self)
        self._tray.setToolTip("Jarvis AI")

        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        action_show: QAction = menu.addAction("Открыть Jarvis")
        action_show.triggered.connect(self._restore_from_tray)
        menu.addSeparator()
        action_quit: QAction = menu.addAction("Выйти")
        action_quit.triggered.connect(self._real_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_clicked)
        self._tray.show()

    def _on_tray_clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _minimize_to_tray(self) -> None:
        if self._tray is not None:
            self.hide()
            self._tray.showMessage(
                "Jarvis",
                "Свернут в трей. Чтобы выйти полностью — ПКМ по иконке.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self._real_quit()

    def _real_quit(self) -> None:
        from PySide6.QtWidgets import QApplication
        if self._tray is not None:
            self._tray.hide()
        if getattr(self, "_wake", None) is not None:
            self._wake.stop()
        bridge.stop()
        QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        # При нажатии крестика — просто прячем (если трей доступен)
        if self._tray is not None:
            event.ignore()
            self._minimize_to_tray()
        else:
            super().closeEvent(event)
