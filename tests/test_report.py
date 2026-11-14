# -*- coding: utf-8 -*-
"""Rapport d'analyse des statics : lecture seule, sans chemin personnel, fichiers candidats repérés."""
import json
import unittest

from helpers import SandboxTest, m, make_pkg


class TestReport(SandboxTest):

    def build(self):
        src = m.Source(m.MANUAL, self.community, False, True)
        return m.build_statics_report([src], "MSFS 2024")

    def snapshot(self):
        return {p: p.read_bytes() for p in self.community.rglob("*") if p.is_file()}

    def test_report_is_read_only_and_anonymous(self):
        make_pkg(self.community, "studio-ebbr", "Brussels EBBR", [
            ("scenery/EBBR_statics.bgl", b"S" * 40, True), ("scenery/EBBR.bgl", b"A" * 9, True)])
        make_pkg(self.community, "studio-lfpg", "Paris LFPG", [
            ("scenery/statics_on.bgl", b"N" * 5, False), ("scenery/statics_off.bgl", b"F" * 5, False),
            ("scenery/statics.bgl", b"N" * 5, True)])
        before = self.snapshot()
        rep = self.build()
        self.assertEqual(self.snapshot(), before)
        dump = json.dumps(rep)
        self.assertNotIn(str(self.tmp), dump)
        self.assertNotIn(str(self.community), dump)
        out = m.write_statics_report(rep)
        self.assertTrue(out.is_file())
        self.assertEqual(out.parent, self.data / "reports")
        self.assertEqual(json.loads(out.read_text())["schema"], m.REPORT_SCHEMA)

    def test_candidates_not_used_by_sgm_are_listed(self):
        make_pkg(self.community, "studio-ebci", "Charleroi EBCI", [
            ("scenery/EBCI_statics.bgl", b"S" * 4, True),
            ("scenery/EBCI_static_aircraft.bgl", b"T" * 4, True),       # « static » sans s
            ("scenery/modelLib_static_people.bgl", b"P" * 4, True),     # bibliothèque : pas basculée
            ("scenery/EBCI_parked_disabled.bgl.bak", b"U" * 4, False),
            ("Options/statics_without.bgl", b"V" * 4, False),
            ("scenery/EBCI_terrain.bgl", b"W" * 4, True)])               # sans rapport : ignoré
        rep = self.build()
        sc = rep["scenes"][0]
        paths = {f["path"]: f for f in sc["files"]}
        self.assertIn("scenery/EBCI_static_aircraft.bgl", paths)
        self.assertIn("scenery/EBCI_parked_disabled.bgl.bak", paths)
        self.assertIn("Options/statics_without.bgl", paths)
        self.assertNotIn("scenery/EBCI_terrain.bgl", paths)
        self.assertTrue(paths["scenery/EBCI_statics.bgl"]["in_layout"])
        self.assertTrue(paths["scenery/EBCI_static_aircraft.bgl"]["used_by_sgm"])
        self.assertFalse(paths["scenery/modelLib_static_people.bgl"]["used_by_sgm"])
        self.assertEqual(sc["bgl_count"], 5)
        self.assertGreaterEqual(rep["summary"]["candidate_files_not_used_by_sgm"], 2)
        self.assertTrue(sc["sgm_groups"])

    def test_aircraft_and_empty_packages_skipped(self):
        make_pkg(self.community, "plane", "Some Plane", [("SimObjects/x_static.bgl", b"x", True)], ctype="AIRCRAFT")
        make_pkg(self.community, "plain", "Plain Scenery", [("scenery/a.bgl", b"x", True)])
        rep = self.build()
        self.assertEqual(rep["scenes"], [])
        self.assertEqual(rep["packages_scanned"], 2)


if __name__ == "__main__":
    unittest.main()
