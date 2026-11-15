# -*- coding: utf-8 -*-
"""Captures « vitrine » de SGM pour la page flightsim.to (scènes de démonstration, rien de réel).

Usage : python scripts/capture_flightsim.py [dossier_sortie] [langue]
Produit, en haute définition (échelle 2) :
  main.png      fenêtre principale, scènes variées (ON / OFF / à vérifier / profils GSX)
  narrow.png    fenêtre étroite (mode compact)
  guide.png     guide intégré
  report.png    fenêtre « Signaler un problème »
Les éditeurs des scènes sont inventés ; aucune marque de tiers.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "captures_flightsim").resolve()
lang = sys.argv[2] if len(sys.argv) > 2 else "en"
out_dir.mkdir(parents=True, exist_ok=True)

tmp = Path(tempfile.mkdtemp(prefix="sgm_vitrine_"))
os.environ["APPDATA"] = str(tmp / "roaming")
os.environ["LOCALAPPDATA"] = str(tmp / "local")
os.environ["HOME"] = os.environ["USERPROFILE"] = str(tmp / "home")
(tmp / "home" / "Downloads").mkdir(parents=True)
os.environ["SGM_NO_UPDATE"] = "1"   # jamais de réseau
import statics_manager as m  # noqa: E402

m._DATA_DIR = tmp / "SGM_data"
m._DATA_DIR.mkdir(parents=True)
lib = tmp / "Library"
gsx = tmp / "GSX"
gsx.mkdir()
INI = b"[general]\n[section.1]\npushback=1\n"


def pkg(folder, title, creator, files, gsx_installed=None):
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
    if gsx_installed:
        name, data = gsx_installed
        (gsx / name).write_bytes(data)


ON_OFF = lambda pre: [(f"scenery/{pre}_statics.bgl", b"S" * 40, True)]
pkg("northwind-ebbr-brussels", "Brussels Airport EBBR", "Northwind Sceneries",
    ON_OFF("EBBR") + [("GSX/ebbr-northwind.ini", INI + b"ebbr", False)], ("ebbr-northwind.ini", INI + b"ebbr"))
pkg("aerolux-lfpg-paris", "Paris Charles de Gaulle LFPG", "Aerolux Studio", [
    ("scenery/statics_on.bgl", b"N" * 9, False), ("scenery/statics_off.bgl", b"F" * 9, False),
    ("scenery/statics.bgl", b"F" * 9, True),
    ("GSX/LFPG FULL/lfpg-aerolux.ini", INI + b"full", False), ("GSX/LFPG LITE/lfpg-aerolux.ini", INI + b"lite", False)])
pkg("skyharbor-egll-heathrow", "London Heathrow EGLL", "Skyharbor Design", [
    ("scenery/EGLL_statics.bgl.off", b"S" * 9, False), ("GSX Profile/egll-skyharbor.ini", INI, False)])
pkg("bluefin-kjfk-newyork", "New York JFK KJFK", "Bluefin Works", [
    ("Scenery/kjfk/kjfk-statics.off", b"S" * 9, False), ("Scenery/kjfk/kjfk-airport.bgl", b"A" * 99, True)])
pkg("northwind-eham-schiphol", "Amsterdam Schiphol EHAM", "Northwind Sceneries",
    ON_OFF("EHAM") + [("GSX/eham-northwind.ini", INI + b"eham", False)], ("eham-northwind.ini", INI + b"eham"))
pkg("altair-lszh-zurich", "Zurich Kloten LSZH", "Altair Simulations", [
    ("scenery/world/scenery/lszh_place.bgl", b"P" * 20, True), ("scenery/world/scenery/lszh_place.bgl.nostatic", b"N" * 15, False)])
pkg("aerolux-ebci-charleroi", "Charleroi Brussels South EBCI", "Aerolux Studio", [
    ("scenery/statics_on.bgl", b"N" * 9, False), ("scenery/statics_off.bgl", b"F" * 9, False),
    ("scenery/EBCI_statics_vehicles.bgl", b"V" * 9, True)])
pkg("meridian-omdb-dubai", "Dubai International OMDB", "Meridian Scenery", ON_OFF("OMDB"))
pkg("skyharbor-ksea-seattle", "Seattle-Tacoma KSEA", "Skyharbor Design",
    [("scenery/KSEA_statics.bgl.off", b"S" * 9, False), ("scenery/KSEA.bgl", b"A" * 50, True)])
pkg("bluefin-rjtt-haneda", "Tokyo Haneda RJTT", "Bluefin Works", ON_OFF("RJTT"))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
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
cfg.update_check = False
cfg.check_downloads = False
cfg.manual_folders.append(str(lib))
cfg.gsx_override = str(gsx)
cfg.first_run = False
cfg.save()
m.set_lang(lang)
app.setLayoutDirection(Qt.RightToLeft if lang in m.RTL_LANGS else Qt.LeftToRight)
w = m.MainWindow()
w.resize(1400, 820)
w.show()

steps = []


def save(widget, name):
    app.processEvents()
    widget.grab().save(str(out_dir / name))
    print(out_dir / name)


def main_shot():
    # quelques scènes passées à ON pour un tableau varié, sans bandeau
    for key in ("skyharbor-egll-heathrow", "bluefin-kjfk-newyork"):
        for s in w.scenes.values():
            if s.root.name == key:
                m.set_scene_state(s, m.OFF if s.state == m.ON else m.ON)
                w.refresh_scene(s)
    w.session_new.clear()
    for s in w.scenes.values():
        s.is_new = False
    w.banner.hide()
    w.rebuild_rows()
    w.update_stats()
    w.apply_filter()
    QTimer.singleShot(400, lambda: (save(w, "main.png"), QTimer.singleShot(100, narrow_shot)))


def narrow_shot():
    w.resize(960, 760)
    QTimer.singleShot(400, lambda: (save(w, "narrow.png"), QTimer.singleShot(100, dialogs)))


def dialogs():
    w.resize(1400, 820)
    d = m.DocDialog(m.tr("m_guide").rstrip("…"), m.tr("help_html"), w._doc_note(), w)
    d.resize(900, 760)
    d.show()
    QTimer.singleShot(400, lambda: (save(d, "guide.png"), d.close(), QTimer.singleShot(100, report)))


def report():
    d = m.ReportDialog("bug", cfg.sim, [s.title for s in w.scenes.values()], w)
    d.show()
    QTimer.singleShot(400, lambda: (save(d, "report.png"), d.close(), app.quit()))


QTimer.singleShot(1800, main_shot)
app.exec()
