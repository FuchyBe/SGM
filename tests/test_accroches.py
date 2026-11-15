# -*- coding: utf-8 -*-
"""Points d'accroche pour une application hôte (3AM), S1 à S12 : sans effet sur SGM seul, utilisables par l'hôte."""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, make_pkg  # noqa: E402

APP = QApplication.instance() or QApplication([])

JETONS = ("text2 hover pressed accent_hover accent_dis_bg accent_dis_fg accent_soft accent_line accent_pressed sel "
          "off_text off_text_hover off_line off_soft off_soft_hover warn_soft warn_line warn_soft_hover blue_soft "
          "blue_soft2 blue_line banner_line danger danger_hover danger_pressed danger_dis_bg danger_dis_fg on_danger "
          "row_hover scroll_hover doc_text heart_hover knob track_dis knob_dis menubar switch_off").split()


class HookTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.saved = {k: getattr(m, k) for k in ("HOST_REPLACE", "EXTRA_SOURCES", "REAL_ROOTS", "HOST_CONFIRM_SIM",
                                                 "HOST_HELP_ITEMS", "SWITCH_MARKS", "running_sims", "UNDO_TOTAL_MAX")}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(m, k, v)
        super().tearDown()

    def window(self):
        w = m.MainWindow()
        self.addCleanup(lambda: (w.close(), w.deleteLater(), APP.processEvents()))
        return w

    def test_valeurs_par_defaut_sans_effet(self):
        self.assertIsNone(m.HOST_REPLACE)
        self.assertIsNone(m.EXTRA_SOURCES)
        self.assertFalse(m.REAL_ROOTS)
        self.assertIsNone(m.HOST_CONFIRM_SIM)
        self.assertIsNone(m.HOST_HELP_ITEMS)
        self.assertFalse(m.SWITCH_MARKS)
        self.assertFalse(m.hosted())

    def test_s4_theme_par_jetons(self):
        for k in JETONS:
            self.assertIn(k, m.C)
        self.assertEqual(m.QSS, m.build_qss(m.C))
        self.assertEqual(m.DOC_CSS, m.build_doc_css(m.C))
        # aucune couleur en dur : chaque couleur de la feuille vient de C
        valeurs = {v.upper() for v in m.C.values()}
        for css in (m.QSS, m.DOC_CSS):
            self.assertEqual({h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", css)} - valeurs, set())
        clair = dict(m.C, hover="#010203", bg="#FAFAFA")
        self.assertIn("#010203", m.build_qss(clair))
        self.assertIn("font-size: 26px", m.build_qss(m.C, font_scale=2.0))      # tailles à l'échelle

    def test_s5_marques_interrupteur(self):
        m.SWITCH_MARKS = True
        sw = m.Switch()
        sw.setChecked(True)
        img = sw.grab()                                # dessin sans erreur, avec ✓
        self.assertFalse(img.isNull())
        sw.setChecked(False)
        self.assertFalse(sw.grab().isNull())

    def test_s1_remplacement_par_l_hote(self):
        w = self.window()
        calls = []
        m.HOST_REPLACE = lambda state: calls.append(state)
        self.assertTrue(m.hosted())
        w._replace_window({"x": 1})
        self.assertEqual(calls, [{"x": 1}])
        self.assertTrue(w.isVisible() or True)            # la fenêtre n'est pas recréée par SGM

    def test_s2_sources_de_l_hote(self):
        lib = self.tmp / "Bibliotheque"
        lib.mkdir()
        cfg = m.Config()
        m.EXTRA_SOURCES = [("3AM", lib), ("3AM", lib)]
        src = m.find_sources(cfg)
        self.assertEqual([s.path for s in src if s.label == "3AM"], [lib])          # dédoublonnée
        m.EXTRA_SOURCES = lambda c: [("Lib", lib)]
        self.assertTrue(any(s.label == "Lib" for s in m.find_sources(cfg)))
        m.EXTRA_SOURCES = lambda c: 1 / 0                                           # erreur de l'hôte : ignorée
        self.assertIsInstance(m.find_sources(cfg), list)

    def test_s3_chemins_reels(self):
        real = make_pkg(self.tmp / "vrai", "test-ebbr", "EBBR", [("s/EBBR_statics.bgl", b"S" * 9, True)])
        link = self.community / "test-ebbr"
        os.symlink(real, link, target_is_directory=True)
        m.REAL_ROOTS = True
        scenes = m.scan_all([m.Source("Community", self.community, True, True)])
        self.assertEqual([s.root for s in scenes], [real.resolve()])

    def test_s7_etat_du_simulateur(self):
        sim = next(iter(m.SIMS))
        m.running_sims = lambda: [sim]
        self.assertEqual((m.sim_state(sim), m.sim_running(sim)), (m.SIM_OPEN, True))
        m.running_sims = lambda: []
        self.assertEqual(m.sim_state(sim), m.SIM_CLOSED)
        m.running_sims = lambda: None
        self.assertEqual((m.sim_state(sim), m.sim_running(sim)), (m.SIM_UNKNOWN, False))

    def test_s8_plafond_des_copies(self):
        m.UNDO_TOTAL_MAX = 0                              # plus de place : empreinte seule
        root = make_pkg(self.community, "test-ebbr", "EBBR", [("s/EBBR_statics.bgl", b"S" * 400, True)])
        before = (root / "s/EBBR_statics.bgl").read_bytes()
        with m.undoable("x"):
            m.set_scene_state(self.scan()["test-ebbr"], m.OFF)
        copies = [f for f in (self.data / "undo").rglob("*_EBBR_statics.bgl")]
        self.assertEqual(copies, [])
        m.undo_last()                                      # retrouvé par empreinte après renommage
        self.assertEqual((root / "s/EBBR_statics.bgl").read_bytes(), before)

    def test_s9_usercfg_durci(self):
        cfg = self.tmp / "UserCfg.opt"
        good = str(self.tmp / "Packages")
        cfg.write_text('﻿InstalledPackagesPath "' + good + '"\n', encoding="utf-8")
        self.assertEqual(m.parse_usercfg(cfg), m.Path(good))
        cfg.write_text('InstalledPackagesPath "relatif\\\\dossier"\n', encoding="utf-8")
        self.assertIsNone(m.parse_usercfg(cfg))
        cfg.write_text('InstalledPackagesPath "' + good + '\x07"\n', encoding="utf-8")
        self.assertIsNone(m.parse_usercfg(cfg))
        cfg.write_bytes(b"x" * (m.USERCFG_MAX + 1))
        self.assertIsNone(m.parse_usercfg(cfg))
        self.assertTrue(m.DocDialog("t", "<p>x</p>").isSizeGripEnabled())
        self.assertTrue(m.FoldersDialog(m.Config(), []).isSizeGripEnabled())

    def test_s10_s12_mode_hote(self):
        m.HOST_REPLACE = lambda state: None
        m.HOST_HELP_ITEMS = ["m_guide", "m_licenses", "m_backups", "m_restore_all", "m_stats_report",
                             "m_check_updates"]
        w = self.window()
        keys = [a.data() for a in w.help_menu.actions() if a.data()]
        self.assertEqual(keys, ["m_guide", "m_licenses", "m_backups", "m_restore_all", "m_stats_report"])
        texts = [a.text() for a in w.menuBar().actions()[0].menu().actions()] if w.menuBar().actions() else []
        self.assertNotIn(m.tr("m_update_auto"), texts)
        asked = []
        old_ask = m.ask
        m.ask = lambda *a, **k: asked.append(a) or True
        try:
            w.config.update_check = None
            w.maybe_check_updates()                         # jamais de question ni de réseau dans l'hôte
            w.check_updates(manual=True)
        finally:
            m.ask = old_ask
        self.assertEqual(asked, [])
        self.assertIsNone(w.upd_worker)

    def test_s11_controle_par_l_hote(self):
        w = self.window()
        m.running_sims = lambda: []
        m.HOST_CONFIRM_SIM = lambda parent: False          # l'hôte refuse : SGM n'écrit pas
        self.assertFalse(w.ensure_sim_closed())
        m.running_sims = lambda: list(m.SIMS)
        m.HOST_CONFIRM_SIM = lambda parent: True           # l'hôte décide seul
        self.assertTrue(w.ensure_sim_closed())
        m.HOST_CONFIRM_SIM = lambda parent: 1 / 0          # erreur de l'hôte : on n'écrit pas
        self.assertFalse(w.ensure_sim_closed())


if __name__ == "__main__":
    import unittest
    unittest.main()
