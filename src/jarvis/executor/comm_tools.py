"""Отчёты и коммуникационные инструменты (ask_user, уведомления)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from tabulate import tabulate

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult
from jarvis.memory.db import db


# ---------- App-usage reports ----------


def _parse_date(s: str | None, default: datetime) -> datetime:
    if not s:
        return default
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Неверный формат даты: {s}")


def collect_app_usage(
    start_date: str | None = None, end_date: str | None = None
) -> ToolResult:
    """Возвращает агрегированную статистику. По умолчанию — за последние 24 часа."""
    try:
        end = _parse_date(end_date, datetime.utcnow())
        start = _parse_date(start_date, end - timedelta(days=1))
        if start >= end:
            return ToolResult.fail("start_date должна быть раньше end_date")
        rows = db.query_app_usage(start, end)
        for r in rows:
            r["minutes"] = round((r.get("total_s") or 0) / 60.0, 1)
        return ToolResult.ok(
            f"Найдено записей: {len(rows)} ({start} — {end})",
            {"start": start.isoformat(), "end": end.isoformat(), "items": rows},
        )
    except Exception as e:
        logger.exception("collect_app_usage")
        return ToolResult.fail(f"Ошибка: {e}")


def generate_report(
    data: list[dict[str, Any]] | None = None, format: str = "text"
) -> ToolResult:
    """Создаёт отчёт. Если data не передано — берёт стат. за последние сутки.
    format: 'text' | 'csv' | 'pdf'.
    """
    try:
        if data is None:
            usage = collect_app_usage()
            if usage.status == "error" or usage.data is None:
                return usage
            data = usage.data["items"]

        if not data:
            return ToolResult.ok("Нет данных за период.", {"format": format})

        rows = [
            [r.get("app_name", ""), r.get("minutes", 0), r.get("sessions", 0)]
            for r in data
        ]
        headers = ["Приложение", "Минуты", "Сессий"]

        if format == "text":
            text = tabulate(rows, headers=headers, tablefmt="github")
            return ToolResult.ok("Отчёт:\n" + text, {"format": "text", "report": text})

        if format == "csv":
            import csv
            import io

            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(headers)
            w.writerows(rows)
            csv_text = buf.getvalue()
            out_path = Path(gettempdir()) / "jarvis_report.csv"
            out_path.write_text(csv_text, encoding="utf-8")
            return ToolResult.ok(
                f"CSV-отчёт сохранён: {out_path}",
                {"format": "csv", "path": str(out_path)},
            )

        if format == "pdf":
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

            out_path = Path(gettempdir()) / "jarvis_report.pdf"
            doc = SimpleDocTemplate(str(out_path), pagesize=A4)
            tbl = Table([headers, *rows])
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ]
                )
            )
            doc.build([tbl])
            return ToolResult.ok(
                f"PDF-отчёт сохранён: {out_path}",
                {"format": "pdf", "path": str(out_path)},
            )

        return ToolResult.fail(f"Неизвестный формат: {format}")
    except Exception as e:
        logger.exception("generate_report")
        return ToolResult.fail(f"Ошибка отчёта: {e}")


# ---------- Communication ----------


class CommunicationBridge:
    """Мост между LLM-инструментом ask_user и активным WebSocket клиентом.

    LLM вызывает ask_user(), функция кладёт вопрос в очередь и ждёт ответа.
    Сервер отправляет вопрос мобильному приложению и при получении ответа
    разрешает Future.
    """

    def __init__(self) -> None:
        self._pending: dict[int, asyncio.Future[str]] = {}
        self._next_id = 1
        self._send_callback = None  # type: ignore

    def set_send_callback(self, fn) -> None:
        """Устанавливает функцию отправки в WebSocket (вызывается сервером)."""
        self._send_callback = fn

    async def ask(self, question: str, timeout: float = 300.0) -> str:
        if self._send_callback is None:
            # Нет подключённого клиента — fallback в консоль
            logger.warning("Нет WebSocket-клиента, fallback в консоль")
            return await asyncio.to_thread(input, f"[Jarvis спрашивает] {question}\n> ")

        loop = asyncio.get_event_loop()
        qid = self._next_id
        self._next_id += 1
        fut: asyncio.Future[str] = loop.create_future()
        self._pending[qid] = fut

        await self._send_callback(
            {"type": "question", "id": qid, "question": question}
        )

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return ""
        finally:
            self._pending.pop(qid, None)

    def resolve(self, qid: int, answer: str) -> None:
        fut = self._pending.get(qid)
        if fut and not fut.done():
            fut.set_result(answer)


bridge = CommunicationBridge()


async def ask_user(question: str) -> ToolResult:
    """Спросить пользователя через мобильное приложение."""
    try:
        answer = await bridge.ask(question)
        if not answer:
            return ToolResult.fail("Пользователь не ответил (тайм-аут)")
        return ToolResult.ok(f"Ответ: {answer}", {"answer": answer})
    except Exception as e:
        logger.exception("ask_user")
        return ToolResult.fail(f"Ошибка ask_user: {e}")


async def send_notification(title: str, message: str) -> ToolResult:
    """Отправить уведомление на мобильное приложение."""
    try:
        if bridge._send_callback is None:
            logger.info(f"[notif] {title}: {message}")
            return ToolResult.ok("Уведомление в логе (нет подключения)")
        await bridge._send_callback(
            {"type": "notification", "title": title, "message": message}
        )
        return ToolResult.ok("Уведомление отправлено")
    except Exception as e:
        logger.exception("send_notification")
        return ToolResult.fail(f"Ошибка уведомления: {e}")
