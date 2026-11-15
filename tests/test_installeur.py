# -*- coding: utf-8 -*-
"""Version installable (v1.0) : mode installé, reprise des données portables, mise à jour, installeur."""
import os
import re
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import ROOT, SandboxTest, m  # noqa: E402

APP = QApplication.instance() or QApplication([])


def portable(base: Path) -> Path:
    """Fausse version portable : SGM.exe + SGM_data complet."""
    (base / "SGM.exe").parent.mkdir(parents=True, exist_ok=True)
    (base / "SGM.exe").write_bytes(b"MZ")
    d = base / "SGM_data"
    for rel, data in (("config.json", '{"version": 3, "lang": "fr", "sim": "MSFS 2024"}'),
                      ("backups/ebbr-123456/scenery/EBBR_statics.bgl", "S"),
                      ("origin/abc/origin.json", '{"root": "D:/Community/ebbr"}'),
                      ("undo/stack.json", "[]"),
                      ("logs/sgm.log", "journal"),
                      ("update/0.9.3/SGM_beta_v0.9.3.zip", "zip")):
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")
    return base


class InstallModeTest(SandboxTest):
    def test_mode_installe_donnees_dans_appdata(self):
        app = self.tmp / "Programs" / "SGM"
        app.mkdir(parents=True)
        (app / m.INSTALL_MARKER).write_text("x")
        old = m._DATA_DIR
        try:
            m._DATA_DIR = None
            with mock.patch.object(m, "app_dir", return_value=app):
                self.assertTrue(m.is_installed())
                d = m.data_dir()
            self.assertEqual(d, self.tmp / "roaming" / "SGM")
            self.assertFalse((app / "SGM_data").exists())          # jamais de données dans le dossier du programme
        finally:
            m._DATA_DIR = old

    def test_mode_portable_inchange(self):
        app = self.tmp / "SGM"
        app.mkdir()
        old = m._DATA_DIR
        try:
            m._DATA_DIR = None
            with mock.patch.object(m, "app_dir", return_value=app):
                self.assertFalse(m.is_installed())
                self.assertEqual(m.data_dir(), app / "SGM_data")
        finally:
            m._DATA_DIR = old

    def test_trouver_les_donnees_portables(self):
        base = portable(self.tmp / "Outils" / "SGM")
        want = base / "SGM_data"
        for f in (base, want):
            self.assertEqual(m.find_portable_data(f), want)
        self.assertIsNone(m.find_portable_data(self.tmp / "Outils"))
        self.assertIsNone(m.find_portable_data(self.tmp / "absent"))

    def test_reprise_copie_sans_toucher_la_source(self):
        base = portable(self.tmp / "Outils" / "SGM")
        src = base / "SGM_data"
        before = {p.relative_to(src): p.read_bytes() for p in src.rglob("*") if p.is_file()}
        dst = self.tmp / "roaming" / "SGM"
        n = m.import_portable(src, dst)
        self.assertEqual(n, 5)                                      # le dossier update/ n'est pas repris
        self.assertFalse((dst / "update").exists())
        for rel in ("config.json", "backups/ebbr-123456/scenery/EBBR_statics.bgl", "origin/abc/origin.json",
                    "undo/stack.json", "logs/sgm.log"):
            self.assertEqual((dst / rel).read_bytes(), (src / rel).read_bytes())
        after = {p.relative_to(src): p.read_bytes() for p in src.rglob("*") if p.is_file()}
        self.assertEqual(before, after)                             # la version portable n'est pas modifiée
        self.assertFalse(any(p.name.endswith(".import-tmp") for p in dst.parent.iterdir()))

    def test_reprise_remplace_et_garde_le_reste(self):
        src = portable(self.tmp / "P")/ "SGM_data"
        dst = self.tmp / "roaming" / "SGM"
        (dst / "profiles").mkdir(parents=True)
        (dst / "config.json").write_text("{}")
        (dst / "profiles" / "a.txt").write_text("a")
        m.import_portable(src, dst)
        self.assertIn("fr", (dst / "config.json").read_text())
        self.assertTrue((dst / "profiles" / "a.txt").is_file())

    def test_reprise_refuse_le_meme_dossier(self):
        src = portable(self.tmp / "P") / "SGM_data"
        with self.assertRaises(ValueError):
            m.import_portable(src, src)
        with self.assertRaises(ValueError):
            m.import_portable(src, src / "sous")

    def test_reprise_echec_ne_change_rien(self):
        src = portable(self.tmp / "P") / "SGM_data"
        dst = self.tmp / "roaming" / "SGM"
        dst.mkdir(parents=True)
        (dst / "config.json").write_text("{}")
        real = m.shutil.copy2
        calls = []

        def boom(a, b, *k, **kw):
            calls.append(a)
            if len(calls) == 3:
                raise OSError("disque plein")
            return real(a, b, *k, **kw)
        with mock.patch.object(m.shutil, "copy2", boom):
            with self.assertRaises(OSError):
                m.import_portable(src, dst)
        self.assertEqual((dst / "config.json").read_text(), "{}")    # rien de changé
        self.assertEqual(sorted(p.name for p in dst.iterdir()), ["config.json"])

    def test_fenetre_bandeau_et_menu(self):
        app = self.tmp / "Programs" / "SGM"
        app.mkdir(parents=True)
        (app / m.INSTALL_MARKER).write_text("x")
        with mock.patch.object(m, "app_dir", return_value=app), mock.patch.object(m, "FRESH_DATA", True):
            w = m.MainWindow()
            try:
                self.assertFalse(w.imp_banner.isHidden())
                keys = [a.data() for a in w.menuBar().actions()[0].menu().actions()]
                self.assertIn("m_import", keys)
                base = portable(self.tmp / "Outils" / "SGM")
                w.set_busy(True)                                    # premier lancement : l'analyse tourne
                with mock.patch.object(m.QFileDialog, "getExistingDirectory", return_value=str(base)) as dlg, \
                        mock.patch.object(m.QMessageBox, "information"):
                    w.import_from_portable(False)                   # clic sur « Reprendre… » (signal clicked)
                    self.assertEqual(dlg.call_count, 1)             # le dossier se choisit même pendant l'analyse
                    self.assertNotEqual(m.Config().lang, "fr")      # copie en attente
                    w.set_busy(False)
                    APP.processEvents()
                self.assertEqual(m.Config().lang, "fr")              # données reprises et rechargées
            finally:
                for x in APP.topLevelWidgets():
                    if isinstance(x, m.MainWindow):
                        x.close()
                        x.deleteLater()
                APP.processEvents()
                m.set_lang("en")
                m.close_logging()
        w = m.MainWindow()                                          # version portable : ni bandeau ni menu
        self.assertTrue(w.imp_banner.isHidden())
        self.assertNotIn("m_import", [a.data() for a in w.menuBar().actions()[0].menu().actions()])
        w.close()
        w.deleteLater()
        APP.processEvents()


