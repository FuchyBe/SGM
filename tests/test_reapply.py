# -*- coding: utf-8 -*-
"""Statics remis par une mise à jour de scène : mémoire du choix ON / OFF, détection, bandeau Réappliquer / Ignorer."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m, make_pkg  # noqa: E402
from test_gui_smoke import wait_scan  # noqa: E402

APP = QApplication.instance() or QApplication([])


def set_version(root, version):
    man = json.loads((root / "manifest.json").read_text())
    man["package_version"] = version
    (root / "manifest.json").write_text(json.dumps(man, indent=2))


def ebbr(base, version="1.0.0", files=None):
    root = make_pkg(base, "test-ebbr", "Brussels Airport EBBR",
                    files or [("scenery/EBBR_statics.bgl", b"S" * 9, True)])
    set_version(root, version)
    return root


def simulate_update(root, version):
    """L'installateur de l'éditeur remet les fichiers d'origine (statics ON) avec une nouvelle version."""
    for p in list((root / "scenery").iterdir()):
        p.unlink()
    make_pkg(root.parent, root.name, "Brussels Airport EBBR", [("scenery/EBBR_statics.bgl", b"S" * 9, True)])
    set_version(root, version)


class DetectionTest(SandboxTest):
    """reapply_candidates : fonction pure, sans interface."""

    def scene(self, root):
        return m.scan_package(root, "Community")

    def test_version_changee_detectee(self):
        s = self.scene(ebbr(self.community, "1.1.0"))
        self.assertEqual(s.version, "1.1.0")
        self.assertEqual(s.state, m.ON)
        found = m.reapply_candidates([s], {s.key: {"state": "off", "version": "1.0.0"}})
        self.assertEqual([x.key for x in found], [s.key])

    def test_meme_version_bascule_a_la_main(self):
        s = self.scene(ebbr(self.community, "1.0.0"))
        self.assertEqual(m.reapply_candidates([s], {s.key: {"state": "off", "version": "1.0.0"}}), [])

    def test_version_vide(self):
        s = self.scene(ebbr(self.community, ""))
        self.assertEqual(s.version, "")
        self.assertEqual(m.reapply_candidates([s], {s.key: {"state": "off", "version": "1.0.0"}}), [])

    def test_choix_on_ou_absent(self):
        s = self.scene(ebbr(self.community, "1.1.0"))
        self.assertEqual(m.reapply_candidates([s], {s.key: {"state": "on", "version": "1.0.0"}}), [])
        self.assertEqual(m.reapply_candidates([s], {}), [])
        self.assertEqual(m.reapply_candidates([s], {s.key: "off"}), [])          # entrée abîmée : ignorée

    def test_scene_off_pas_signalee(self):
        s = self.scene(ebbr(self.community, "1.1.0", [("scenery/EBBR_statics.bgl.off", b"S" * 9, False)]))
        self.assertEqual(s.state, m.OFF)
        self.assertEqual(m.reapply_candidates([s], {s.key: {"state": "off", "version": "1.0.0"}}), [])

    def test_scene_a_verifier_jamais_signalee(self):
        s = self.scene(ebbr(self.community, "1.1.0", [("scenery/EBBR_statics.bgl", b"S" * 9, True),
                                                      ("scenery/EBBR_statics.bgl.off", b"T" * 9, False)]))
        self.assertIsNone(m.wanted_entry(s))
        self.assertEqual(m.reapply_candidates([s], {s.key: {"state": "off", "version": "1.0.0"}}), [])

    def test_memoriser_seulement_les_cas_simples(self):
        s = self.scene(ebbr(self.community, "2.0"))
        wanted = {}
        self.assertTrue(m.remember_statics(wanted, [s, None]))
        self.assertEqual(wanted, {s.key: {"state": "on", "version": "2.0"}})
        self.assertFalse(m.remember_statics(wanted, [s]))                          # rien de neuf


class ConfigTest(SandboxTest):
    def test_persistance_par_simulateur_et_nettoyage(self):
        cfg = m.Config()
        cfg.statics_wanted["k1"] = {"state": "off", "version": "1.2.0"}
        cfg.save()
        raw = json.loads(cfg.file.read_text(encoding="utf-8"))
        raw["profiles"][cfg.sim]["statics_wanted"].update({"k2": {"state": "bof"}, "k3": "off",
                                                          "k4": {"state": "on", "version": 7}})
        cfg.file.write_text(json.dumps(raw), encoding="utf-8")
        cfg = m.Config()
        self.assertEqual(cfg.statics_wanted, {"k1": {"state": "off", "version": "1.2.0"},
                                              "k4": {"state": "on", "version": "7"}})
        cfg.sim = next(s for s in m.SIMS if s != cfg.sim)                          # l'autre simulateur : vide
        self.assertEqual(cfg.statics_wanted, {})


class ReapplyGuiTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.root = ebbr(self.community, "1.0.0")
        cfg = m.Config()
        cfg.manual_folders.append(str(self.community))
        cfg.save()
        self._ask = m.ask
        m.ask = lambda *a, **k: True
        self.w = None

    def tearDown(self):
        m.ask = self._ask
        m.HOST_CONFIRM_SIM = None
        if self.w is not None:
            self.w.close()
            self.w.deleteLater()
            APP.processEvents()
        super().tearDown()

    def window(self):
        self.w = m.MainWindow()
        QTimer.singleShot(0, self.w.start_scan)
        wait_scan(self.w)
        return self.w

    def rescan(self):
        self.w.start_scan()
        wait_scan(self.w)

    def key(self):
        return m.norm_key(self.root)

    def banner_shown(self):
        return not self.w.reapply_banner.isHidden()

    def test_bascule_memorisee_puis_mise_a_jour_reappliquee(self):
        w = self.window()
        k = self.key()
        self.assertNotIn(k, w.config.statics_wanted)                        # jamais basculée : rien
        w.on_toggle(w.scenes[k], False)
        self.assertEqual(m.Config().statics_wanted[k], {"state": "off", "version": "1.0.0"})   # enregistré sur disque
        self.rescan()
        self.assertFalse(self.banner_shown())                               # même version : rien
        simulate_update(self.root, "1.1.0")
        self.rescan()
        self.assertTrue(self.banner_shown())
        self.assertIn("Brussels Airport EBBR", w.reapply_lbl._full)
        self.assertIn("Brussels Airport EBBR", w.reapply_lbl.toolTip())
        n_backups = len(list((self.data / "backups").rglob("*.*")))
        w.reapply_found()
        self.assertFalse(self.banner_shown())
        self.assertEqual(w.scenes[k].state, m.OFF)
        self.assertGreater(len(list((self.data / "backups").rglob("*.*"))), n_backups)   # sauvegarde faite
        self.assertEqual(w.config.statics_wanted[k], {"state": "off", "version": "1.1.0"})
        self.assertIn("Reapply OFF (1)", w.btn_undo.toolTip())               # une seule action annulable
        self.rescan()
        self.assertFalse(self.banner_shown())                               # ne revient pas
        w.undo_last_action()                                                 # annulable
        self.assertEqual(w.scenes[k].state, m.ON)
        self.assertTrue((self.root / "scenery/EBBR_statics.bgl").is_file())
        self.assertEqual(w.config.statics_wanted[k], {"state": "on", "version": "1.1.0"})   # état réel relu

    def test_ignorer(self):
        w = self.window()
        k = self.key()
        w.on_toggle(w.scenes[k], False)
        simulate_update(self.root, "2.0.0")
        self.rescan()
        self.assertTrue(self.banner_shown())
        w.ignore_reapply()
        self.assertFalse(self.banner_shown())
        self.assertEqual(m.Config().statics_wanted[k], {"state": "on", "version": "2.0.0"})
        self.assertEqual(w.scenes[k].state, m.ON)                            # rien n'a été touché
        self.rescan()
        self.assertFalse(self.banner_shown())

    def test_simulateur_ouvert_rien_ne_change(self):
        w = self.window()
        k = self.key()
        w.on_toggle(w.scenes[k], False)
        simulate_update(self.root, "2.0.0")
        self.rescan()
        m.HOST_CONFIRM_SIM = lambda parent: False                           # accroche S11 : écriture refusée
        w.reapply_found()
        self.assertEqual(w.scenes[k].state, m.ON)
        self.assertTrue(self.banner_shown())
        self.assertEqual(w.config.statics_wanted[k], {"state": "off", "version": "1.0.0"})

    def test_restauration_efface_le_choix(self):
        w = self.window()
        k = self.key()
        w.on_toggle(w.scenes[k], False)
        self.assertIn(k, w.config.statics_wanted)
        w.on_restore(w.scenes[k])
        self.assertEqual(w.scenes[k].state, m.ON)
        self.assertNotIn(k, m.Config().statics_wanted)

    def test_tout_restaurer_efface_le_choix(self):
        w = self.window()
        k = self.key()
        w.set_all(m.OFF)
        self.assertEqual(w.config.statics_wanted[k]["state"], "off")
        w.restore_all()
        wait_scan(w)
        self.assertNotIn(k, m.Config().statics_wanted)

    def test_profil_memorise(self):
        w = self.window()
        k = self.key()
        w.config.statics_profiles["p"] = {k: "off"}
        w.apply_profile("p")
        self.assertEqual(w.config.statics_wanted[k], {"state": "off", "version": "1.0.0"})


if __name__ == "__main__":
    import unittest
    unittest.main()
