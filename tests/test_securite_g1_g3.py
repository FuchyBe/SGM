# -*- coding: utf-8 -*-
"""Sécurité G1 à G3 (relecture du gardien de 3AM, 2026-11-15)."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, profile  # noqa: E402

APP = QApplication.instance() or QApplication([])


class G1ProfilsGsxTest(SandboxTest):
    def install(self, name, data):
        src = self.tmp / "dl" / name
        src.parent.mkdir(exist_ok=True)
        src.write_bytes(data)
        m.install_profile_files([src], self.gsx)

    def test_profil_retouche_garde(self):
        self.install("ebbr-a.ini", profile("sgm"))
        (self.gsx / "ebbr-a.ini").write_bytes(profile("retouché dans l'éditeur GSX"))
        kept = []
        self.assertEqual(m.gsx_restore(self.gsx, None, kept), 0)
        self.assertEqual(kept, ["ebbr-a.ini"])
        self.assertEqual((self.gsx / "ebbr-a.ini").read_bytes(), profile("retouché dans l'éditeur GSX"))
        self.assertTrue(m.gsx_has_origin(self.gsx, ["ebbr-a.ini"]))      # toujours dans le journal

    def test_profil_intact_retire(self):
        self.install("ebbr-a.ini", profile("sgm"))
        self.assertEqual(m.gsx_restore(self.gsx), 1)
        self.assertFalse((self.gsx / "ebbr-a.ini").exists())

    def test_profil_remplace_puis_retouche(self):
        (self.gsx / "ebbr-a.ini").write_bytes(profile("origine"))
        self.install("ebbr-a.ini", profile("sgm"))
        self.assertEqual(m.gsx_restore(self.gsx), 1)                     # intact : l'origine revient
        self.assertEqual((self.gsx / "ebbr-a.ini").read_bytes(), profile("origine"))
        self.install("ebbr-a.ini", profile("sgm"))
        (self.gsx / "ebbr-a.ini").write_bytes(profile("à la main"))
        kept = []
        m.gsx_restore(self.gsx, None, kept)
        self.assertEqual((self.gsx / "ebbr-a.ini").read_bytes(), profile("à la main"))
        self.assertEqual(kept, ["ebbr-a.ini"])

    def test_ancien_journal_sans_empreinte(self):
        self.install("ebbr-a.ini", profile("sgm"))
        jd = m._gsx_journal_dir(self.gsx)
        j = json.loads((jd / "journal.json").read_text(encoding="utf-8"))
        for e in j["files"].values():
            e.pop("written")                                              # journal SGM ≤ 0.8
        (jd / "journal.json").write_text(json.dumps(j), encoding="utf-8")
        kept = []
        self.assertEqual(m.gsx_restore(self.gsx, None, kept), 0)          # inconnu = on ne touche à rien
        self.assertTrue((self.gsx / "ebbr-a.ini").is_file())


class G2CorbeilleTest(SandboxTest):
    def test_pas_de_disque_fixe_archive_gardee(self):
        arc = self.tmp / "home" / "Downloads" / "ebbr.zip"
        arc.write_bytes(b"zip")
        old = m.drive_is_fixed
        m.drive_is_fixed = lambda p: False
        try:
            with self.assertRaises(m.NotRecyclable):
                m.send_to_trash(arc)
            failed = m.trash_archives([arc])
        finally:
            m.drive_is_fixed = old
        self.assertTrue(arc.is_file())
        self.assertEqual(failed[0][0], "ebbr.zip")
        self.assertIn("ebbr.zip", failed[0][1])


class G3SimulateurTest(SandboxTest):
    def test_les_deux_simulateurs_et_inconnu(self):
        w = m.MainWindow()
        warned, asked = [], []
        old = (m.running_sims, m.warn, m.ask)
        m.warn = lambda parent, text: warned.append(text)
        m.ask = lambda parent, text, default_yes=True: asked.append((text, default_yes)) or False
        try:
            m.running_sims = lambda: []
            self.assertTrue(w.ensure_sim_closed())
            other = next(s for s in m.SIMS if s != w.config.sim)
            m.running_sims = lambda: [other]                  # l'AUTRE simulateur tourne : bloqué aussi
            self.assertFalse(w.ensure_sim_closed())
            self.assertIn(other, warned[0])
            m.running_sims = lambda: None                     # inconnu : on demande, « Non » par défaut
            self.assertFalse(w.ensure_sim_closed())
            self.assertEqual(asked, [(m.tr("sim_unknown"), False)])
        finally:
            m.running_sims, m.warn, m.ask = old
            w.close()
            w.deleteLater()
            APP.processEvents()


if __name__ == "__main__":
    import unittest
    unittest.main()
