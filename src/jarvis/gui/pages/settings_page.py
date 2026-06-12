"""Страница настроек: выбор модели и конфигурация (пишет в .env)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from jarvis.gui.theme import Colors

# Человекочитаемые названия провайдеров для выпадающего списка.
_PROVIDERS = [
    ("glm", "GLM · Zhipu (основная, бесплатная)"),
    ("gemini", "Gemini · Google"),
    ("ollama", "Ollama · локально"),
]


class _Field(QFrame):
    """Карточка одного поля настроек: лейбл + контрол + хинт."""

    def __init__(self, label: str, hint: str, control: QWidget) -> None:
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title = QLabel(label)
        title.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(title)

        sub = QLabel(hint)
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(sub)

        layout.addSpacing(4)
        layout.addWidget(control)


class _SectionLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: 12px; font-weight: 700; "
            "font-family: 'JetBrains Mono','Consolas',monospace; padding-top: 8px;"
        )


class SettingsPage(QWidget):
    """Редактор настроек, который пишет напрямую в .env."""

    def __init__(self) -> None:
        super().__init__()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("./настройки")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 800; "
            "font-family: 'JetBrains Mono','Consolas',monospace;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Изменения сохраняются в .env. Перезапустите Jarvis для применения."
        )
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(subtitle)
        layout.addSpacing(6)

        from jarvis.core.config import settings

        # ===== Выбор модели =====
        layout.addWidget(_SectionLabel("# МОДЕЛЬ"))

        self._provider_combo = QComboBox()
        current_idx = 0
        for i, (key, label) in enumerate(_PROVIDERS):
            self._provider_combo.addItem(label, key)
            if key == settings.llm_provider:
                current_idx = i
        self._provider_combo.setCurrentIndex(current_idx)
        layout.addWidget(_Field(
            "Провайдер LLM",
            "Какая нейросеть управляет агентом. GLM — бесплатная и основная.",
            self._provider_combo,
        ))

        # --- GLM ---
        self._glm_key = QLineEdit(settings.glm_api_key)
        self._glm_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._glm_key.setPlaceholderText("ключ с open.bigmodel.cn")
        layout.addWidget(_Field(
            "GLM API ключ",
            "Бесплатный ключ: open.bigmodel.cn (модель glm-4-flash бесплатна)",
            self._glm_key,
        ))

        self._glm_model = QLineEdit(settings.glm_model)
        self._glm_model.setPlaceholderText("glm-4-flash")
        layout.addWidget(_Field(
            "Модель GLM",
            "Например: glm-4-flash (бесплатно), glm-4-plus, glm-4.5",
            self._glm_model,
        ))

        self._thinking_check = QCheckBox("🧠 Глубокое мышление (reasoning)")
        self._thinking_check.setChecked(settings.glm_thinking)
        layout.addWidget(_Field(
            "Глубокое мышление",
            "Модель сначала рассуждает «про себя», потом отвечает (как DeepSeek). "
            f"Использует reasoning-модель {settings.glm_thinking_model} (бесплатно).",
            self._thinking_check,
        ))

        # --- Gemini ---
        self._gem_key = QLineEdit(settings.gemini_api_key)
        self._gem_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gem_key.setPlaceholderText("AIza...")
        layout.addWidget(_Field(
            "Gemini API ключ",
            "Бесплатный ключ: aistudio.google.com/app/apikey",
            self._gem_key,
        ))

        self._gem_model = QLineEdit(settings.gemini_model)
        self._gem_model.setPlaceholderText("gemini-1.5-flash")
        layout.addWidget(_Field(
            "Модель Gemini",
            "Например: gemini-1.5-flash, gemini-2.5-flash",
            self._gem_model,
        ))

        # --- Ollama ---
        self._ollama_host = QLineEdit(settings.ollama_host)
        self._ollama_host.setPlaceholderText("http://localhost:11434")
        layout.addWidget(_Field(
            "Ollama хост",
            "Адрес локального сервера Ollama",
            self._ollama_host,
        ))

        self._ollama_model = QLineEdit(settings.ollama_model)
        self._ollama_model.setPlaceholderText("gpt-oss:20b")
        layout.addWidget(_Field(
            "Модель Ollama",
            "Установите: ollama pull gpt-oss:20b (открытая модель OpenAI, ~14 ГБ). "
            "Полегче: qwen2.5:7b. Нужна модель с поддержкой tools.",
            self._ollama_model,
        ))

        # ===== Знания и расширения =====
        layout.addWidget(_SectionLabel("# ЗНАНИЯ И РАСШИРЕНИЯ"))

        self._rag_check = QCheckBox("Подмешивать знания из базы (RAG) в ответы")
        self._rag_check.setChecked(settings.rag_enabled)
        layout.addWidget(_Field(
            "RAG",
            "Перед ответом ищет релевантные фрагменты в базе знаний плагинов",
            self._rag_check,
        ))

        self._mcp_check = QCheckBox("Подключать внешние MCP-серверы")
        self._mcp_check.setChecked(settings.mcp_enabled)
        layout.addWidget(_Field(
            "MCP-клиент",
            "Серверы берутся из mcp_servers.json. Требует пакет mcp (pip install mcp)",
            self._mcp_check,
        ))

        # ===== Голос =====
        layout.addWidget(_SectionLabel("# ГОЛОС"))

        self._tts_check = QCheckBox("Озвучивать ответы (TTS)")
        self._tts_check.setChecked(settings.tts_enabled)
        layout.addWidget(_Field(
            "Озвучка",
            "Офлайн через pyttsx3 (pip install pyttsx3). Тумблер 🔊 есть и в чате",
            self._tts_check,
        ))

        self._vosk_input = QLineEdit(settings.vosk_model_path)
        self._vosk_input.setPlaceholderText("./models/vosk-model-small-ru")
        layout.addWidget(_Field(
            "Модель Vosk (голосовой ввод)",
            "Путь к модели для распознавания речи. Скачать: alphacephei.com/vosk/models. "
            "Нужны: pip install vosk sounddevice",
            self._vosk_input,
        ))

        # ===== Мобильное приложение =====
        layout.addWidget(_SectionLabel("# МОБИЛЬНОЕ ПРИЛОЖЕНИЕ"))

        mobile_btn = QPushButton("📱  Запустить сервер для телефона")
        mobile_btn.clicked.connect(self._start_mobile)
        layout.addWidget(_Field(
            "Управление с телефона",
            "Поднимет сервер на этом ПК и покажет QR-код. Отсканируй телефоном "
            "(в одной Wi-Fi сети) → откроется приложение Jarvis → «На главный экран».",
            mobile_btn,
        ))

        # ===== Сервер =====
        layout.addWidget(_SectionLabel("# СЕРВЕР (удалённый доступ)"))

        host_row = QHBoxLayout()
        self._host_input = QLineEdit(settings.host)
        self._host_input.setPlaceholderText("0.0.0.0")
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(settings.port)
        host_row.addWidget(self._host_input, stretch=2)
        host_row.addWidget(self._port_input, stretch=1)
        host_holder = QWidget()
        host_holder.setLayout(host_row)
        layout.addWidget(_Field(
            "Адрес и порт сервера",
            "Только для серверного режима (мобильное приложение)",
            host_holder,
        ))

        self._token_input = QLineEdit(settings.auth_token)
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(_Field(
            "Auth Token",
            "Секрет для авторизации мобильного клиента",
            self._token_input,
        ))

        # ===== Безопасность / Observer =====
        layout.addWidget(_SectionLabel("# БЕЗОПАСНОСТЬ"))

        self._safe_root_input = QLineEdit(settings.safe_root)
        self._safe_root_input.setPlaceholderText("По умолчанию — рабочий стол")
        layout.addWidget(_Field(
            "Безопасная зона (SAFE_ROOT)",
            "Папка, в пределах которой Jarvis может создавать/удалять файлы",
            self._safe_root_input,
        ))

        self._observer_check = QCheckBox("Отслеживать время в приложениях")
        self._observer_check.setChecked(settings.enable_observer)
        layout.addWidget(_Field(
            "Observer",
            "Каждые 2 секунды записывает в БД, какое приложение активно",
            self._observer_check,
        ))

        # Действия
        actions = QHBoxLayout()
        actions.addStretch()
        save_btn = QPushButton(">_ Сохранить")
        save_btn.setObjectName("Primary")
        save_btn.setMinimumWidth(160)
        save_btn.clicked.connect(self._save)
        actions.addWidget(save_btn)

        layout.addSpacing(10)
        layout.addLayout(actions)
        layout.addStretch()

        scroll.setWidget(wrapper)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _start_mobile(self) -> None:
        """Запускает мобильный сервер и показывает QR-код с адресом."""
        import secrets
        from pathlib import Path

        from jarvis.core.config import settings
        from jarvis.server import embedded, security

        # 1) Надёжный токен (генерируем, если слабый/дефолтный) — secure-by-default
        if security.token_is_weak():
            new_token = secrets.token_urlsafe(24)
            settings.auth_token = new_token
            self._token_input.setText(new_token)
            try:
                self._update_env_file(Path.cwd() / ".env", {"AUTH_TOKEN": new_token})
            except Exception:  # noqa: BLE001
                pass
        token = settings.auth_token

        # 2) Правило брандмауэра (вход с телефона). Спросим — потребуются права админа.
        if sys.platform == "win32" and not embedded.firewall_rule_exists():
            ans = QMessageBox.question(
                self,
                "Брандмауэр",
                "Разрешить телефону подключаться к ПК через брандмауэр Windows?\n"
                "Появится запрос прав администратора (один раз).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                embedded.add_firewall_rule_elevated()

        # 3) Запуск сервера
        try:
            url = embedded.start()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить сервер:\n{e}")
            return
        # QR с токеном — вход на телефоне в один тап
        url = f"{url}?token={token}"
        serving = embedded.is_serving()

        dlg = QDialog(self)
        dlg.setWindowTitle("Сервер для телефона запущен")
        v = QVBoxLayout(dlg)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(12)

        # Статус: реально ли сервер отвечает
        status = QLabel(
            "✓ Сервер работает" if serving else "✗ Сервер НЕ отвечает (см. data\\jarvis.log)"
        )
        status.setStyleSheet(
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:13px;"
            + (f"color:{Colors.ACCENT};" if serving else f"color:{Colors.ERROR};")
        )
        v.addWidget(status, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Отсканируйте QR телефоном")
        title.setStyleSheet(
            f"font-family:'JetBrains Mono','Consolas',monospace;color:{Colors.ACCENT};"
            "font-size:16px;font-weight:700;"
        )
        v.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        qr = self._qr_pixmap(url)
        if qr is not None:
            img = QLabel()
            img.setPixmap(qr)
            img.setStyleSheet("background:white;padding:10px;border-radius:8px;")
            v.addWidget(img, alignment=Qt.AlignmentFlag.AlignCenter)

        link = QLabel(url)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        link.setStyleSheet(
            f"font-family:'JetBrains Mono','Consolas',monospace;color:{Colors.TEXT_PRIMARY};font-size:14px;"
        )
        v.addWidget(link, alignment=Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(
            "Телефон и ПК — в одной Wi-Fi сети. Токен уже зашит в QR — вход в один тап.\n"
            "Если не подключается: разреши порт в брандмауэре (кнопка выше → «Да») и "
            "проверь, что Wi-Fi сеть общая (не «гостевая»)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;")
        v.addWidget(hint)

        ok = QPushButton("Готово")
        ok.setObjectName("Primary")
        ok.clicked.connect(dlg.accept)
        v.addWidget(ok)
        dlg.exec()

    @staticmethod
    def _qr_pixmap(data: str) -> QPixmap | None:
        try:
            import qrcode

            img = qrcode.make(data)
            from io import BytesIO

            buf = BytesIO()
            img.save(buf, format="PNG")
            pm = QPixmap()
            pm.loadFromData(buf.getvalue())
            if not pm.isNull():
                return pm.scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        except Exception:  # noqa: BLE001
            pass
        return None

    def _save(self) -> None:
        env_file = Path.cwd() / ".env"
        try:
            new_values = {
                "LLM_PROVIDER": self._provider_combo.currentData(),
                "GLM_API_KEY": self._glm_key.text().strip(),
                "GLM_MODEL": self._glm_model.text().strip() or "glm-4-flash",
                "GLM_THINKING": "true" if self._thinking_check.isChecked() else "false",
                "GEMINI_API_KEY": self._gem_key.text().strip(),
                "GEMINI_MODEL": self._gem_model.text().strip() or "gemini-1.5-flash",
                "OLLAMA_HOST": self._ollama_host.text().strip() or "http://localhost:11434",
                "OLLAMA_MODEL": self._ollama_model.text().strip() or "qwen2.5:7b",
                "RAG_ENABLED": "true" if self._rag_check.isChecked() else "false",
                "MCP_ENABLED": "true" if self._mcp_check.isChecked() else "false",
                "TTS_ENABLED": "true" if self._tts_check.isChecked() else "false",
                "VOSK_MODEL_PATH": self._vosk_input.text().strip() or "./models/vosk-model-small-ru",
                "HOST": self._host_input.text().strip() or "0.0.0.0",
                "PORT": str(self._port_input.value()),
                "AUTH_TOKEN": self._token_input.text().strip(),
                "SAFE_ROOT": self._safe_root_input.text().strip(),
                "ENABLE_OBSERVER": "true" if self._observer_check.isChecked() else "false",
            }
            self._update_env_file(env_file, new_values)
            QMessageBox.information(
                self,
                "Сохранено",
                "Настройки записаны в .env\n\nПерезапустите Jarvis, чтобы изменения вступили в силу.",
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")

    @staticmethod
    def _update_env_file(path: Path, values: dict[str, str]) -> None:
        """Обновляет .env, сохраняя комментарии и неизменённые строки."""
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        keys_seen: set[str] = set()
        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                new_lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in values:
                new_lines.append(f"{key}={values[key]}")
                keys_seen.add(key)
            else:
                new_lines.append(line)

        missing = [k for k in values if k not in keys_seen]
        if missing:
            new_lines.append("")
            for key in missing:
                new_lines.append(f"{key}={values[key]}")

        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
