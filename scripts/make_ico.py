"""Fabrique assets/SGM.ico (16 → 256 px) et assets/SGM-256.png à partir de paint_logo() de l'application.

Usage : python scripts/make_ico.py   (à relancer seulement si l'icône change ; le fichier .ico est versionné)
"""
import io, os, struct, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication
import statics_manager as sm

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def png_bytes(img) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def main():
    app = QApplication.instance() or QApplication([])
    out = os.path.join(ROOT, "assets")
    os.makedirs(out, exist_ok=True)
    pngs = [(n, png_bytes(sm.logo_image(n))) for n in ICO_SIZES]
    head = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for n, png in pngs:
        d = 0 if n >= 256 else n
        entries += struct.pack("<BBBBHHII", d, d, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    with open(os.path.join(out, "SGM.ico"), "wb") as f:
        f.write(head + entries + data)
    sm.logo_image(256).save(os.path.join(out, "SGM-256.png"))
    sm.logo_image(512).save(os.path.join(out, "SGM-512.png"))
    print("assets/SGM.ico, assets/SGM-256.png, assets/SGM-512.png")


if __name__ == "__main__":
    main()
