"""Загрузка и валидация настроек из .env.

Использует pydantic-settings — типизированный аналог os.environ.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_safe_root() -> str:
    """По умолчанию — рабочий стол пользователя."""
    home = Path.home()
    desktop_ru = home / "OneDrive" / "Рабочий стол"
    desktop_en = home / "Desktop"
    if desktop_ru.exists():
        return str(desktop_ru)
    if desktop_en.exists():
        return str(desktop_en)
    return str(home)


class Settings(BaseSettings):
    """Типизированные настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM — выбор провайдера
    # Поддерживаются: "glm" (бесплатный API), "gemini", "ollama".
    # Ветка gpt-oss: по умолчанию локальная модель OpenAI gpt-oss:20b через Ollama.
    llm_provider: str = Field(default="ollama", description="Активный провайдер LLM")

    # --- GLM (Zhipu AI / z.ai), OpenAI-совместимый эндпоинт ---
    glm_api_key: str = Field(default="", description="API-ключ GLM (open.bigmodel.cn)")
    glm_model: str = Field(default="glm-4-flash", description="Бесплатная модель GLM")
    glm_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="Базовый URL OpenAI-совместимого API GLM",
    )
    glm_thinking: bool = Field(
        default=False, description="Глубокое мышление (reasoning) у GLM"
    )
    glm_thinking_model: str = Field(
        default="glm-4.5-flash",
        description="Reasoning-модель, используется при включённом мышлении",
    )

    # --- Gemini ---
    gemini_api_key: str = Field(default="", description="API-ключ Gemini")
    gemini_model: str = Field(default="gemini-1.5-flash")

    # --- Ollama (локальные модели) ---
    ollama_host: str = Field(default="http://localhost:11434")
    # Ветка gpt-oss: открытая модель OpenAI (Apache 2.0), локально через Ollama.
    ollama_model: str = Field(default="gpt-oss:20b")

    # --- RAG ---
    rag_enabled: bool = Field(default=True, description="Подмешивать знания из RAG")
    rag_top_k: int = Field(default=3, description="Сколько фрагментов знаний подмешивать")
    rag_db_path: str = Field(default="./data/rag_store.pkl")
    # Семантический поиск через эмбеддинги GLM (иначе TF-IDF, офлайн)
    rag_embeddings: bool = Field(default=False, description="Векторный поиск через эмбеддинги")
    embedding_model: str = Field(default="embedding-3", description="Модель эмбеддингов GLM")

    # --- Долговременная память (между сессиями) ---
    memory_enabled: bool = Field(default=True, description="Долговременная память")
    memory_db_path: str = Field(default="./data/memory_store.pkl")
    memory_top_k: int = Field(default=3, description="Сколько воспоминаний подмешивать")

    # --- История чатов (множественные диалоги) ---
    chats_db_path: str = Field(default="./data/chats.db", description="БД диалогов")

    # --- Автообновление ---
    update_check: bool = Field(default=True, description="Проверять обновления при старте")
    update_repo: str = Field(
        default="lastlofty/jarvis", description="GitHub-репозиторий для релизов owner/name"
    )

    # --- Плагины и MCP ---
    plugins_dir: str = Field(default="./plugins", description="Папка с плагинами/скиллами")
    mcp_config_path: str = Field(default="./mcp_servers.json", description="Конфиг MCP-серверов")
    mcp_enabled: bool = Field(default=False, description="Подключать внешние MCP-серверы")

    # --- Голос ---
    tts_enabled: bool = Field(default=False, description="Озвучивать ответы (TTS)")
    vosk_model_path: str = Field(
        default="./models/vosk-model-small-ru", description="Путь к модели Vosk (STT)"
    )

    # --- Трей / хоткей / wake-word ---
    global_hotkey: str = Field(default="ctrl+alt+j", description="Глобальный хоткей показать/скрыть")
    wake_word_enabled: bool = Field(default=False, description="Активация по слову 'джарвис'")
    wake_word: str = Field(default="джарвис", description="Слово активации")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    auth_token: str = Field(default="change_me_to_random_secret")

    # Safety
    safe_root: str = Field(default_factory=_default_safe_root)
    require_confirm_delete: bool = Field(default=True)

    # DB
    db_path: str = Field(default="./data/jarvis.db")

    # Observer
    observer_interval: float = Field(default=2.0)
    enable_observer: bool = Field(default=True)

    # Logs
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./data/jarvis.log")

    @field_validator("safe_root")
    @classmethod
    def _safe_root_fallback(cls, v: str) -> str:
        """Пустой SAFE_ROOT (в т.ч. `SAFE_ROOT=` в .env) -> рабочий стол."""
        return v if v and v.strip() else _default_safe_root()

    def ensure_dirs(self) -> None:
        """Создаёт директории для БД и логов, если их нет."""
        for path_str in (self.db_path, self.log_file):
            p = Path(path_str).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)


# Singleton — импортируется во всём проекте
settings = Settings()
settings.ensure_dirs()
