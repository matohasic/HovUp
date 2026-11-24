from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap, QPolygon
)


def create_app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, 64, 64)
    gradient.setColorAt(0, QColor("#4285F4"))
    gradient.setColorAt(1, QColor("#7138D8"))

    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)

    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(11, 12, 36, 30, 5, 5)

    painter.setBrush(QColor("#DCEBFF"))
    painter.drawRoundedRect(14, 15, 30, 24, 3, 3)

    painter.setBrush(QColor("#4285F4"))
    painter.drawPolygon(QPolygon([
        QPoint(14, 37),
        QPoint(24, 24),
        QPoint(31, 32),
        QPoint(37, 26),
        QPoint(44, 37)
    ]))

    painter.setBrush(QColor("#FFC857"))
    painter.drawEllipse(34, 18, 6, 6)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#FFFFFF"), 5))
    painter.drawEllipse(31, 30, 22, 22)

    painter.setPen(QPen(QColor("#FFFFFF"), 6))
    painter.drawLine(48, 48, 57, 57)

    painter.end()
    return QIcon(pixmap)
