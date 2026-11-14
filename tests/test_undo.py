# -*- coding: utf-8 -*-
"""Annuler la dernière action : retour exact à l'état d'avant, pour chaque méthode, tout ou rien."""
import json

from helpers import SandboxTest, make_pkg, m, profile


class UndoTest(SandboxTest):
    def files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def toggle_and_undo(self, folder, root, target):
        before = self.files(root)
        with m.undoable(f"Statics {target} — {folder}"):
            m.set_scene_state(self.scan()[folder], target)
        self.assertNotEqual(self.files(root), before)
        self.assertEqual(m.undo_label(), f"Statics {target} — {folder}")
        self.assertEqual(m.undo_last(), f"Statics {target} — {folder}")
        self.assertEqual(self.files(root), before)
        self.assertEqual(m.undo_stack(), [])

    def test_renommage(self):
        root = make_pkg(self.community, "test-ebbr", "EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 400, True), ("scenery/EBBR.bgl", b"A" * 900, True)])
        self.toggle_and_undo("test-ebbr", root, m.OFF)

    def test_variante(self):
        root = make_pkg(self.community, "test-lfpg", "LFPG", [
            ("s/statics_on.bgl", b"N" * 50, False), ("s/statics_off.bgl", b"F" * 20, False),
            ("s/statics.bgl", b"N" * 50, True)])
        self.toggle_and_undo("test-lfpg", root, m.OFF)

    def test_methode_officielle_et_layout(self):
        d = "scenery/world/scenery"
        root = make_pkg(self.community, "orbx-airport-lyni-nis", "LYNI", [
            (f"{d}/lyni_place.bgl", b"WITH" * 50, True), (f"{d}/lyni_place.bgl.nostatic", b"NO" * 40, False)])
        (root / "layout.json.nostatic").write_text((root / "layout.json").read_text())
        self.toggle_and_undo("orbx-airport-lyni-nis", root, m.OFF)

    def test_staticq_et_paire(self):
        d = "scenery/UK2000Scenery/scenery"
        root = make_pkg(self.community, "uk2000-khnd", "KHND", [
            (f"{d}/khnd-airport.bgl", b"NO" * 200, True), (f"{d}/khnd-airport.bgl.staticq", b"WITH" * 100, False)])
        self.toggle_and_undo("uk2000-khnd", root, m.ON)
        d = "Scenery/x/scene"
        root = make_pkg(self.community, "inibuilds-airport-kpvd", "KPVD", [
            (f"{d}/kpvd-scene-airport_nostatic.bgl", b"N" * 180, True),
            (f"{d}/kpvd-scene-airport_static.bgl.disabled", b"S" * 181, False)])
        self.toggle_and_undo("inibuilds-airport-kpvd", root, m.ON)

    def test_gros_fichier_retrouve_par_empreinte(self):
        old = m.UNDO_COPY_MAX
        m.UNDO_COPY_MAX = 10                        # pas de copie : retrouvé après renommage
        try:
            root = make_pkg(self.community, "test-big", "EBBR", [("scenery/EBBR_statics.bgl", b"S" * 400, True)])
            self.toggle_and_undo("test-big", root, m.OFF)
        finally:
            m.UNDO_COPY_MAX = old

    def test_tout_off_en_une_action(self):
        a = make_pkg(self.community, "a", "AAAA", [("s/AAAA_statics.bgl", b"S" * 40, True)])
        b = make_pkg(self.community, "b", "BBBB", [("s/BBBB_statics.bgl", b"T" * 40, True)])
        before = (self.files(a), self.files(b))
        with m.undoable("Tout OFF"):
            for k in ("a", "b"):
                m.set_scene_state(self.scan()[k], m.OFF)
        self.assertEqual(len(m.undo_stack()), 1)
        m.undo_last()
        self.assertEqual((self.files(a), self.files(b)), before)

    def test_profils_gsx(self):
        (self.gsx / "ebbr-old.ini").write_bytes(profile("old"))
        before = self.files(self.gsx)
        src = self.tmp / "dl"
        src.mkdir()
        (src / "ebbr-new.ini").write_bytes(profile("new"))
        (src / "ebbr-old.ini").write_bytes(profile("remplacé"))
        with m.undoable("GSX"):
            m.install_profile_files([src / "ebbr-new.ini", src / "ebbr-old.ini"], self.gsx)
        self.assertNotEqual(self.files(self.gsx), before)
        m.undo_last()
        self.assertEqual(self.files(self.gsx), before)

    def test_refus_si_modifie_depuis(self):
        root = make_pkg(self.community, "test-ebbr", "EBBR", [("scenery/EBBR_statics.bgl", b"S" * 40, True)])
        with m.undoable("x"):
            m.set_scene_state(self.scan()["test-ebbr"], m.OFF)
        (root / "scenery/EBBR_statics.bgl.off").write_bytes(b"modifie a la main")
        snap = self.files(root)
        with self.assertRaises(m.UndoError):
            m.undo_last()
        self.assertEqual(self.files(root), snap)              # rien touché
        self.assertEqual(len(m.undo_stack()), 1)

    def test_pile_limitee_et_action_sans_effet(self):
        root = make_pkg(self.community, "test-ebbr", "EBBR", [("scenery/EBBR_statics.bgl", b"S" * 40, True)])
        with m.undoable("rien"):
            pass
        self.assertEqual(m.undo_stack(), [])
        for i in range(m.UNDO_MAX + 3):
            with m.undoable(f"n{i}"):
                m.set_scene_state(self.scan()["test-ebbr"], m.OFF if i % 2 == 0 else m.ON)
        self.assertEqual(len(m.undo_stack()), m.UNDO_MAX)
        self.assertEqual(len([d for d in (self.data / "undo").iterdir() if d.is_dir()]), m.UNDO_MAX)
        self.assertEqual(m.undo_label(), f"n{m.UNDO_MAX + 2}")
        # annuler plusieurs fois de suite : chaque action à rebours
        state = lambda: self.scan()["test-ebbr"].state
        cur = state()
        m.undo_last()
        self.assertNotEqual(state(), cur)
        m.undo_last()
        self.assertEqual(state(), cur)

    def test_restauration_origine_annulable(self):
        root = make_pkg(self.community, "test-ebbr", "EBBR", [("scenery/EBBR_statics.bgl", b"S" * 40, True)])
        m.set_scene_state(self.scan()["test-ebbr"], m.OFF)
        after_off = self.files(root)
        with m.undoable("restaurer"):
            m.restore_scene_statics(root)
        m.undo_last()
        self.assertEqual(self.files(root), after_off)

    def test_rien_a_annuler(self):
        with self.assertRaises(m.UndoError):
            m.undo_last()


if __name__ == "__main__":
    import unittest
    unittest.main()
