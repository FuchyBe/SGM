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

        # catégories
        w.cat_combo.setCurrentIndex(m.CATEGORY_KEYS.index("gsx_none"))
        APP.processEvents()
        self.assertEqual([r.scene.icao for r in w.rows.values() if r.isVisible()], ["LEMD"])

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
