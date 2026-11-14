# -*- coding: utf-8 -*-
"""Signaler un problème / Proposer une idée : texte de l'issue, paquet .zip, fenêtre."""
import json
import os
import zipfile
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m  # noqa: E402

APP = QApplication.instance() or QApplication([])


def query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


class IssueTextTest(SandboxTest):
    def test_texte_de_l_utilisateur_dans_l_issue(self):
        q = query(m.report_url("bug", "MSFS 2024", "fr", ["sgm-bug-1.zip"],
                               {"what": "Les statics restent visibles", "scene": "EBBR"}, "EBBR statics"))
        self.assertEqual(q["title"], "Bug: EBBR statics")
        self.assertIn("### What happened?\nLes statics restent visibles", q["body"])
        self.assertIn("### Scenery concerned (name, developer, ICAO)\nEBBR", q["body"])
        self.assertIn("`sgm-bug-1.zip`", q["body"])
        self.assertEqual(q["labels"], "bug")

    def test_idee(self):
        q = query(m.report_url("idea", "MSFS 2020", "en", (), {"idea": "Profils", "why": "Gain de temps"}, "Profils"))
        self.assertEqual(q["title"], "Idea: Profils")
        self.assertIn("### Your idea\nProfils", q["body"])
        self.assertNotIn("What happened", q["body"])
        self.assertEqual(q["labels"], "enhancement")

    def test_chemin_personnel_retire(self):
        _t, body = m.issue_text("bug", "MSFS 2024", "en", {"what": r"Erreur dans C:\Users\Jean Dupont\Downloads\a.zip"})
        self.assertNotIn("Jean", body)
        self.assertIn(r"~\Downloads\a.zip", body)

    def test_texte_long_raccourci_dans_l_adresse(self):
        long = "x" * 20000
        _t, body = m.issue_text("bug", "MSFS 2024", "en", {"what": long, "steps": long})
        self.assertLessEqual(len(body), m.ISSUE_BODY_MAX)
        self.assertIn("full text in the attached file", body)
        self.assertLess(len(m.report_url("bug", "MSFS 2024", "en", (), {"what": long, "steps": long})), 16000)

    def test_paquet_complet(self):
        long = "y" * 9000
        out = m.build_report_package("bug", "MSFS 2024", "en", {"what": long}, "Titre",
                                     report={"summary": {"scenes_with_candidates": 2}}, include_log=False)
        self.assertEqual(out.parent, self.data / "reports")
        self.assertTrue(out.name.startswith("sgm-bug-") and out.suffix == ".zip")
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            msg = z.read("message.md").decode("utf-8")
            rep = json.loads(z.read("statics-report.json"))
        self.assertEqual(names, ["message.md", "statics-report.json"])
        self.assertIn(long, msg)                      # texte complet, non raccourci
        self.assertEqual(rep["summary"]["scenes_with_candidates"], 2)
        self.assertFalse(list(self.data.glob("reports/*.tmp")))


class ReportDialogTest(SandboxTest):
    def test_fenetre_bug_puis_idee(self):
        d = m.ReportDialog("bug", "MSFS 2024", ["Brussels Airport EBBR", "EBBR"])
        self.assertTrue(d.cb_report.isChecked() and d.cb_log.isChecked())
        self.assertTrue(d.rows["idea"][1].isHidden())
        self.assertFalse(d.rows["what"][1].isHidden())
        d.inputs["what"].setPlainText("Rien ne change")
        d.summary.setText("Test")
        d.toggle_preview()
        txt = d.preview.toPlainText()
        self.assertIn("Bug: Test", txt)
        self.assertIn("Rien ne change", txt)
        self.assertIn("statics-report.json", txt)
        d.set_kind("idea")
        self.assertFalse(d.cb_report.isChecked() or d.cb_log.isChecked())
        self.assertTrue(d.rows["what"][1].isHidden())
        self.assertEqual(d.main_text(), "")
        d.inputs["idea"].setPlainText("Une idée")
        self.assertEqual(d.fields(), {"idea": "Une idée", "why": ""})
        self.assertIn("Idea: Test", d.preview.toPlainText())
        d.deleteLater()

    def test_texte_obligatoire(self):
        d = m.ReportDialog("idea", "MSFS 2024")
        shown = []
        orig = m.warn
        m.warn = lambda parent, text: shown.append(text)
        try:
            d.accept_if_filled()
        finally:
            m.warn = orig
        self.assertEqual(shown, [m.tr("rd_empty")])
        self.assertEqual(d.result(), 0)
        d.deleteLater()


if __name__ == "__main__":
    import unittest
    unittest.main()