class InstallUpdateTest(SandboxTest):
    def test_script_met_a_jour_la_version_affichee(self):
        src = self.tmp / "new"
        src.mkdir()
        (src / "SGM.exe").write_bytes(b"MZ")
        s = m.updater_script(src, self.tmp / "app", 1, self.tmp / "bak", self.tmp / "log", reg_version="1.0")
        self.assertIn(f"Uninstall\\{m.INSTALL_APP_ID}_is1", s)
        self.assertIn('/v DisplayVersion /t REG_SZ /d "1.0" /f', s)
        self.assertNotIn("reg add", m.updater_script(src, self.tmp / "app", 1, self.tmp / "bak", self.tmp / "log"))
        s = m.updater_script(src, self.tmp / "app", 1, self.tmp / "bak", self.tmp / "log", reg_version='1.0" & del x')
        self.assertIn('/d "1.0" /f', s)                             # seulement des chiffres et des points

    def test_release_avec_installeur_et_sha256sums(self):
        pre = m.DOWNLOAD_PREFIX + "v1.0/"
        data = {"tag_name": "v1.0", "assets": [
            {"name": "SGM_beta_v1.0.zip", "browser_download_url": pre + "SGM_beta_v1.0.zip", "size": 10},
            {"name": "SGM_Setup_v1.0.exe", "browser_download_url": pre + "SGM_Setup_v1.0.exe", "size": 10},
            {"name": "SHA256SUMS.txt", "browser_download_url": pre + "SHA256SUMS.txt", "size": 1}]}
        info = m.release_info(data)
        self.assertEqual(info["zip_name"], "SGM_beta_v1.0.zip")      # l'installeur n'est jamais pris pour le zip
        self.assertTrue(info["sha_url"].endswith("SHA256SUMS.txt"))
        sums = f"{'a' * 64}  SGM_beta_v1.0.zip\n{'b' * 64}  SGM_Setup_v1.0.exe\n"
        self.assertEqual(m.expected_sha256(sums, "SGM_beta_v1.0.zip"), "a" * 64)


class InstallerScriptTest(SandboxTest):
    def test_script_inno_setup(self):
        iss = (ROOT / "installer" / "SGM.iss").read_text(encoding="utf-8")
        self.assertIn("PrivilegesRequired=lowest", iss)              # pas de demande administrateur
        self.assertIn(r"DefaultDirName={localappdata}\Programs\SGM", iss)
        self.assertIn("DisableDirPage=yes", iss)                      # le dossier effacé à la désinstallation est fixe
        app_id = re.search(r"AppId=\{(\{[0-9A-F-]+\})", iss).group(1)
        self.assertEqual(app_id, m.INSTALL_APP_ID)
        self.assertIn('Source: "SGM.installed"', iss)
        self.assertTrue((ROOT / "installer" / m.INSTALL_MARKER).is_file())
        self.assertIn('Excludes: "SGM_data\\*"', iss)               # jamais de données portables dans l'installeur
        self.assertIn("MB_DEFBUTTON2", iss)                           # données gardées par défaut
        self.assertIn(r"{userappdata}\SGM", iss)
        langs = re.findall(r'^Name: "(\w+)"; MessagesFile', iss, re.M)
        for lang in langs:
            self.assertIn(f"{lang}.DeleteData=", iss)
