# -*- coding: utf-8 -*-
"""Planche de choix des icônes (outil de l'agent directeur-artistique).

Usage : python scripts/render_icons.py [sortie.png]
Rend chaque docs/identite/icone-*.svg aux tailles 16 → 256 px, sur fond sombre et sur fond clair,
et écrit aussi les PNG individuels dans docs/identite/png/.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "identite"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(svg: Path, size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    QSvgRenderer(str(svg)).render(p, QRectF(0, 0, size, size))
    p.end()
    return img


def main(out: Path):
    app = QGuiApplication(sys.argv)  # noqa: F841
    icons = sorted(SRC.glob("icone-*.svg"))
    (SRC / "png").mkdir(exist_ok=True)
    pad, label_w, gap = 24, 150, 18
    row_h = 256 + 2 * pad
    width = label_w + 2 * (sum(SIZES) + gap * len(SIZES) + pad) + pad
    sheet = QImage(width, row_h * len(icons) + 60, QImage.Format_ARGB32_Premultiplied)
    sheet.fill(QColor("#0B0D11"))
    p = QPainter(sheet)
    p.setRenderHint(QPainter.Antialiasing)
    f = QFont()
    f.setPixelSize(15)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#8B93A5"))
    p.drawText(QRectF(label_w, 14, 800, 30), Qt.AlignLeft | Qt.AlignVCenter,
               "Fond sombre (barre des tâches en mode sombre)")
    x_light = label_w + sum(SIZES) + gap * len(SIZES) + pad
    p.drawText(QRectF(x_light + pad, 14, 800, 30), Qt.AlignLeft | Qt.AlignVCenter, "Fond clair (explorateur Windows)")
    for r, svg in enumerate(icons):
        y0 = 60 + r * row_h
        p.setPen(QColor("#E7E9ED"))
        f.setPixelSize(28)
        p.setFont(f)
        p.drawText(QRectF(20, y0, label_w - 20, row_h), Qt.AlignLeft | Qt.AlignVCenter, svg.stem.split("-")[1])
        p.fillRect(QRectF(x_light, y0 + 6, width - x_light - pad, row_h - 12), QColor("#F2F3F5"))
        for base in (label_w, x_light + pad):
            x = base
            for s in SIZES:
                img = render(svg, s)
                p.drawImage(int(x), int(y0 + pad + (256 - s) / 2), img)
                x += s + gap
        for s in SIZES:
            render(svg, s).save(str(SRC / "png" / f"{svg.stem}-{s}.png"))
    p.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out))
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SRC / "planche.png")
