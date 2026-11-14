# -*- coding: utf-8 -*-
"""Bouton Annuler : activé après une action, remet la scène et le profil GSX, se désactive ensuite."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from PySide6.QtCore import QTimer  # noqa: E402

from helpers import SandboxTest, m, make_pkg, profile  # noqa: E402
from test_gui_smoke import wait_scan  # noqa: E402

APP = QApplication.instance() or QApplication([])


class UndoGuiTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.root = make_pkg(self.community, "test-ebbr", "Brussels Airport EBBR",
                             [("s/EBBR_statics.bgl", b"S" * 9, True), ("GSX/ebbr-x.ini", profile("a"), False)])
        cfg = m.Config()
        cfg.manual_folders.append(str(self.community))
        cfg.gsx_override = str(self.gsx)
        cfg.save()
        self._ask = m.ask
        m.ask = lambda *a, **k: True

    def tearDown(self):
        m.ask = self._ask
        super().tearDown()

    def test_annuler_bascule_et_gsx(self):
        w = m.MainWindow()
        QTimer.singleShot(0, w.start_scan)
        wait_scan(w)
        scene = next(s for s in w.scenes.values() if s.folder == "test-ebbr")
        self.assertFalse(w.btn_undo.isEnabled())
        w.on_toggle(scene, False)
        self.assertEqual(w.scenes[scene.key].state, m.OFF)
        self.assertTrue(w.btn_undo.isEnabled())
        self.assertIn("Brussels Airport EBBR", w.btn_undo.toolTip())
        w.on_gsx(w.scenes[scene.key], 0, str(self.gsx))
        self.assertTrue((self.gsx / "ebbr-x.ini").is_file())
        w.undo_last_action()                                # le profil GSX est retiré
        self.assertFalse((self.gsx / "ebbr-x.ini").exists())
        self.assertEqual(w.scenes[scene.key].state, m.OFF)
        w.undo_last_action()                                # puis la bascule
        self.assertEqual(w.scenes[scene.key].state, m.ON)
        self.assertTrue((self.root / "s/EBBR_statics.bgl").is_file())
        self.assertFalse(w.btn_undo.isEnabled())
        w.close()
        w.deleteLater()
        APP.processEvents()


if __name__ == "__main__":
    import unittest
    unittest.main()
