# -*- coding: utf-8 -*-
"""Mise à jour automatique : versions, release GitHub, empreinte SHA-256, extraction sûre, script, interface.
Aucun accès réseau : les téléchargements sont simulés."""
import hashlib
import io
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m  # noqa: E402

APP = QApplication.instance() or QApplication([])
DL = "https://github.com/FuchyBe/SGM/releases/download/v9.9/"


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def release(**kw):
    data = {"tag_name": "v9.9", "draft": False, "prerelease": False, "body": "**Nouveau**", "html_url": "https://x",
            "assets": [{"name": "SGM_beta_v9.9.zip", "browser_download_url": DL + "SGM_beta_v9.9.zip", "size": 10},
                       {"name": "SGM_beta_v9.9.zip.sha256", "browser_download_url": DL + "SGM_beta_v9.9.zip.sha256"}]}
    data.update(kw)
    return data


class UpdateEngineTest(SandboxTest):
    def test_versions(self):
        self.assertEqual(m.parse_version("beta v0.10"), (0, 10))
        self.assertTrue(m.is_newer("v0.10", "0.9"))
        self.assertTrue(m.is_newer("0.8.1", "0.8"))
        self.assertFalse(m.is_newer("0.8", "0.8.0"))
        self.assertFalse(m.is_newer("v0.7", "0.8"))
        self.assertFalse(m.is_newer("nightly", "0.8"))

    def test_quand_verifier(self):
        self.assertFalse(m.should_check_updates(None, 0))          # pas encore demandé
        self.assertFalse(m.should_check_updates(False, 0))
        self.assertTrue(m.should_check_updates(True, 0, now=10 ** 9))
        self.assertFalse(m.should_check_updates(True, 10 ** 9 - 3600, now=10 ** 9))   # une fois par jour

    def test_release_filtree(self):
        info = m.release_info(release())
        self.assertEqual((info["version"], info["zip_name"]), ("9.9", "SGM_beta_v9.9.zip"))
        self.assertTrue(info["sha_url"].endswith(".sha256"))
        self.assertIsNone(m.release_info(release(draft=True)))
        self.assertIsNone(m.release_info(release(prerelease=True)))
        evil = release(assets=[{"name": "SGM_beta_v9.9.zip", "browser_download_url": "https://evil.example/SGM.zip"}])
        self.assertIsNone(m.release_info(evil))                      # téléchargement hors du dépôt : refusé
        self.assertIsNone(m.release_info(release(assets=[])))

    def test_fetch_sans_reseau(self):
        import json
        info = m.fetch_latest_release(lambda url, *a: json.dumps(release()).encode())
        self.assertEqual(info["version"], "9.9")
        with self.assertRaises(m.UpdateError):
            m.fetch_latest_release(lambda url, *a: b"pas du json")

    def test_aucune_release_publiee_404(self):
        import urllib.error

        def g404(url, *a):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        def g500(url, *a):
            raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)
        self.assertIsNone(m.fetch_latest_release(g404))       # brouillon seulement : « à jour », pas une erreur
        with self.assertRaises(m.UpdateError):
            m.fetch_latest_release(g500)

    def test_script_chemins_speciaux(self):
        src = self.tmp / "new"
        (src / "_internal").mkdir(parents=True)
        (src / "SGM.exe").write_bytes(b"E")
        s = m.updater_script(src, m.Path("C:/Jeux/A&B/50%"), 42, self.tmp / "bak", self.tmp / "log")
        self.assertIn('set "DST=C:/Jeux/A&B/50%%"', s)          # % doublé, & entre guillemets
        self.assertIn('/FI "PID eq 42" /FI "IMAGENAME eq SGM.exe"', s)

    def test_plusieurs_zip_dans_la_release(self):
        two = release(assets=release()["assets"] + [
            {"name": "SGM-v9.9-source.zip", "browser_download_url": DL + "SGM-v9.9-source.zip"}])
        self.assertEqual(m.release_info(two)["zip_name"], "SGM_beta_v9.9.zip")
        amb = release(assets=[{"name": "SGM-a.zip", "browser_download_url": DL + "SGM-a.zip"},
                              {"name": "SGM-b.zip", "browser_download_url": DL + "SGM-b.zip"}])
        self.assertIsNone(m.release_info(amb))                 # deux paquets possibles : on n'en choisit aucun
        dots = release(assets=[{"name": "SGM_beta_v9.9.zip", "browser_download_url": DL + "../x/SGM_beta_v9.9.zip"}])
        self.assertIsNone(m.release_info(dots))
        self.assertTrue(m.is_newer("v1", "0.9.1"))

    def test_empreinte(self):
        h = "a" * 64
        self.assertEqual(m.expected_sha256(f"{h}  SGM_beta_v9.9.zip\n", "SGM_beta_v9.9.zip"), h)
        self.assertEqual(m.expected_sha256(f"{h} *sgm_beta_v9.9.zip", "SGM_beta_v9.9.zip"), h)
        self.assertEqual(m.expected_sha256(h, "x.zip"), h)
        self.assertEqual(m.expected_sha256(f"{h}  autre.zip", "SGM_beta_v9.9.zip"), "")

    def prepared(self, zip_bytes, sha_text=None):
        info = m.release_info(release())
        sha_text = sha_text if sha_text is not None else hashlib.sha256(zip_bytes).hexdigest() + "  SGM_beta_v9.9.zip"
        files = {info["zip_url"]: zip_bytes, info["sha_url"]: sha_text.encode()}
        return m.prepare_update(info, getter=lambda url, *a: files[url], base=self.tmp / "upd")

    def test_preparation_complete(self):
        z = make_zip({"SGM/SGM.exe": b"EXE", "SGM/_internal/x.dll": b"D", "SGM/README.md": b"r",
                      "SGM/SGM_data/config.json": b"{}"})
        res = self.prepared(z)
        self.assertEqual(res["version"], "9.9")
        self.assertTrue((res["src"] / "SGM.exe").is_file())
        script = res["script"].read_text(encoding="utf-8")
        self.assertNotIn("SGM_data", script.replace(str(self.tmp), ""))  # SGM_data jamais sauvegardé ni copié
        self.assertIn('robocopy "%SRC%" "%DST%" "SGM.exe"', script)       # seulement les éléments de la version
        self.assertIn('robocopy "%SRC%\\_internal" "%DST%\\_internal" /E', script)
        self.assertIn(":rollback", script)                           # retour à l'ancienne version en cas d'échec
        self.assertIn(str(m.app_dir()), script)
        self.assertIn(f"PID eq {os.getpid()}", script)

    def test_empreinte_fausse_ou_absente(self):
        z = make_zip({"SGM/SGM.exe": b"EXE"})
        with self.assertRaises(m.UpdateError) as ctx:
            self.prepared(z, "0" * 64 + "  SGM_beta_v9.9.zip")
        self.assertEqual(str(ctx.exception), "sha")
        with self.assertRaises(m.UpdateError) as ctx:
            self.prepared(z, "rien")
        self.assertEqual(str(ctx.exception), "no_sha")
        info = m.release_info(release(assets=[release()["assets"][0]]))
        with self.assertRaises(m.UpdateError):
            m.prepare_update(info, getter=lambda *a: b"", base=self.tmp / "upd")

    def test_archive_dangereuse_ou_incomplete(self):
        with self.assertRaises(m.UpdateError):
            self.prepared(make_zip({"../../evil.exe": b"x", "SGM/SGM.exe": b"E"}))
        with self.assertRaises(m.UpdateError):
            self.prepared(make_zip({"SGM/README.md": b"r"}))           # pas de SGM.exe

    def test_reglages_memorises(self):
        cfg = m.Config()
        self.assertIsNone(cfg.update_check)
        cfg.update_check, cfg.update_last, cfg.update_skip = True, 123.0, "9.9"
        cfg.save()
        cfg = m.Config()
        self.assertEqual((cfg.update_check, cfg.update_last, cfg.update_skip), (True, 123.0, "9.9"))


