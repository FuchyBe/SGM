# -*- coding: utf-8 -*-
"""Restauration de l'état d'origine : statics, layout.json, manifest.json et dossier GSX."""
import json
import unittest

from helpers import SandboxTest, m, make_pkg, profile


def set_version(root, version):
    man = json.loads((root / "manifest.json").read_text())
    man["package_version"] = version
    (root / "manifest.json").write_text(json.dumps(man, indent=2))


class TestRestore(SandboxTest):

    def files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_rename_restored_exactly_after_many_switches(self):
        root = make_pkg(self.community, "test-ebbr", "Brussels EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 400, True), ("scenery/EBBR.bgl", b"A" * 900, True)])
        set_version(root, "1.2.0")
        before = self.files(root)
        for i in range(13):                      # plus que les 10 sauvegardes gardées
            m.set_scene_state(self.scan()["test-ebbr"], m.OFF if i % 2 == 0 else m.ON)
        self.assertTrue((root / "scenery/EBBR_statics.bgl.off").exists())
        self.assertTrue(m.has_origin(root))
        m.restore_scene_statics(root)
        self.assertEqual(self.files(root), before)
        self.assertFalse(m.has_origin(root))

    def test_variant_restores_original_unknown_content(self):
        root = make_pkg(self.community, "test-lfpg", "Paris LFPG", [
            ("s/statics_on.bgl", b"N" * 50, False), ("s/statics_off.bgl", b"F" * 20, False),
            ("s/statics.bgl", b"Z" * 30, True)])
        before = self.files(root)
        m.set_scene_state(self.scan()["test-lfpg"], m.OFF)
        m.set_scene_state(self.scan()["test-lfpg"], m.ON)
        self.assertNotEqual(self.files(root), before)
        m.restore_scene_statics(root)
        self.assertEqual(self.files(root), before)

    def test_file_created_by_sgm_is_removed(self):
        root = make_pkg(self.community, "test-x", "Test XXXX", [
            ("s/statics_on.bgl", b"N" * 5, False), ("s/statics_off.bgl", b"F" * 5, False)])
        before = self.files(root)
        m.set_scene_state(self.scan()["test-x"], m.ON)
        self.assertTrue((root / "s/statics.bgl").exists())
        m.restore_scene_statics(root)
        self.assertEqual(self.files(root), before)

    def test_unknown_file_blocks_restore_and_nothing_changes(self):
        root = make_pkg(self.community, "test-y", "Test YYYY", [("s/y_statics.bgl", b"S" * 5, True)])
        m.set_scene_state(self.scan()["test-y"], m.OFF)
        (root / "s/y_statics.bgl.off").write_bytes(b"edited by user")
        before = self.files(root)
        with self.assertRaises(m.RestoreError) as ctx:
            m.restore_scene_statics(root)
        self.assertIn("s/y_statics.bgl", str(ctx.exception))
        self.assertEqual(self.files(root), before)     # tout ou rien
        self.assertTrue(m.has_origin(root))            # la photo est gardée

    def test_scenery_updated_by_developer_is_not_touched(self):
        root = make_pkg(self.community, "test-z", "Test ZZZZ", [("s/z_statics.bgl", b"S" * 5, True)])
        set_version(root, "1.0.0")
        m.set_scene_state(self.scan()["test-z"], m.OFF)
        set_version(root, "1.1.0")
        (root / "s/z_statics.bgl.off").rename(root / "s/z_statics.bgl")
        with self.assertRaises(m.RestoreError):
            m.restore_scene_statics(root)
        self.assertTrue((root / "s/z_statics.bgl").exists())
        self.assertFalse(m.has_origin(root))

    def test_snapshot_taken_only_once(self):
        root = make_pkg(self.community, "test-w", "Test WWWW", [("s/w_statics.bgl", b"S" * 5, True)])
        m.set_scene_state(self.scan()["test-w"], m.OFF)
        first = (m.origin_dir(root) / "origin.json").read_text()
        m.set_scene_state(self.scan()["test-w"], m.ON)
        m.set_scene_state(self.scan()["test-w"], m.OFF)
        self.assertEqual((m.origin_dir(root) / "origin.json").read_text(), first)

    def test_gsx_restore_puts_back_replaced_and_removes_added(self):
        make_pkg(self.community, "test-eblg", "Liege EBLG", [
            ("GSX/eblg-x.ini", profile("scene"), False), ("GSX/eblg-x.py", b"# scene", False)])
        (self.gsx / "eblg-x.ini").write_bytes(profile("mine"))
        (self.gsx / "other.ini").write_bytes(profile("untouched"))
        sc = self.scan()["test-eblg"]
        m.copy_gsx(sc, sc.gsx_variants[0], self.gsx)
        m.copy_gsx(sc, sc.gsx_variants[0], self.gsx)   # deuxième copie : l'origine reste la première
        self.assertEqual((self.gsx / "eblg-x.ini").read_bytes(), profile("scene"))
        self.assertTrue(m.gsx_has_origin(self.gsx, ["eblg-x.ini"]))
        self.assertEqual(m.gsx_restore(self.gsx, ["eblg-x.ini", "eblg-x.py"]), 2)
        self.assertEqual((self.gsx / "eblg-x.ini").read_bytes(), profile("mine"))
        self.assertFalse((self.gsx / "eblg-x.py").exists())
        self.assertEqual((self.gsx / "other.ini").read_bytes(), profile("untouched"))
        self.assertEqual(m.gsx_journal_dests(), [])

    def test_restore_all_lists_every_scene(self):
        for n in ("a", "b"):
            make_pkg(self.community, f"test-{n}", n, [("s/x_statics.bgl", b"S", True)])
            m.set_scene_state(self.scan()[f"test-{n}"], m.OFF)
        self.assertEqual(sorted(p.name for p in m.origin_roots()), ["test-a", "test-b"])


if __name__ == "__main__":
    unittest.main()
