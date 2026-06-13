"""Скилл обработки счетов: учёт, сверка, финансовая отчётность.

Агент читает счёт (read_invoice), извлекает поля и сохраняет их (record_invoice)
в локальный реестр <SAFE_ROOT>/finance/invoices.csv. Затем умеет сверять данные
(reconcile_invoices) и готовить сводку (financial_summary).
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.docs import read_document
from jarvis.core.types import ToolResult

_FIELDS = ["number", "vendor", "date", "amount", "currency", "recorded_at"]


def _ledger() -> Path:
    p = Path(settings.safe_root) / "finance"
    p.mkdir(parents=True, exist_ok=True)
    return p / "invoices.csv"


def _rows() -> list[dict]:
    f = _ledger()
    if not f.exists():
        return []
    with open(f, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_invoice(path: str) -> ToolResult:
    """Читает счёт (txt/pdf) для извлечения номера, поставщика, даты, суммы."""
    text, err = read_document(path)
    if err:
        return ToolResult.fail(err)
    return ToolResult.ok(text[:6000], {"length": len(text)})


def record_invoice(
    number: str, vendor: str, date: str, amount: float, currency: str = "RUB"
) -> ToolResult:
    """Сохраняет данные счёта в реестр."""
    try:
        amount_f = float(str(amount).replace(",", ".").replace(" ", ""))
    except ValueError:
        return ToolResult.fail(f"Неверная сумма: {amount}")

    rows = _rows()
    if any(r["number"] == str(number) and r["vendor"] == vendor for r in rows):
        return ToolResult.fail(
            f"Счёт {number} от «{vendor}» уже есть в реестре (возможный дубль)."
        )

    f = _ledger()
    new = not f.exists()
    with open(f, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "number": number, "vendor": vendor, "date": date,
            "amount": amount_f, "currency": currency,
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        })
    return ToolResult.ok(
        f"Счёт {number} от «{vendor}» на {amount_f} {currency} записан.",
        {"file": str(f)},
    )


def reconcile_invoices() -> ToolResult:
    """Сверка реестра: дубли, пустые/некорректные суммы."""
    rows = _rows()
    if not rows:
        return ToolResult.ok("Реестр счетов пуст.")
    seen: dict[tuple, int] = defaultdict(int)
    bad: list[str] = []
    for r in rows:
        seen[(r["number"], r["vendor"])] += 1
        try:
            if float(r["amount"]) <= 0:
                bad.append(f"{r['number']}: сумма {r['amount']}")
        except ValueError:
            bad.append(f"{r['number']}: некорректная сумма '{r['amount']}'")
    dups = [f"{n} ({v})" for (n, v), c in seen.items() if c > 1]
    parts = [f"Всего записей: {len(rows)}"]
    parts.append("Дубликаты: " + (", ".join(dups) if dups else "нет"))
    parts.append("Проблемные суммы: " + (", ".join(bad) if bad else "нет"))
    return ToolResult.ok("\n".join(parts), {"duplicates": dups, "issues": bad})


def financial_summary() -> ToolResult:
    """Финансовая сводка: итоги по поставщикам и общая сумма."""
    rows = _rows()
    if not rows:
        return ToolResult.ok("Реестр счетов пуст.")
    by_vendor: dict[str, float] = defaultdict(float)
    by_cur: dict[str, float] = defaultdict(float)
    for r in rows:
        try:
            amt = float(r["amount"])
        except ValueError:
            continue
        by_vendor[r["vendor"]] += amt
        by_cur[r.get("currency", "RUB")] += amt
    lines = ["Сводка по поставщикам:"]
    for v, s in sorted(by_vendor.items(), key=lambda x: -x[1]):
        lines.append(f"  {v}: {round(s, 2)}")
    lines.append("Итого по валютам:")
    for c, s in by_cur.items():
        lines.append(f"  {c}: {round(s, 2)}")
    return ToolResult.ok("\n".join(lines), {"by_vendor": dict(by_vendor), "by_currency": dict(by_cur)})


DECLARATIONS = [
    {
        "name": "read_invoice",
        "description": "Прочитать счёт (txt/pdf), чтобы извлечь номер, поставщика, дату и сумму.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Путь к файлу счёта"}},
            "required": ["path"],
        },
    },
    {
        "name": "record_invoice",
        "description": "Записать данные счёта в реестр после извлечения полей.",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {"type": "string", "description": "Номер счёта"},
                "vendor": {"type": "string", "description": "Поставщик/контрагент"},
                "date": {"type": "string", "description": "Дата счёта (YYYY-MM-DD)"},
                "amount": {"type": "number", "description": "Сумма"},
                "currency": {"type": "string", "description": "Валюта (RUB/USD/EUR)"},
            },
            "required": ["number", "vendor", "amount"],
        },
    },
    {
        "name": "reconcile_invoices",
        "description": "Сверить реестр счетов: найти дубликаты и некорректные суммы.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "financial_summary",
        "description": "Подготовить финансовую сводку: итоги по поставщикам и валютам.",
        "parameters": {"type": "object", "properties": {}},
    },
]

HANDLERS = {
    "read_invoice": read_invoice,
    "record_invoice": record_invoice,
    "reconcile_invoices": reconcile_invoices,
    "financial_summary": financial_summary,
}
