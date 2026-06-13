"""Тесты ядра агента: RAG-стор, конвертация инструментов, цикл оркестратора."""
from __future__ import annotations

import pytest


# ---------- RAG ----------


def test_rag_index_and_search(tmp_path):
    from jarvis.rag.store import RAGStore

    store = RAGStore(persist_path=str(tmp_path / "rag.pkl"))
    store.add_text(
        "Jarvis поддерживает модели GLM, Gemini и Ollama. GLM основная.",
        source="kb1",
    )
    store.add_text("Рецепт борща: свёкла, капуста, картофель.", source="kb2")

    hits = store.search("какие модели у jarvis", k=2)
    assert hits, "поиск должен что-то находить"
    assert hits[0].source == "kb1", "самый релевантный — про модели"
    assert hits[0].score > 0


def test_rag_reindex_replaces_source(tmp_path):
    from jarvis.rag.store import RAGStore

    store = RAGStore(persist_path=str(tmp_path / "rag.pkl"))
    store.add_text("первая версия текста про альфа", source="doc")
    store.add_text("вторая версия текста про бета", source="doc")
    # источник один — старые чанки должны быть вытеснены
    assert store.stats()["sources"] == 1
    hits = store.search("бета", k=3)
    assert any("бета" in h.text for h in hits)
    assert all("альфа" not in h.text for h in hits)


def test_rag_persistence(tmp_path):
    from jarvis.rag.store import RAGStore

    path = str(tmp_path / "rag.pkl")
    store = RAGStore(persist_path=path)
    store.add_text("сохрани меня между запусками", source="persist")
    # новый экземпляр читает с диска
    store2 = RAGStore(persist_path=path)
    assert store2.stats()["chunks"] >= 1
    assert store2.search("сохрани", k=1)


# ---------- Конвертация инструментов ----------


def test_to_openai_tools_shape():
    from jarvis.llm.providers.base import LLMProvider

    decls = [
        {
            "name": "demo",
            "description": "тест",
            "parameters": {"type": "object", "properties": {"x": {"type": "string"}}},
        }
    ]
    tools = LLMProvider.to_openai_tools(decls)
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "demo"
    assert "parameters" in tools[0]["function"]


# ---------- Реестр: динамическая регистрация ----------


def test_register_tool_appears_in_declarations():
    from jarvis.core.types import ToolResult
    from jarvis.executor import registry

    def handler(value: str) -> ToolResult:
        return ToolResult.ok(f"echo {value}")

    decl = {
        "name": "echo_test",
        "description": "echo",
        "parameters": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
    }
    registry.register_tool(decl, handler)
    names = [d["name"] for d in registry.all_declarations()]
    assert "echo_test" in names


@pytest.mark.asyncio
async def test_dispatch_extra_handler():
    from jarvis.core.types import ToolResult
    from jarvis.executor import registry

    def handler(value: str) -> ToolResult:
        return ToolResult.ok(f"echo {value}")

    registry.register_tool(
        {
            "name": "echo2",
            "description": "echo",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        },
        handler,
    )
    result = await registry.dispatch("echo2", {"value": "hi"})
    assert result.status == "success"
    assert "hi" in result.message


# ---------- Оркестратор: цикл инструментов ----------


@pytest.mark.asyncio
async def test_orchestrator_tool_loop():
    from jarvis.llm.orchestrator import Orchestrator
    from jarvis.llm.providers.base import LLMProvider, LLMResponse, ToolCall

    class FakeProvider(LLMProvider):
        display_name = "Fake"

        def __init__(self) -> None:
            self.step = 0

        async def generate(self, messages, tools):
            self.step += 1
            if self.step == 1:
                return LLMResponse(
                    tool_calls=[ToolCall(id="c1", name="get_active_window", arguments={})]
                )
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            return LLMResponse(text=f"done:{len(tool_msgs)}")

    orch = Orchestrator(provider=FakeProvider())
    ans = await orch.handle("что в активном окне?")
    assert ans == "done:1"
    roles = [m["role"] for m in orch.history]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]


