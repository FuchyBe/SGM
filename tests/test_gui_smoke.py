# -*- coding: utf-8 -*-
"""L'interface démarre, analyse, change de langue (dont l'arabe) et ouvre ses fenêtres sans erreur."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, make_pkg, profile  # noqa: E402

APP = QApplication.instance() or QApplication([])


def wait_scan(win, timeout_ms=15000):
    """Attend la fin de l'analyse en arrière-plan."""
    elapsed = 0
    while (win.busy or win.worker is None) and elapsed < timeout_ms:
        APP.processEvents()
        QTimer.singleShot(50, lambda: None)
        win.worker and win.worker.wait(50)
        elapsed += 50
    APP.processEvents()


class TestGui(SandboxTest):

    def setUp(self):
        super().setUp()
        pkgs = self.tmp / "pkgs"
        cfg = (self.tmp / "local" / "Packages" / "Microsoft.Limitless_8wekyb3d8bbwe" / "LocalCache")
        cfg.mkdir(parents=True)
        (cfg / "UserCfg.opt").write_text(f'InstalledPackagesPath "{pkgs}"\n')
        make_pkg(pkgs / "Community", "test-ebbr", "Brussels Airport EBBR",
                 [("s/EBBR_statics.bgl", b"S", True), ("GSX/ebbr-x.ini", profile("a"), False)])
        make_pkg(pkgs / "Community2024", "test-lemd", "Madrid Barajas LEMD", [("s/LEMD.bgl", b"A", True)])

    def test_main_window_lifecycle(self):
        w = m.MainWindow()
        w.show()
        QTimer.singleShot(0, w.start_scan)
        wait_scan(w)
        self.assertEqual(sorted(s.icao for s in w.scenes.values()), ["EBBR", "LEMD"])
        self.assertEqual(sorted(s.label for s in w.sources), ["Community", "Community2024"])

        # filtres par colonne (même logique pour Statics et GSX)
        visible = lambda: sorted(r.scene.icao for r in w.rows.values() if r.isVisible())
        gsx = w.col_header.combos["gsx"]
        gsx.setCurrentIndex(gsx.findData("none"))
        APP.processEvents()
        self.assertEqual(visible(), ["LEMD"])
        self.assertTrue(w.reset_btn.isVisibleTo(w))
        st = w.col_header.combos["statics"]
        st.setCurrentIndex(st.findData("on"))
        APP.processEvents()
        self.assertEqual(visible(), [])                       # LEMD n'a pas de statics
        w.reset_filters()
        APP.processEvents()
        self.assertEqual(visible(), ["EBBR", "LEMD"])
        st.setCurrentIndex(st.findData("on"))
        APP.processEvents()
        self.assertEqual(visible(), ["EBBR"])
        w.reset_filters()

        # colonnes : ajustées au texte sur une ligne (automatique), réglables à la main, double-clic = automatique
        def settle(wd, ht):
            w.resize(wd, ht)
            for _ in range(5):
                APP.processEvents()
            w.layout_columns()
        row = lambda: next(iter(w.rows.values()))   # relue : une analyse peut reconstruire les lignes
        settle(1280, 800)
        self.assertTrue(w._col_auto)
        ns, ng = w._natural_widths()
        ws0, wg0 = row().st_col.width(), row().gsx_col.width()
        self.assertEqual((ws0, wg0), (max(ns, w._floors()[0]), max(ng, w._floors()[1])))
        for r in w.rows.values():                  # aucun texte de colonne coupé
            if not r.isHidden():
                self.assertEqual(r.st_note.text(), r.st_note._full)
                self.assertEqual(r.gsx_note.text(), r.gsx_note._full)
        settle(1900, 900)                          # plus large : les colonnes gardent leur largeur, la scène grandit
        self.assertEqual((row().st_col.width(), row().gsx_col.width()), (ws0, wg0))
        settle(700, 600)                           # très étroit : jamais sous l'en-tête lisible
        fs_, fg_ = w._floors()
        self.assertGreaterEqual(row().st_col.width(), fs_)
        self.assertGreaterEqual(row().gsx_col.width(), fg_)
        settle(1280, 800)
        before = row().st_col.width()
        w._drag_column(0, -40)                     # trait scène | Statics tiré vers la gauche
        w._save_columns()
        self.assertFalse(w._col_auto)
        self.assertEqual(row().st_col.width(), before + 40)
        cfg = m.Config()
        self.assertFalse(cfg.col_auto)              # réglage à la main mémorisé
        self.assertEqual(cfg.col_fs, w.config.col_fs)
        w.col_header.handles[1].reset.emit()        # double-clic : retour à l'automatique
        self.assertTrue(w._col_auto and m.Config().col_auto)
        self.assertEqual(row().st_col.width(), before)

        # fenêtres d'aide et dossiers
        for html in ("help_html", "disclaimer_html", "licenses_html"):
            m.DocDialog("x", m.tr(html), "", w).close()
        m.FoldersDialog(w.config, w.sources, w).close()

        # changement de langue (fenêtre recréée), y compris l'arabe de droite à gauche
        for lang in ("fr", "ar", "en"):
            w.change_language(lang)
            APP.processEvents()
            w = APP.main_window if hasattr(APP, "main_window") else w
        w.close()


if __name__ == "__main__":
    unittest.main()
