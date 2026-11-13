# -*- coding: utf-8 -*-
"""Avions statiques : détection, renommage, variantes, layout.json, cas ambigus."""
import unittest

from helpers import SandboxTest, m, make_pkg, manifest_size, read_layout


class TestStatics(SandboxTest):

    def test_rename_on_off_updates_layout_and_manifest(self):
        root = make_pkg(self.community, "test-ebbr", "Brussels EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 400, True),
            ("scenery/EBBR_airport.bgl", b"A" * 900, True)])
        sc = self.scan()["test-ebbr"]
        self.assertEqual(sc.state, m.ON)
        self.assertEqual(sc.groups[0].mode, "rename")

        m.set_scene_state(sc, m.OFF)
        self.assertTrue((root / "scenery/EBBR_statics.bgl.off").is_file())
        self.assertFalse((root / "scenery/EBBR_statics.bgl").exists())
        self.assertNotIn("scenery/EBBR_statics.bgl", read_layout(root))
        self.assertEqual(manifest_size(root), 900)

        sc = self.scan()["test-ebbr"]
        self.assertEqual(sc.state, m.OFF)
        m.set_scene_state(sc, m.ON)
        self.assertTrue((root / "scenery/EBBR_statics.bgl").is_file())
        self.assertIn("scenery/EBBR_statics.bgl", read_layout(root))
        self.assertEqual(manifest_size(root), 1300)

    def test_variants_copy_chosen_file(self):
        root = make_pkg(self.community, "test-lfpg", "Paris LFPG", [
            ("scenery/statics_on.bgl", b"N" * 500, False),
            ("scenery/statics_off.bgl", b"F" * 120, False),
            ("scenery/statics.bgl", b"N" * 500, True)])
        sc = self.scan()["test-lfpg"]
        self.assertEqual(sc.state, m.ON)
        self.assertEqual(sc.groups[0].mode, "variant")
        m.set_scene_state(sc, m.OFF)
        self.assertEqual((root / "scenery/statics.bgl").read_bytes(), b"F" * 120)
        self.assertEqual(self.scan()["test-lfpg"].state, m.OFF)
        # les deux variantes sont intactes
        self.assertEqual((root / "scenery/statics_on.bgl").read_bytes(), b"N" * 500)

    def test_variant_unknown_active_file(self):
        make_pkg(self.community, "test-x", "Test XXXX", [
            ("s/statics_on.bgl", b"N" * 10, False), ("s/statics_off.bgl", b"F" * 10, False),
            ("s/statics.bgl", b"Z" * 10, True)])
        g = self.scan()["test-x"].groups[0]
        self.assertEqual(g.state, m.UNKNOWN)
        self.assertEqual(g.note, "note_unknown_active")

    def test_unrelated_statics_file_is_never_overwritten(self):
        """Paire on/off sans statics.bgl + autre fichier statics au contenu différent : ambigu, rien ne bouge."""
        root = make_pkg(self.community, "test-ebci", "Charleroi EBCI", [
            ("s/statics_on.bgl", b"N" * 50, False), ("s/statics_off.bgl", b"F" * 20, False),
            ("s/EBCI_statics_vehicles.bgl", b"V" * 30, True)])
        sc = self.scan()["test-ebci"]
        self.assertEqual(sc.state, m.CONFLICT)
        self.assertFalse(sc.toggleable)
        self.assertEqual(sc.groups[0].note, "note_ambiguous_active")
        m.set_scene_state(sc, m.OFF)
        m.set_scene_state(sc, m.ON)
        self.assertEqual((root / "s/EBCI_statics_vehicles.bgl").read_bytes(), b"V" * 30)
        self.assertEqual(sorted(p.name for p in (root / "s").iterdir()),
                         ["EBCI_statics_vehicles.bgl", "statics_off.bgl", "statics_on.bgl"])

    def test_variant_base_with_other_name_is_recognised(self):
        """statics_on/off + EBCI_statics.bgl identique à une variante : bascule normale."""
        root = make_pkg(self.community, "test-ebci2", "Charleroi EBCI", [
            ("s/statics_on.bgl", b"N" * 50, False), ("s/statics_off.bgl", b"F" * 20, False),
            ("s/EBCI_statics.bgl", b"F" * 20, True)])
        sc = self.scan()["test-ebci2"]
        self.assertEqual(sc.state, m.OFF)
        m.set_scene_state(sc, m.ON)
        self.assertEqual((root / "s/EBCI_statics.bgl").read_bytes(), b"N" * 50)
        self.assertEqual(manifest_size(root), 50)

    def test_conflict_is_never_toggled(self):
        root = make_pkg(self.community, "test-lszh", "Zurich LSZH", [
            ("s/LSZH_statics.bgl", b"S" * 10, True), ("s/LSZH_statics.bgl.off", b"T" * 10, False)])
        sc = self.scan()["test-lszh"]
        self.assertEqual(sc.state, m.CONFLICT)
        self.assertFalse(sc.toggleable)
        m.set_scene_state(sc, m.OFF)          # ne doit rien faire
        self.assertTrue((root / "s/LSZH_statics.bgl").is_file())
        self.assertEqual((root / "s/LSZH_statics.bgl.off").read_bytes(), b"T" * 10)

    def test_backup_made_before_change(self):
        make_pkg(self.community, "test-eblg", "Liege EBLG", [("s/EBLG_statics.bgl", b"S" * 10, True)])
        m.set_scene_state(self.scan()["test-eblg"], m.OFF)
        backups = list((self.data / "backups" / "test-eblg").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "layout.json").is_file())

    def test_deep_folders_and_aircraft_skipped(self):
        deep = self.community / "Europe" / "Belgium" / "Liege"
        make_pkg(deep, "test-eblg", "Liege EBLG", [("s/EBLG_statics.bgl", b"S", True)])
        make_pkg(self.community, "test-a320", "A320 Demo", [("statics_x.bgl", b"S", False)], ctype="AIRCRAFT")
        found = self.scan()
        self.assertIn("test-eblg", found)
        self.assertNotIn("test-a320", found)
        self.assertEqual(found["test-eblg"].source, f"{m.MANUAL} › Europe › Belgium › Liege")


if __name__ == "__main__":
    unittest.main()