@pytest.mark.asyncio
async def test_orchestrator_trims_history():
    from jarvis.llm import orchestrator as orch_mod
    from jarvis.llm.orchestrator import Orchestrator
    from jarvis.llm.providers.base import LLMProvider, LLMResponse

    class PlainProvider(LLMProvider):
        display_name = "Plain"

        async def generate(self, messages, tools):
            return LLMResponse(text="ok")

    orch = Orchestrator(provider=PlainProvider())
    # забиваем историю сверх лимита
    for i in range(orch_mod.MAX_HISTORY_MESSAGES + 20):
        await orch.handle(f"сообщение {i}")

    # system всегда первый, история ограничена, хвост валиден
    assert orch.history[0]["role"] == "system"
    assert len(orch.history) <= orch_mod.MAX_HISTORY_MESSAGES + 3
    assert orch.history[1]["role"] in ("user", "assistant")


@pytest.mark.asyncio
async def test_orchestrator_plain_answer_no_tools():
    from jarvis.llm.orchestrator import Orchestrator
    from jarvis.llm.providers.base import LLMProvider, LLMResponse

    class PlainProvider(LLMProvider):
        display_name = "Plain"

        async def generate(self, messages, tools):
            return LLMResponse(text="привет")

    orch = Orchestrator(provider=PlainProvider())
    ans = await orch.handle("привет")
    assert ans == "привет"


def test_long_term_memory_remember_recall(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "mem.pkl"))
    # пересоздаём модуль, чтобы singleton подхватил путь
    import importlib

    import jarvis.memory.long_term as lt
    importlib.reload(lt)

    lt.long_term.remember("Пользователя зовут Богдан")
    lt.long_term.remember("Любит киберпанк и тёмную тему")
    hits = lt.long_term.recall("как зовут пользователя")
    assert any("Богдан" in h.text for h in hits)
    assert lt.long_term.count() == 2


def test_conversation_store(tmp_path):
    from jarvis.memory.conversations import ConversationStore

    store = ConversationStore(db_path=str(tmp_path / "chats.db"))
    cid = store.create("Тестовый чат")
    store.add_message(cid, "user", "привет")
    store.add_message(cid, "assistant", "здравствуй")

    convs = store.list()
    assert len(convs) == 1 and convs[0].title == "Тестовый чат"
    msgs = store.messages(cid)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[1].content == "здравствуй"

    store.rename(cid, "Новое имя")
    assert store.list()[0].title == "Новое имя"
    store.delete(cid)
    assert store.list() == []


def test_plan_tools_flow():
    from jarvis.executor import plan_tools

    plan_tools.reset_plan()
    r = plan_tools.create_plan(["шаг один", "шаг два"])
    assert r.status == "success"
    assert "1/2" not in r.message  # пока ничего не выполнено
    plan_tools.complete_step(1)
    done = plan_tools.get_plan()
    assert "[x] 1" in done.message
    assert "(1/2)" in done.message
    bad = plan_tools.complete_step(99)
    assert bad.status == "error"


def test_mobile_webapp_present():
    from pathlib import Path

    import jarvis.server.api as api

    webdir = Path(api.__file__).parent / "webapp"
    assert (webdir / "index.html").exists()
    assert (webdir / "manifest.webmanifest").exists()
    assert (webdir / "sw.js").exists()
    html = (webdir / "index.html").read_text(encoding="utf-8")
    assert "jarvis" in html.lower() and "websocket" in html.lower()


def test_embedded_url_format():
    from jarvis.server import embedded

    url = embedded.url()
    assert url.startswith("http://") and url.endswith("/app/")


def test_security_token_and_bruteforce(monkeypatch):
    from jarvis.core.config import settings
    from jarvis.server import security

    # слабый/короткий токен блокирует всех
    monkeypatch.setattr(settings, "auth_token", "short")
    assert security.token_is_weak()
    assert not security.check_token("short")

    # надёжный токен — constant-time сравнение
    strong = "X" * 24
    monkeypatch.setattr(settings, "auth_token", strong)
    assert not security.token_is_weak()
    assert security.check_token(strong)
    assert not security.check_token("wrong")
    assert not security.check_token(None)

    # анти-брутфорс: блокировка после серии неудач
    ip = "10.0.0.9"
    assert security.lock_remaining(ip) == 0
    for _ in range(5):
        security.record_fail(ip)
    assert security.lock_remaining(ip) > 0
    security.record_success(ip)
    assert security.lock_remaining(ip) == 0


