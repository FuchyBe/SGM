# -*- coding: utf-8 -*-
"""Journal local : contenu utile, aucun chemin personnel, rotation, copie pour le signalement."""
import logging.handlers
import os
import sys
import unittest

from helpers import SandboxTest, make_pkg, m


class LogTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self._hook = sys.excepthook
        self.assertTrue(m.setup_logging())

    def tearDown(self):
        m.close_logging()
        sys.excepthook = self._hook
        super().tearDown()

    def text(self) -> str:
        for h in m.LOG.handlers:
            h.flush()
        return m.log_file().read_text(encoding="utf-8")

    def test_scrub_retire_le_dossier_personnel(self):
        s = m.scrub(r"C:\Users\Jean Dupont\Downloads\a.zip ; c:/users/bob/x ; D:\MSFS\Community\pkg")
        self.assertNotIn("Jean", s)
        self.assertNotIn("bob", s)
        self.assertIn(r"~\Downloads\a.zip", s)
        self.assertIn(r"D:\MSFS\Community\pkg", s)
        self.assertNotIn(str(self.tmp / "home"), m.scrub(str(self.tmp / "home" / "Downloads" / "x.zip")))

    def test_bascule_journalisee_sans_chemin(self):
        make_pkg(self.community, "test-ebbr", "Brussels EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 40, True), ("scenery/EBBR.bgl", b"A" * 90, True)])
        m.set_scene_state(self.scan()["test-ebbr"], m.OFF)
        log = self.text()
        self.assertIn("Statics Brussels EBBR [test-ebbr] : on -> off", log)
        self.assertIn("renommé EBBR_statics.bgl -> EBBR_statics.bgl.off", log)
        self.assertIn("terminé", log)
        self.assertNotIn(str(self.tmp), log)

    def test_erreur_journalisee_avec_trace(self):
        root = make_pkg(self.community, "test-ebbr", "Brussels EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 40, True)])
        scene = self.scan()["test-ebbr"]
        (root / "scenery/EBBR_statics.bgl.off").write_bytes(b"x")     # cible déjà présente
        with self.assertRaises(Exception):
            m.set_scene_state(scene, m.OFF)
        log = self.text()
        self.assertIn("Échec de la bascule Brussels EBBR", log)
        self.assertIn("Traceback", log)

    def test_gsx_et_restauration(self):
        f = self.tmp / "home" / "Downloads" / "ebbr.ini"
        f.write_bytes(b"[general]\n")
        m.install_profile_files([f], self.gsx)
        m.gsx_restore(self.gsx)
        log = self.text()
        self.assertIn("GSX : installation de ebbr.ini", log)
        self.assertIn("remis à l'origine", log)
        self.assertNotIn(str(self.tmp / "home"), log)

    def test_rotation(self):
        h = next(h for h in m.LOG.handlers if isinstance(h, logging.handlers.RotatingFileHandler))
        self.assertEqual((h.maxBytes, h.backupCount), (1_000_000, 4))
        self.assertTrue(m.setup_logging())                  # pas de second fichier ouvert
        self.assertEqual(sum(isinstance(x, logging.handlers.RotatingFileHandler) for x in m.LOG.handlers), 1)

    def test_journal_dans_le_paquet_de_signalement(self):
        m.LOG.info("chemin %s", r"C:\Users\Jean Dupont\Downloads")
        out = m.build_report_package("bug", "MSFS 2024", "en", {"what": "x"}, include_log=True)
        import zipfile
        with zipfile.ZipFile(out) as z:
            self.assertIn("sgm.log", z.namelist())
            self.assertNotIn("Jean", z.read("sgm.log").decode("utf-8"))

if __name__ == "__main__":
    unittest.main()
