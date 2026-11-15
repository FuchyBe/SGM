# -*- coding: utf-8 -*-
"""Robustesse (revue des agents du 2026-11-15) : Annuler une restauration, gros fichiers, scène disparue,
annulation interrompue, paquets homonymes, contrôle du simulateur avant GSX."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, make_pkg, profile  # noqa: E402

APP = QApplication.instance() or QApplication([])


class RobustesseTest(SandboxTest):
    def files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_annuler_une_restauration_garde_l_origine(self):
        root = make_pkg(self.community, "e", "EBBR", [("s/EBBR_statics.bgl", b"S" * 40, True)])
        orig = self.files(root)
        m.set_scene_state(self.scan()["e"], m.OFF)
        with m.undoable("restaurer"):
            m.restore_scene_statics(root)
        m.undo_last()                                    # retour à OFF
        self.assertTrue(m.has_origin(root))
        m.set_scene_state(self.scan()["e"], m.ON)
        m.set_scene_state(self.scan()["e"], m.OFF)
        m.restore_scene_statics(root)                    # la vraie origine, pas l'état OFF
        self.assertEqual(self.files(root), orig)

    def test_annuler_une_restauration_gsx_garde_le_journal(self):
        (self.gsx / "ebbr-a.ini").write_bytes(profile("à moi"))
        src = self.tmp / "dl"
        src.mkdir()
        (src / "ebbr-a.ini").write_bytes(profile("sgm"))
        m.install_profile_files([src / "ebbr-a.ini"], self.gsx)
        with m.undoable("restaurer"):
            m.gsx_restore(self.gsx)
        m.undo_last()                                    # le profil SGM revient
        self.assertEqual((self.gsx / "ebbr-a.ini").read_bytes(), profile("sgm"))
        m.gsx_restore(self.gsx)                          # et l'origine est toujours connue
        self.assertEqual((self.gsx / "ebbr-a.ini").read_bytes(), profile("à moi"))

    def test_annuler_gros_fichier_avec_double_identique(self):
        old = m.UNDO_COPY_MAX
        m.UNDO_COPY_MAX = 10                             # « gros » fichiers : pas de copie
        try:
            d = "scenery/UK2000Scenery/scenery"
            root = make_pkg(self.community, "uk", "KHND", [
                (f"{d}/khnd-airport.bgl", b"NO" * 200, True), (f"{d}/khnd-airport.bgl.staticq", b"WI" * 300, False)])
            m.set_scene_state(self.scan()["uk"], m.ON)
            before = self.files(root)
            with m.undoable("off"):
                m.set_scene_state(self.scan()["uk"], m.OFF)
            m.undo_last()                                # retrouvé grâce au .staticq resté à côté
            self.assertEqual(self.files(root), before)
        finally:
            m.UNDO_COPY_MAX = old

    def test_scene_disparue_rien_n_est_touche(self):
        root = make_pkg(self.community, "e", "EBBR", [("s/EBBR_statics.bgl", b"S" * 40, True)])
        sc = self.scan()["e"]
        (root / "s/EBBR_statics.bgl").rename(self.tmp / "ailleurs.bgl")
        with self.assertRaises(m.ToggleError):
            m.set_scene_state(sc, m.OFF)
        self.assertFalse(m.has_origin(root))             # aucune photo d'origine vide

    def test_annulation_interrompue_remise_en_etat(self):
        a = make_pkg(self.community, "a", "AAAA", [("s/AAAA_statics.bgl", b"A" * 40, True)])
        b = make_pkg(self.community, "b", "BBBB", [("s/BBBB_statics.bgl", b"B" * 40, True)])
        with m.undoable("tout off"):
            for k in ("a", "b"):
                m.set_scene_state(self.scan()[k], m.OFF)
        after = (self.files(a), self.files(b))
        real, calls = os.replace, []

        def boom(s, d):
            calls.append(s)
            if len(calls) == 2:
                raise PermissionError(13, "verrouillé", str(d))
            return real(s, d)
        m.os.replace = boom
        try:
            with self.assertRaises(m.UndoError):
                m.undo_last()
        finally:
            m.os.replace = real
        for root in (a, b):
            self.assertEqual([p for p in root.rglob("*.sgm-undo")], [])   # aucun fichier sous un nom temporaire
        self.assertEqual(len(m.undo_stack()), 1)         # l'action reste annulable

    def test_paquets_homonymes_sauvegardes_separees(self):
        c2 = self.tmp / "Community2020"
        a = make_pkg(self.community, "meme-nom", "EBBR", [("s/EBBR_statics.bgl", b"A" * 9, True)])
        b = make_pkg(c2, "meme-nom", "EBBR", [("s/EBBR_statics.bgl", b"B" * 9, True)])
        m.backup_files(a, [a / "s/EBBR_statics.bgl"])
        for _ in range(12):
            m.backup_files(b, [b / "s/EBBR_statics.bgl"])
        dirs = sorted((self.data / "backups").glob("meme-nom-*"))
        self.assertEqual(len(dirs), 2)
        self.assertTrue(any(len(list(d.iterdir())) == 1 for d in dirs))   # la sauvegarde de A existe encore

    def test_gsx_bloque_si_simulateur_ouvert(self):
        w = m.MainWindow()
        old = (m.running_sims, m.warn)
        m.running_sims = lambda: list(m.SIMS)[:1]
        m.warn = lambda *a, **k: None
        try:
            arc = self.tmp / "x.zip"
            arc.write_bytes(b"pas une archive")
            w.install_paths([str(arc)])                  # refusé avant toute écriture
            self.assertEqual(m.undo_stack(), [])
        finally:
            m.running_sims, m.warn = old
            w.close()
            w.deleteLater()
            APP.processEvents()


if __name__ == "__main__":
    import unittest
    unittest.main()