class UpdateGuiTest(SandboxTest):
    def test_resultats(self):
        w = m.MainWindow()
        shown, infos, warned = [], [], []
        w.show_update_dialog = lambda info: shown.append(info["version"])
        old_info, old_warn = m.QMessageBox.information, m.warn
        m.QMessageBox.information = staticmethod(lambda *a, **k: infos.append(a[2]))
        m.warn = lambda parent, text: warned.append(text)
        try:
            info = m.release_info(release())
            w.on_update_result(info, "", manual=False)
            self.assertEqual(shown, ["9.9"])
            w.config.update_skip = "9.9"
            w.on_update_result(info, "", manual=False)               # version ignorée : rien au lancement
            self.assertEqual(shown, ["9.9"])
            w.on_update_result(info, "", manual=True)                # mais proposée si on la demande
            self.assertEqual(shown, ["9.9", "9.9"])
            w.on_update_result(m.release_info(release(tag_name="v0.1")), "", manual=True)
            self.assertEqual(infos, [m.tr("update_uptodate", ver=m.APP_VERSION)])
            w.on_update_result(None, "timeout", manual=False)        # silencieux au lancement
            self.assertEqual(warned, [])
            w.on_update_result(None, "timeout", manual=True)
            self.assertEqual(len(warned), 1)
            self.assertGreater(m.Config().update_last, 0)
        finally:
            m.QMessageBox.information, m.warn = old_info, old_warn
            w.close()
            w.deleteLater()
            APP.processEvents()


if __name__ == "__main__":
    import unittest
    unittest.main()
