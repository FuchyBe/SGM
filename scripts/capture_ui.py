# -*- coding: utf-8 -*-
"""Capture d'écran de SGM avec des scènes de démonstration (sans toucher au vrai simulateur).

Usage : python scripts/capture_ui.py [langue] [sortie.png] [largeur] [hauteur]
  ex.   python scripts/capture_ui.py fr docs/captures/fr.png 1280 760
Sert à l'agent designer-interface pour vérifier l'interface (textes coupés, alignements, arabe RTL…).
Tout se passe dans un dossier temporaire : données SGM, APPDATA et scènes factices.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
out = Path(sys.argv[2] if len(sys.argv) > 2 else f"capture_{lang}.png").resolve()
width = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
height = int(sys.argv[4]) if len(sys.argv) > 4 else 760

tmp = Path(tempfile.mkdtemp(prefix="sgm_capture_"))
os.environ["APPDATA"] = str(tmp / "roaming")
os.environ["LOCALAPPDATA"] = str(tmp / "local")
os.environ["HOME"] = os.environ["USERPROFILE"] = str(tmp / "home")
(tmp / "home" / "Downloads").mkdir(parents=True)

import statics_manager as m  # noqa: E402

m._DATA_DIR = tmp / "SGM_data"
m._DATA_DIR.mkdir(parents=True)
lib = tmp / "Library"
INI = b"[general]\n[section.1]\npushback=1\n"


def pkg(folder, title, creator, files):
    root = lib / folder
    content = []
    for rel, data, in_layout in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        if in_layout:
            content.append({"path": rel, "size": len(data), "date": 0})
    (root / "layout.json").write_text(json.dumps({"content": content}))
    (root / "manifest.json").write_text(json.dumps({"title": title, "creator": creator, "content_type": "SCENERY",
                                                    "package_version": "1.0.0",
                                                    "total_package_size": str(sum(c["size"] for c in content)).zfill(20)}))


pkg("demo-ebbr-brussels", "Brussels Airport EBBR", "Demo Studio", [("scenery/EBBR_statics.bgl", b"S" * 9, True)])
pkg("demo-lfpg-paris", "Paris Charles de Gaulle LFPG", "Demo Works", [
    ("scenery/statics_on.bgl", b"N" * 9, False), ("scenery/statics_off.bgl", b"F" * 9, False),
    ("scenery/statics.bgl", b"F" * 9, True),
    ("GSX/LFPG FULL/lfpg-demo.ini", INI + b"full", False), ("GSX/LFPG LITE/lfpg-demo.ini", INI + b"lite", False)])
pkg("demo-ebci-charleroi", "Charleroi Brussels South EBCI", "Demo Sim", [
    ("scenery/statics_on.bgl", b"N" * 9, False), ("scenery/statics_off.bgl", b"F" * 9, False),
    ("scenery/EBCI_statics_vehicles.bgl", b"V" * 9, True)])
pkg("demo-egll-heathrow", "London Heathrow EGLL", "Demo Works", [
    ("scenery/EGLL_statics.bgl.off", b"S" * 9, False), ("GSX Profile/egll-demo.ini", INI, False)])
pkg("demo-kdfw-dallas", "Dallas Fort Worth KDFW", "Demo Builds", [
    ("Scenery/kdfw-scene/kdfw-scene-statics.off", b"S" * 9, False), ("Scenery/kdfw-scene/kdfw-scene-airport.bgl", b"A" * 99, True)])
pkg("demo-lyni-nis", "Nis Constantine LYNI", "Demo Studio", [
    ("scenery/world/scenery/lyni_place.bgl", b"P" * 20, True), ("scenery/world/scenery/lyni_place.bgl.nostatic", b"N" * 15, False)])
pkg("demo-eham-schiphol", "Amsterdam Schiphol EHAM", "Demo Studio", [("scenery/EHAM.bgl", b"A" * 9, True)])

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setStyleSheet(m.QSS)
f = QFont()
f.setFamilies(["Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"])
f.setPointSizeF(9.5)
app.setFont(f)
cfg = m.Config()
cfg.lang = lang
cfg.manual_folders.append(str(lib))
cfg.save()
m.set_lang(lang)
w = m.MainWindow()
w.resize(width, height)
w.show()


def shoot():
    app.processEvents()
    out.parent.mkdir(parents=True, exist_ok=True)
    w.grab().save(str(out))
    print(out)
    app.quit()


QTimer.singleShot(1500, shoot)
app.exec()
