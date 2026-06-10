"""Иконка приложения: неон-зелёная «λ» на тёмном фоне (кибербез-стиль)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from jarvis.gui.theme import Colors


def make_icon(size: int = 64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # тёмный скруглённый фон с акцентной рамкой
    p.setBrush(QColor(Colors.BG_DARKEST))
    p.setPen(QPen(QColor(Colors.ACCENT_DARK), max(1.0, size * 0.03)))
    r = size * 0.14
    p.drawRoundedRect(QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92), r, r)

    # лямбда (Λ) — две линии, не зависят от шрифта
    pen = QPen(QColor(Colors.ACCENT), max(2.0, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    apex = QPointF(size * 0.52, size * 0.27)
    p.drawLine(QPointF(size * 0.26, size * 0.78), apex)          # левая нога
    p.drawLine(apex, QPointF(size * 0.76, size * 0.78))          # правая нога
    p.drawLine(QPointF(size * 0.40, size * 0.50), QPointF(size * 0.30, size * 0.34))  # хвостик λ
    p.end()
    return QIcon(pm)
