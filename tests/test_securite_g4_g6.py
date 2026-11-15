# -*- coding: utf-8 -*-
"""Sécurité G4 à G6 (relecture du gardien de 3AM, 2026-11-15)."""
import io
import zipfile

from helpers import SandboxTest, m, make_pkg


class G4SauvegardesTest(SandboxTest):
    def test_rangees_par_paquet_avec_arborescence(self):
        a = make_pkg(self.community, "pkg-a", "AAAA", [("scenery/x/statics.bgl", b"A1", True),
                                                       ("scenery/y/statics.bgl", b"A2", True)])
        m.backup_files(a, [a / "scenery/x/statics.bgl", a / "scenery/y/statics.bgl"])
        snap = next((self.data / "backups" / "pkg-a").iterdir())
        self.assertEqual((snap / "scenery/x/statics.bgl").read_bytes(), b"A1")    # plus de collision de noms
        self.assertEqual((snap / "scenery/y/statics.bgl").read_bytes(), b"A2")

    def test_annuler_sauvegarde_sous_le_nom_du_paquet(self):
        root = make_pkg(self.community, "pkg-b", "BBBB", [("scenery/BBBB_statics.bgl", b"S" * 9, True)])
        self.assertEqual(m.package_root(root / "scenery/BBBB_statics.bgl"), root)
        with m.undoable("x"):
            m.set_scene_state(self.scan()["pkg-b"], m.OFF)
        m.undo_last()
        self.assertFalse((self.data / "backups" / "scenery").exists())            # plus de dossier « scenery »
        self.assertTrue((self.data / "backups" / "pkg-b").is_dir())


class G5ArchivesTest(SandboxTest):
    def zip(self, files):
        p = self.tmp / "a.zip"
        with zipfile.ZipFile(p, "w") as z:
            for n, d in files.items():
                z.writestr(n, d)
        return p

    def test_trop_de_fichiers_refuse_avant_extraction(self):
        old = m.MAX_ARCHIVE_MEMBERS
        m.MAX_ARCHIVE_MEMBERS = 5
        try:
            arc = self.zip({f"f{i}.txt": b"x" for i in range(6)} | {"ebbr-x.ini": b"[general]"})
            with self.assertRaises(m.ArchiveError):
                m.extract_profiles(arc, self.tmp / "out")
            self.assertFalse((self.tmp / "out" / "ebbr-x.ini").exists())          # rien d'extrait
        finally:
            m.MAX_ARCHIVE_MEMBERS = old

    def test_total_des_profils_plafonne(self):
        old = m.MAX_PROFILE_TOTAL
        m.MAX_PROFILE_TOTAL = 10
        try:
            arc = self.zip({"ebbr-a.ini": b"x" * 8, "ebbr-b.ini": b"y" * 8})
            with self.assertRaises(m.ArchiveError):
                m.extract_profiles(arc, self.tmp / "out")
        finally:
            m.MAX_PROFILE_TOTAL = old

    def test_archive_normale(self):
        arc = self.zip({"GSX/ebbr-a.ini": b"[general]", "readme.txt": b"r"})
        m.extract_profiles(arc, self.tmp / "out")
        self.assertTrue((self.tmp / "out/GSX/ebbr-a.ini").is_file())
        self.assertFalse((self.tmp / "out/readme.txt").exists())


class G6AnnulationTest(SandboxTest):
    def test_fichier_renomme_pas_copie(self):
        root = make_pkg(self.community, "pkg-c", "CCCC", [("scenery/CCCC_statics.bgl", b"S" * 500, True)])
        before = (root / "scenery/CCCC_statics.bgl").read_bytes()
        with m.undoable("x"):
            m.set_scene_state(self.scan()["pkg-c"], m.OFF)
        d = self.data / "undo" / m.undo_stack()[-1]
        self.assertEqual([f.name for f in d.iterdir() if f.name.endswith("statics.bgl")], [])
        rec = __import__("json").loads((d / "undo.json").read_text(encoding="utf-8"))
        self.assertTrue(any(f["path"].endswith("layout.json") and f["copy"] for f in rec["files"]))  # méta copiés
        m.undo_last()
        self.assertEqual((root / "scenery/CCCC_statics.bgl").read_bytes(), before)

    def test_variante_ecrasee_toujours_copiee(self):
        root = make_pkg(self.community, "pkg-d", "DDDD", [
            ("s/statics_on.bgl", b"N" * 50, False), ("s/statics_off.bgl", b"F" * 20, False),
            ("s/statics.bgl", b"N" * 50, True)])
        with m.undoable("x"):
            m.set_scene_state(self.scan()["pkg-d"], m.OFF)
        m.undo_last()                                        # contenu écrasé : retrouvé depuis la variante ON
        self.assertEqual((root / "s/statics.bgl").read_bytes(), b"N" * 50)


if __name__ == "__main__":
    import unittest
    unittest.main()
