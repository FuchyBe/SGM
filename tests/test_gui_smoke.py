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

        # colonnes : ×1,5 à 1280 px, proportionnelles, minimums respectés, réglables à la poignée
        w.resize(1280, 800)
        APP.processEvents()
        row = next(iter(w.rows.values()))
        ws0, wg0 = row.st_col.width(), row.gsx_col.width()
        self.assertGreaterEqual(ws0, 300)
        self.assertGreaterEqual(wg0, 400)
        w.resize(1900, 900)
        APP.processEvents()
        self.assertGreater(row.st_col.width(), ws0)
        self.assertGreater(row.gsx_col.width(), wg0)
        w.resize(820, 600)
        APP.processEvents()
        self.assertGreaterEqual(row.st_col.width(), m.COL_STATICS_MIN)
        self.assertGreaterEqual(row.gsx_col.width(), m.COL_GSX_MIN)
        w.resize(1280, 800)
        APP.processEvents()
        before = row.st_col.width()
        w._drag_column(1, 40)
        w._save_columns()
        self.assertEqual(row.st_col.width(), before + 40)
        self.assertEqual(m.Config().col_fs, w.config.col_fs)  # réglage mémorisé

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
