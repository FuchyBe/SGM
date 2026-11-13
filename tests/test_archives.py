# -*- coding: utf-8 -*-
"""Installation de profils depuis une archive : sécurité, versions, détection dans Téléchargements."""
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from helpers import SandboxTest, m, profile


class TestArchives(SandboxTest):

    def downloads(self) -> Path:
        return self.tmp / "home" / "Downloads"

    def test_safe_extraction(self):
        evil = self.tmp / "evil.zip"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("../../escape.ini", profile("x"))
            z.writestr("/abs/abs.ini", profile("y"))
            z.writestr("C:/win/c.ini", profile("z"))
            z.writestr("big/eddf-big.ini", b"[section.1]\n" + b"x" * (5 * 1024 * 1024))
            z.writestr("ok/eddf-ok.ini", profile("ok"))
            z.writestr("run.exe", b"MZ")
        out = Path(tempfile.mkdtemp(dir=self.tmp))
        m.extract_profiles(evil, out)
        files = sorted(str(p.relative_to(out)).replace("\\", "/") for p in out.rglob("*") if p.is_file())
        self.assertEqual(files, ["abs/abs.ini", "ok/eddf-ok.ini"])
        self.assertFalse((self.tmp / "escape.ini").exists())
        self.assertFalse(Path("/abs/abs.ini").exists())

    def test_versions_in_archive(self):
        arc = self.tmp / "LEMD_GSX.zip"
        with zipfile.ZipFile(arc, "w") as z:
            z.writestr("LEMD GSX/FULL - VDGS/lemd-x.ini", profile("full"))
            z.writestr("LEMD GSX/FULL - VDGS/lemd-x.py", b"# py")
            z.writestr("LEMD GSX/LITE/lemd-x.ini", profile("lite"))
            z.writestr("LEMD GSX/readme.txt", b"hi")
        out = Path(tempfile.mkdtemp(dir=self.tmp))
        m.extract_profiles(arc, out)
        vs = m.profiles_in_folder(out)
        self.assertEqual([len(v.files) for v in vs], [2, 1])
        self.assertEqual(m.icaos_of([f for v in vs for f in v.files]), {"LEMD"})
        copied = m.install_profile_files(vs[1].files, self.gsx)
        self.assertEqual(copied, ["lemd-x.ini"])

    def test_broken_archive_raises(self):
        bad = self.tmp / "broken.zip"
        bad.write_bytes(b"not a zip")
        with self.assertRaises(m.ArchiveError) as ctx:
            m.extract_profiles(bad, Path(tempfile.mkdtemp(dir=self.tmp)))
        self.assertEqual(ctx.exception.key, "arch_error")

    def test_rar_without_7zip(self):
        if m.find_7z():
            self.skipTest("7-Zip installé sur cette machine")
        with self.assertRaises(m.ArchiveError) as ctx:
            m.extract_profiles(self.tmp / "x.rar", Path(tempfile.mkdtemp(dir=self.tmp)))
        self.assertEqual(ctx.exception.key, "arch_need_7z")

    def test_downloads_detection(self):
        dl = self.downloads()
        with zipfile.ZipFile(dl / "LOWW_gsx.zip", "w") as z:
            z.writestr("loww-x.ini", profile("a"))
        with zipfile.ZipFile(dl / "livery.zip", "w") as z:
            z.writestr("aircraft.cfg", b"x")
        old = dl / "old_gsx.zip"
        with zipfile.ZipFile(old, "w") as z:
            z.writestr("gsx/egll-x.ini", profile("o"))
        os.utime(old, (time.time() - 90 * 86400,) * 2)
        self.assertEqual(m.downloads_dir(), dl)
        found = [p.name for p in m.find_download_archives(set())]
        self.assertEqual(found, ["LOWW_gsx.zip"])
        seen = {m.archive_key(dl / "LOWW_gsx.zip")}
        self.assertEqual(m.find_download_archives(seen), [])


if __name__ == "__main__":
    unittest.main()
