# -*- coding: utf-8 -*-
"""Dossiers de téléchargement : plusieurs dossiers, dossier modifié, archives déjà installées ignorées,
bouton Analyser qui revérifie même les archives déjà proposées."""
import os
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, profile  # noqa: E402

APP = QApplication.instance() or QApplication([])


def zip_profile(folder: Path, name: str, icao: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    arc = folder / name
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr(f"{icao}-demo.ini", profile(icao))
    return arc


class DownloadFoldersTest(SandboxTest):
    def test_defaut_puis_dossiers_choisis(self):
        cfg = m.Config()
        self.assertEqual(cfg.download_dirs(), [m.downloads_dir()])
        other = self.tmp / "D" / "Fichiers"
        cfg.download_folders = [str(m.downloads_dir()), str(other)]
        cfg.save()
        self.assertEqual(m.Config().download_dirs(), [m.downloads_dir(), other])

    def test_plusieurs_dossiers_et_deja_installe(self):
        dl, other = m.downloads_dir(), self.tmp / "D" / "Fichiers"
        a = zip_profile(dl, "ebbr.zip", "ebbr")
        b = zip_profile(other, "lemd.zip", "lemd")
        zip_profile(other, "lfpg.zip", "lfpg")
        found = {p.name for p in m.find_download_archives(set(), [dl, other], installed=["LFPG-demo.ini"])}
        self.assertEqual(found, {"ebbr.zip", "lemd.zip"})           # lfpg déjà dans GSX : ignoré
        self.assertEqual(m.find_download_archives({m.archive_key(a)}, [dl]), [])
        self.assertTrue(m.in_downloads(b, [dl, other]))
        self.assertFalse(m.in_downloads(b, dl))
        self.assertFalse(m.in_downloads(other / "sous" / "x.zip", [other]))
        self.assertEqual(m.cleanup_candidates({a: m.ARCH_OK, b: m.ARCH_OK}, [dl, other]), [a, b])

    def test_fenetre_dossiers(self):
        cfg = m.Config()
        dlg = m.FoldersDialog(cfg, [])
        other = self.tmp / "D" / "Fichiers"
        dlg._set_downloads([str(m.downloads_dir()), str(other), str(other)])     # doublon ignoré
        self.assertTrue(dlg.downloads_changed)
        self.assertEqual(m.Config().download_folders, [os.path.normpath(str(m.downloads_dir())),
                                                       os.path.normpath(str(other))])
        dlg.remove_download(str(other))
        self.assertEqual(m.Config().download_folders, [])                   # retour au dossier par défaut
        dlg._set_downloads([str(other)])
        self.assertEqual(m.Config().download_dirs(), [Path(os.path.normpath(str(other)))])
        dlg.reset_downloads()
        self.assertEqual(m.Config().download_dirs(), [m.downloads_dir()])
        dlg.deleteLater()


if __name__ == "__main__":
    import unittest
    unittest.main()
