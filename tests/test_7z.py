# -*- coding: utf-8 -*-
"""Archives .7z (et .rar, même chemin de code : 7-Zip) avec un vrai 7-Zip. Ignoré si 7-Zip est absent.
Sur GitHub (ubuntu-latest), 7-Zip est installé : ces tests y tournent toujours."""
import shutil
import subprocess
import unittest

from helpers import SandboxTest, m, profile

SEVEN = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")


@unittest.skipUnless(SEVEN, "7-Zip absent")
class SevenZipTest(SandboxTest):
    def make_7z(self, files: dict) -> m.Path:
        src = self.tmp / "src"
        for name, data in files.items():
            f = src / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        arc = self.tmp / "dl" / "profils.7z"
        arc.parent.mkdir(exist_ok=True)
        subprocess.run([SEVEN, "a", "-y", str(arc), "."], cwd=src, capture_output=True, check=True)
        return arc

    def test_extraction_profils_uniquement(self):
        arc = self.make_7z({"EBBR/ebbr-demo.ini": profile("ebbr"), "EBBR/ebbr-demo.py": b"# py",
                            "readme.txt": b"r", "textures/a.dds": b"x" * 100})
        out = self.tmp / "out"
        out.mkdir()
        m.extract_profiles(arc, out)
        got = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        self.assertEqual(got, ["EBBR/ebbr-demo.ini", "EBBR/ebbr-demo.py"])

    def test_profil_trop_gros_archive_refusee(self):
        """7-Zip extrairait le fichier avant le garde-fou : l'archive est refusée d'avance (sécurité)."""
        old = m.MAX_MEMBER_SIZE
        m.MAX_MEMBER_SIZE = 50
        try:
            arc = self.make_7z({"ebbr-a.ini": profile("a"), "ebbr-big.ini": b"[general]\n" + b"x" * 200})
            out = self.tmp / "out"
            out.mkdir()
            with self.assertRaises(m.ArchiveError):
                m.extract_profiles(arc, out)
            self.assertEqual(list(out.rglob("*")), [])
        finally:
            m.MAX_MEMBER_SIZE = old

    def test_plafonds_avant_extraction(self):
        old = m.MAX_ARCHIVE_MEMBERS
        m.MAX_ARCHIVE_MEMBERS = 3
        try:
            arc = self.make_7z({f"f{i}.txt": b"x" for i in range(5)} | {"ebbr-a.ini": profile("a")})
            out = self.tmp / "out"
            out.mkdir()
            with self.assertRaises(m.ArchiveError):
                m.extract_profiles(arc, out)
            self.assertEqual(list(out.rglob("*")), [])
        finally:
            m.MAX_ARCHIVE_MEMBERS = old

    def test_liste_et_detection_dans_telechargements(self):
        arc = self.make_7z({"GSX/lemd-x.ini": profile("lemd")})
        names = [n.replace("\\", "/") for n in m._names_in_archive(arc)]
        self.assertIn("GSX/lemd-x.ini", names)
        self.assertEqual(m.find_download_archives(set(), [arc.parent]), [arc])
        self.assertEqual([n for n, _s in m._list_7z(SEVEN, arc) if n.endswith(".ini")][0].replace("\\", "/"),
                         "GSX/lemd-x.ini")

    def test_installation_complete_depuis_un_7z(self):
        arc = self.make_7z({"lfpg-x.ini": profile("lfpg")})
        tmp = self.tmp / "ext"
        tmp.mkdir()
        m.extract_profiles(arc, tmp)
        variants = m.profiles_in_folder(tmp)
        self.assertTrue(variants)
        m.install_profile_files(variants[0].files, self.gsx)
        self.assertEqual((self.gsx / "lfpg-x.ini").read_bytes(), profile("lfpg"))


class SansSevenZipTest(SandboxTest):
    def test_message_clair_si_7zip_absent(self):
        arc = self.tmp / "a.7z"
        arc.write_bytes(b"7z")
        old = m.find_7z
        m.find_7z = lambda: None
        try:
            with self.assertRaises(m.ArchiveError) as ctx:
                m.extract_profiles(arc, self.tmp)
            self.assertEqual(ctx.exception.key, "arch_need_7z")
            self.assertEqual(m._names_in_archive(arc), [])
        finally:
            m.find_7z = old


if __name__ == "__main__":
    unittest.main()
