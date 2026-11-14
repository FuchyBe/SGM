# -*- coding: utf-8 -*-
"""Suppression des archives de profils GSX après installation (Corbeille), jamais en cas d'erreur."""
import os
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, profile  # noqa: E402

APP = QApplication.instance() or QApplication([])


class TestArchiveCleanup(SandboxTest):

    def setUp(self):
        super().setUp()
        self.dl = self.tmp / "home" / "Downloads"
        self.dl.mkdir(parents=True, exist_ok=True)

    def zip_profile(self, folder: Path, name: str, icao="ebbr") -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        arc = folder / name
        with zipfile.ZipFile(arc, "w") as z:
            z.writestr(f"{icao} GSX/{icao}-x.ini", profile(icao))
        return arc

    def broken(self, name: str) -> Path:
        arc = self.dl / name
        arc.write_bytes(b"not a zip")
        return arc

    # ── moteur
    def test_candidates_only_ok_and_in_downloads(self):
        ok_dl = self.zip_profile(self.dl, "ok.zip")
        ok_other = self.zip_profile(self.tmp / "elsewhere", "ok2.zip")
        err_dl = self.broken("bad.zip")
        cancel_dl = self.zip_profile(self.dl, "cancel.zip", "lfpg")
        out = m.cleanup_candidates({ok_dl: m.ARCH_OK, ok_other: m.ARCH_OK, err_dl: m.ARCH_ERROR,
                                    cancel_dl: m.ARCH_CANCEL}, self.dl)
        self.assertEqual(out, [ok_dl])

    def test_send_to_trash_is_recoverable(self):
        arc = self.zip_profile(self.dl, "ok.zip")
        m.send_to_trash(arc)
        self.assertFalse(arc.exists())
        self.assertTrue((self.data / "trash" / "ok.zip").is_file())      # hors Windows : SGM_data/trash
        failed = m.trash_archives([arc])                                 # déjà partie : échec signalé
        self.assertEqual([n for n, _err in failed], ["ok.zip"])

    # ── parcours dans la fenêtre
    def window(self, mode):
        w = m.MainWindow()
        w.config.archive_cleanup = mode
        self.asked, self.warned = [], []
        m.ask = lambda _p, msg, **k: (self.asked.append(msg), True)[1]
        m.warn = lambda _p, msg: self.warned.append(msg)
        return w

    def test_auto_deletes_installed_and_keeps_errors(self):
        orig_ask, orig_warn = m.ask, m.warn
        try:
            w = self.window("auto")
            good = self.zip_profile(self.dl, "EBBR_GSX.zip")
            bad = self.broken("LFPG_GSX.zip")
            other = self.zip_profile(self.tmp / "elsewhere", "EHAM_GSX.zip", "eham")
            w.install_paths([good, bad, other])
            self.assertTrue((self.gsx / "ebbr-x.ini").is_file())
            self.assertTrue((self.gsx / "eham-x.ini").is_file())
            self.assertFalse(good.exists())                     # installée depuis Téléchargements : à la Corbeille
            self.assertTrue(bad.exists())                       # erreur : jamais supprimée
            self.assertTrue(other.exists())                     # hors Téléchargements : jamais supprimée
            self.assertTrue(any("LFPG_GSX.zip" in x for x in self.warned))   # alerte
            w.close()
        finally:
            m.ask, m.warn = orig_ask, orig_warn

    def test_ask_mode_asks_and_never_mode_keeps(self):
        orig_ask, orig_warn = m.ask, m.warn
        try:
            w = self.window("ask")
            good = self.zip_profile(self.dl, "EBBR_GSX.zip")
            w.install_paths([good])
            self.assertTrue(any("EBBR_GSX.zip" in x for x in self.asked))
            self.assertFalse(good.exists())
            w.config.archive_cleanup = "never"
            again = self.zip_profile(self.dl, "EBBR_GSX_again.zip")
            w.install_paths([again])                            # déjà installé à l'identique : succès
            self.assertTrue(again.exists())                     # « jamais » : on garde
            w.close()
        finally:
            m.ask, m.warn = orig_ask, orig_warn

    def test_already_installed_counts_as_success(self):
        orig_ask, orig_warn = m.ask, m.warn
        try:
            w = self.window("auto")
            first = self.zip_profile(self.dl, "a.zip")
            w.install_paths([first])
            second = self.zip_profile(self.dl, "b.zip")
            self.asked.clear()
            w.install_paths([second])
            self.assertFalse(second.exists())
            self.assertEqual(self.asked, [])                    # rien à confirmer : déjà installé
            w.close()
        finally:
            m.ask, m.warn = orig_ask, orig_warn


if __name__ == "__main__":
    unittest.main()
