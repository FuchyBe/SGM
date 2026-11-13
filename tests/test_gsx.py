# -*- coding: utf-8 -*-
"""Profils GSX : détection, copie, versions, profils installés à la main, OACI."""
import unittest

from helpers import SandboxTest, m, make_pkg, profile


class TestGsx(SandboxTest):

    def test_single_profile_status_and_copy(self):
        make_pkg(self.community, "test-eblg", "Liege Airport EBLG", [
            ("Extras/GSX Profile/eblg-test.ini", profile("a"), False),
            ("Extras/GSX Profile/eblg-test.py", b"# py", False),
            ("Extras/GSX Profile/readme.txt", b"hello", False)])
        sc = self.scan()["test-eblg"]
        self.assertEqual(len(sc.gsx_variants), 1)
        v = sc.gsx_variants[0]
        self.assertEqual(sorted(f.name for f in v.files), ["eblg-test.ini", "eblg-test.py"])
        self.assertEqual(m.gsx_status(v.files, self.gsx), m.GSX_MISSING)
        m.copy_gsx(sc, v, self.gsx)
        self.assertEqual(m.gsx_status(v.files, self.gsx), m.GSX_SAME)
        self.assertFalse((self.gsx / "readme.txt").exists())
        (self.gsx / "eblg-test.ini").write_bytes(profile("edited"))
        m.forget_hash(self.gsx / "eblg-test.ini")
        self.assertEqual(m.gsx_status(v.files, self.gsx), m.GSX_DIFF)

    def test_non_gsx_ini_ignored(self):
        make_pkg(self.community, "test-x", "Test LIRF", [("Extras/options.ini", b"[settings]\nvolume=1\n", False)])
        self.assertNotIn("test-x", {k: v for k, v in self.scan().items() if v.gsx_variants})

    def test_variant_labels(self):
        self.assertEqual(m.variant_labels(["FULL - GSX VDGS", "LITE - GSX VDGS", "GSX VDGS"]),
                         ["FULL", "LITE", "Standard"])

    def test_versions_switch_and_choice_state(self):
        make_pkg(self.community, "test-lfmn", "Nice LFMN", [
            ("GSX/Nice FULL/lfmn-x.ini", profile("same"), False),
            ("GSX/Nice FULL/lfmn-x.py", b"# full", False),
            ("GSX/Nice LITE/lfmn-x.ini", profile("same"), False)])
        sc = self.scan()["test-lfmn"]
        full, lite = sc.gsx_variants
        self.assertEqual((full.label, lite.label), ("FULL", "LITE"))
        # FULL installé à la main : les deux .ini sont identiques -> impossible de trancher
        m.copy_gsx(sc, full, self.gsx)
        state, act, why, _ = m.gsx_variant_state(sc, self.gsx, None)
        self.assertEqual((state, why), (m.VAR_CHECK, "reason_multi"))
        # choix mémorisé : LITE -> le .py de FULL est retiré
        m.copy_gsx(sc, lite, self.gsx)
        self.assertFalse((self.gsx / "lfmn-x.py").exists())
        state, act, _, _ = m.gsx_variant_state(sc, self.gsx, m.variant_id(sc, lite))
        self.assertEqual((state, act), (m.VAR_CHOSEN, 1))

    def test_edited_profile_is_never_removed(self):
        make_pkg(self.community, "test-lfmn", "Nice LFMN", [
            ("GSX/FULL/lfmn-x.ini", profile("f"), False), ("GSX/FULL/lfmn-x.py", b"# full", False),
            ("GSX/LITE/lfmn-x.ini", profile("l"), False)])
        sc = self.scan()["test-lfmn"]
        (self.gsx / "lfmn-x.py").write_bytes(b"# edited by the user")
        m.copy_gsx(sc, sc.gsx_variants[1], self.gsx)
        self.assertEqual((self.gsx / "lfmn-x.py").read_bytes(), b"# edited by the user")

    def test_manual_profile_and_search_query(self):
        make_pkg(self.community, "test-lemd", "Madrid Barajas LEMD", [("scenery/LEMD.bgl", b"A", True)])
        (self.gsx / "lemd-community.ini").write_bytes(profile("m"))
        (self.gsx / "lemdx-other.ini").write_bytes(profile("o"))
        sc = self.scan()["test-lemd"]
        self.assertTrue(sc.is_airport)
        self.assertEqual(m.gsx_manual_profiles(sc, m.gsx_dest_index(self.gsx)), ["lemd-community.ini"])
        self.assertEqual(m.gsx_search_query(sc), "LEMD GSX")
        url = m.SEARCH_ENGINES["fsto"].format(q=m.quote_plus(m.gsx_search_query(sc)))
        self.assertTrue(url.startswith("https://flightsim.to/"))
        self.assertIn("LEMD+GSX", url)

    def test_icao_detection(self):
        self.assertEqual(m.detect_icao("Paris Charles de Gaulle LFPG", "x"), "LFPG")
        self.assertEqual(m.detect_icao("MSFS FULL Pack", "x"), "")
        self.assertEqual(m.detect_icao("Liege Spa Airfield", "studio-ebsp-spa"), "EBSP")
        self.assertEqual(m.detect_icao("Orbx Landmarks", "orbx-landmarks"), "")

    def test_report_url_has_no_personal_data(self):
        url = m.report_url("bug", "MSFS 2024", "fr")
        self.assertTrue(url.startswith(m.ISSUES_NEW_URL))
        self.assertIn("title=Bug", url)
        self.assertIn("FuchyBe/SGM", url)
        self.assertNotIn(str(self.tmp), url)
        self.assertNotIn("Users", url)


if __name__ == "__main__":
    unittest.main()
