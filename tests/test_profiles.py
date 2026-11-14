# -*- coding: utf-8 -*-
"""Profils de statics : enregistrement, application (cas simples), mémorisation, annulation."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, make_pkg  # noqa: E402
from test_gui_smoke import wait_scan  # noqa: E402

APP = QApplication.instance() or QApplication([])


class ProfilesEngineTest(SandboxTest):
    def setUp(self):
        super().setUp()
        make_pkg(self.community, "a", "AAAA", [("s/AAAA_statics.bgl", b"S" * 9, True)])
        make_pkg(self.community, "b", "BBBB", [("s/BBBB_statics.bgl.off", b"T" * 9, False)])
        make_pkg(self.community, "c", "CCCC", [("s/CCCC_statics.bgl", b"U" * 9, True),
                                               ("s/CCCC_statics.bgl.off", b"V" * 9, False)])   # à vérifier

    def test_enregistrer_et_planifier(self):
        sc = self.scan()
        prof = m.profile_from_scenes(sc.values())
        self.assertEqual(prof, {sc["a"].key: "on", sc["b"].key: "off"})        # la scène à vérifier est exclue
        m.set_scene_state(sc["a"], m.OFF)
        sc = self.scan()
        prof2 = dict(prof)
        prof2[sc["c"].key] = "off"
        prof2["inconnue"] = "on"
        todo, check, missing = m.profile_plan(prof2, sc.values())
        self.assertEqual([(s.key, t) for s, t in todo], [(sc["a"].key, m.ON)])
        self.assertEqual((check, missing), (1, 1))

    def test_memorise_par_simulateur(self):
        cfg = m.Config()
        cfg.statics_profiles["Vols photo"] = {"k1": "off", "k2": "on", "k3": "bizarre"}
        cfg.save()
        cfg = m.Config()
        self.assertEqual(cfg.statics_profiles, {"Vols photo": {"k1": "off", "k2": "on"}})
        cfg.sim = "MSFS 2020"
        self.assertEqual(cfg.statics_profiles, {})


class ProfilesGuiTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.a = make_pkg(self.community, "a", "AAAA", [("s/AAAA_statics.bgl", b"S" * 9, True)])
        self.b = make_pkg(self.community, "b", "BBBB", [("s/BBBB_statics.bgl", b"T" * 9, True)])
        cfg = m.Config()
        cfg.manual_folders.append(str(self.community))
        cfg.save()
        self._ask, self._get = m.ask, m.QInputDialog.getText
        m.ask = lambda *a, **k: True
        m.QInputDialog.getText = staticmethod(lambda *a, **k: ("Trafic IA dense", True))

    def tearDown(self):
        m.ask, m.QInputDialog.getText = self._ask, self._get
        super().tearDown()

    def test_appliquer_puis_annuler(self):
        w = m.MainWindow()
        QTimer.singleShot(0, w.start_scan)
        wait_scan(w)
        state = lambda f: next(s for s in w.scenes.values() if s.folder == f).state
        w.save_profile()                                     # tout ON
        self.assertIn("Trafic IA dense", m.Config().statics_profiles)
        w.build_profiles_menu()
        self.assertTrue(any("Trafic IA dense" in a.text() for a in w.profiles_menu.actions()))
        for f in ("a", "b"):
            w.on_toggle(next(s for s in w.scenes.values() if s.folder == f), False)
        self.assertEqual((state("a"), state("b")), (m.OFF, m.OFF))
        w.apply_profile("Trafic IA dense")
        self.assertEqual((state("a"), state("b")), (m.ON, m.ON))
        self.assertIn("Trafic IA dense", m.undo_label())
        w.undo_last_action()                                 # le profil entier est annulé d'un coup
        self.assertEqual((state("a"), state("b")), (m.OFF, m.OFF))
        w.delete_profile("Trafic IA dense")
        self.assertEqual(m.Config().statics_profiles, {})
        w.close()
        w.deleteLater()
        APP.processEvents()


if __name__ == "__main__":
    import unittest
    unittest.main()
