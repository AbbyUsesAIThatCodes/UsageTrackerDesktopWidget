"""Resolution-independent botanical artwork, drawn with native Qt paths."""
from dataclasses import dataclass
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont, QPixmap, QIcon
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class Theme:
    background: str
    paper: str
    ink: str
    muted: str
    accent: str
    soft: str
    leaf: str
    petal: str
    gold: str
    border: str


THEMES = {
    "Rosewater": Theme("#f6f0ea", "#fffcf8", "#392e39", "#76636c", "#a3426c", "#ecd6df", "#657c58", "#d883a3", "#b18026", "#e4d7d5"),
    "Marigold": Theme("#f8f2e3", "#fffcf4", "#433726", "#746345", "#98521b", "#f4dfb4", "#6c7846", "#eca634", "#815226", "#e4d8bb"),
    "Lavender": Theme("#f0edf6", "#fcfaff", "#38304b", "#6f6481", "#7254a5", "#e1d8f0", "#678474", "#b59ad8", "#b18c4b", "#ddd4e8"),
    "Sage": Theme("#edf2e9", "#fcfdf7", "#2d4234", "#5f7362", "#3c7153", "#d5e5d6", "#678756", "#d6a46c", "#947127", "#d1dfd0"),
    "Forget-me-not": Theme("#ebf2f6", "#fafdff", "#2d3d50", "#5c7084", "#356b98", "#d4e5f1", "#618775", "#87b6df", "#bb9141", "#d1dfe8"),
    "Moonflower": Theme("#202b33", "#2b3742", "#f7e9e0", "#c0b9bf", "#f0bad3", "#45505e", "#9aae96", "#cbaad9", "#e6c785", "#49535e"),
}
FLOWERS = ("Cosmos", "Daisy", "Poppy", "Tulip", "Lavender")
PATTERNS = ("Meadow", "Pressed flowers", "Polka dots", "Trellis", "Plain")


def flower(painter, x, y, size, species, theme, angle=0):
    painter.save()
    painter.translate(x, y)
    painter.rotate(angle)
    painter.scale(size / 50, size / 50)
    painter.setPen(QPen(QColor(theme.leaf), 2.1))
    stem = QPainterPath(QPointF(0, 5))
    stem.cubicTo(8, 26, -8, 55, 3, 78)
    painter.drawPath(stem)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(theme.leaf))
    for side, height in ((-1, 35), (1, 51)):
        leaf = QPainterPath(QPointF(1, height + 9))
        leaf.cubicTo(18 * side, height + 6, 27 * side, height - 8, 24 * side, height - 12)
        leaf.cubicTo(7 * side, height - 15, 2 * side, height, 1, height + 9)
        painter.drawPath(leaf)
    if species == "Lavender":
        for row in range(6):
            for side in (-1, 1):
                painter.setBrush(QColor(theme.petal if row % 2 else theme.accent))
                painter.drawEllipse(QRectF(side * (6 - row * .6) - 4, -29 + row * 6, 8, 10))
    elif species == "Tulip":
        painter.setBrush(QColor(theme.petal))
        path = QPainterPath(QPointF(-22, -24))
        path.lineTo(-8, -14); path.lineTo(0, -31); path.lineTo(8, -14); path.lineTo(22, -24)
        path.cubicTo(25, 15, -25, 15, -22, -24)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(theme.accent), 1))
        painter.drawLine(QPointF(0, -14), QPointF(0, 5))
    else:
        count = {"Cosmos": 8, "Daisy": 12, "Poppy": 5}[species]
        for petal in range(count):
            painter.save(); painter.rotate(petal * 360 / count)
            color = theme.paper if species == "Daisy" else (theme.petal if petal % 2 else theme.accent)
            painter.setBrush(QColor(color)); painter.setPen(QPen(QColor(theme.petal), .7))
            width = 13 if species == "Daisy" else 22 if species == "Cosmos" else 31
            painter.drawEllipse(QRectF(-width / 2, -31, width, 30))
            painter.restore()
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(theme.gold))
        painter.drawEllipse(QRectF(-7, -7, 14, 14))
        painter.setBrush(QColor(theme.ink))
        for dot in range(7):
            angle = dot * math.tau / 7
            painter.drawEllipse(QPointF(math.cos(angle) * 4, math.sin(angle) * 4), .7, .7)
    painter.restore()


class GardenHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEMES["Rosewater"]
        self.species = "Cosmos"
        self.pattern = "Meadow"
        self.setMinimumHeight(126)
        self.setAccessibleName("Usage Garden botanical banner")

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme; width = self.width()
        p.fillRect(self.rect(), QColor(t.background))
        if self.pattern == "Polka dots":
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(t.border))
            for x in range(10, width, 19):
                for y in range(8, self.height(), 19):
                    p.drawEllipse(QPointF(x, y), 1.3, 1.3)
        elif self.pattern == "Trellis":
            p.setPen(QPen(QColor(t.border), 1))
            for x in range(-150, width + 150, 26):
                p.drawLine(x, 0, x + 150, 150); p.drawLine(x, 0, x - 150, 150)
        elif self.pattern == "Pressed flowers":
            p.setOpacity(.16)
            for x in range(10, width, 75):
                flower(p, x, 10, 20, self.species, t, 40)
            p.setOpacity(1)
        elif self.pattern == "Meadow":
            p.setOpacity(.32)
            p.setPen(QPen(QColor(t.leaf), 1.1))
            for x in range(8, width, 17):
                height = 5 + (x % 13)
                p.drawLine(QPointF(x, self.height()), QPointF(x - 4, self.height() - height))
                p.drawLine(QPointF(x, self.height()), QPointF(x + 5, self.height() - height + 4))
            p.setOpacity(1)
        # Typography has a quiet, opaque area even with patterned paper.
        p.fillRect(QRectF(15, 20, 242, 96), QColor(t.background))
        p.setPen(QColor(t.accent)); p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.drawText(QPointF(23, 39), "A LITTLE ROOM TO BLOOM")
        p.setPen(QColor(t.ink)); p.setFont(QFont("Georgia", 25))
        p.drawText(QPointF(21, 78), "Usage Garden")
        p.setPen(QColor(t.muted)); p.setFont(QFont("Segoe UI", 9))
        p.drawText(QPointF(24, 102), "Your allowances, gently explained.")
        for x, y, size, angle in ((width - 25, 41, 44, 18), (width - 64, 78, 32, -18), (width - 91, 27, 24, -20)):
            flower(p, x, y, size, self.species, t, angle)
        p.end()


def app_icon(theme=None, species="Cosmos"):
    t = theme or THEMES["Rosewater"]
    pixmap = QPixmap(128, 128); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(t.background))
    painter.drawRoundedRect(QRectF(3, 3, 122, 122), 28, 28)
    flower(painter, 64, 45, 54, species, t, -12)
    painter.end()
    return QIcon(pixmap)