def _load_plugin(name):
    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "plugins" / name / "skill.py"
    spec = importlib.util.spec_from_file_location(f"plugin_{name}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_invoice_processor(tmp_path, monkeypatch):
    from jarvis.core.config import settings

    monkeypatch.setattr(settings, "safe_root", str(tmp_path))
    inv = _load_plugin("invoice_processor")
    assert inv.record_invoice("A1", "Acme", "2026-01-01", 100, "RUB").status == "success"
    assert inv.record_invoice("A2", "Acme", "2026-01-02", 50, "RUB").status == "success"
    # дубль номера+поставщика -> ошибка
    assert inv.record_invoice("A1", "Acme", "2026-01-01", 100, "RUB").status == "error"
    summ = inv.financial_summary()
    assert "Acme" in summ.message and "150" in summ.message


def test_call_analyzer_crm(tmp_path, monkeypatch):
    from jarvis.core.config import settings

    monkeypatch.setattr(settings, "safe_root", str(tmp_path))
    crm = _load_plugin("call_analyzer")
    r = crm.save_crm_record("Альфа", "Саммари звонка", "Прислать КП", "в работе")
    assert r.status == "success"
    lst = crm.list_crm_records()
    assert "Альфа" in lst.message


def test_ollama_tool_args_to_object():
    from jarvis.llm.providers.ollama_provider import OllamaProvider

    msgs = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "x", "type": "function",
                 "function": {"name": "get_weather", "arguments": '{"city": "Москва"}'}}
            ],
        }
    ]
    out = OllamaProvider._to_ollama_messages(msgs)
    fn = out[0]["tool_calls"][0]["function"]
    assert fn["arguments"] == {"city": "Москва"}  # строка -> объект (формат Ollama)
    assert "id" not in out[0]["tool_calls"][0]


def test_open_app_unknown_fails_honestly():
    from jarvis.executor.app_tools import open_app

    res = open_app("несуществующее_приложение_zzz_999")
    assert res.status == "error"
    assert "найти" in res.message.lower() or "открыть" in res.message.lower()


def test_run_script_blocked_outside_safe_root(tmp_path, monkeypatch):
    from jarvis.core.config import settings
    from jarvis.executor.app_tools import run_script

    monkeypatch.setattr(settings, "safe_root", str(tmp_path))
    # путь вне SAFE_ROOT -> запрещено
    res = run_script("C:/Windows/System32/calc.exe")
    assert res.status == "error"
    assert "безопасн" in res.message.lower()


def test_updater_version_compare():
    from jarvis.core.updater import is_newer

    assert is_newer("v1.2.0", "1.1.9")
    assert is_newer("0.3.0", "0.2.9")
    assert not is_newer("0.2.0", "0.2.0")
    assert not is_newer("0.1.5", "0.2.0")


def test_markdown_render():
    from jarvis.gui.markdown_render import markdown_to_html

    html = markdown_to_html("## Заголовок\n- пункт\n\n`код`\n\n```\nx=1\n```")
    assert "Заголовок" in html
    assert "<ul" in html and "<li>" in html
    assert "<code" in html
    assert "<pre" in html


@pytest.mark.asyncio
async def test_orchestrator_stream_emits_chunks():
    from jarvis.llm.orchestrator import Orchestrator
    from jarvis.llm.providers.base import LLMProvider, LLMResponse

    class PlainProvider(LLMProvider):
        display_name = "Plain"

        async def generate(self, messages, tools):
            return LLMResponse(text="привет мир")

    orch = Orchestrator(provider=PlainProvider())
    chunks: list[str] = []
    ans = await orch.handle_stream("привет", lambda c: chunks.append(c))
    # дефолтный stream() оборачивает generate -> один чанк с полным текстом
    assert ans == "привет мир"
    assert "".join(chunks) == "привет мир"
