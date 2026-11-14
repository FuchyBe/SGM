# -*- coding: utf-8 -*-
"""Traductions complètes et cohérentes, migration de la configuration."""
import json
import re
import unittest

import i18n
from helpers import SandboxTest, m

PLACEHOLDER = re.compile(r"{(\w+)}")


class TestI18n(unittest.TestCase):

    def test_every_language_has_translations(self):
        codes = [c for c, _ in i18n.LANGS]
        self.assertEqual(codes[0], "en")
        for code in codes[1:]:
            self.assertIn(code, i18n.TR, code)

    def test_no_unknown_keys_and_same_placeholders(self):
        for lang, table in i18n.TR.items():
            for key, text in table.items():
                self.assertIn(key, i18n.EN, f"{lang}: clé inconnue {key}")
                self.assertEqual(set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(i18n.EN[key])),
                                 f"{lang}/{key}: champs {{…}} différents de l'anglais")

    def test_short_ui_strings_translated_everywhere(self):
        """Les libellés courts de l'interface doivent exister dans les 12 langues (les longs textes
        d'aide peuvent retomber sur l'anglais)."""
        long_keys = {"help_html", "disclaimer_html", "licenses_html", "help_lang_note",
                     "versions_title", "licenses_missing"}
        missing = {}
        for lang, table in i18n.TR.items():
            if lang == "fr":
                continue
            gaps = [k for k in i18n.EN if k not in table and k not in long_keys
                    and not i18n.EN[k].isupper() and k not in ("f_on", "f_off", "col_statics", "col_scene",
                                                                 "manual", "statics_tip", "standard", "stats_n",
                                                                 "stats_on", "stats_off", "stats_gsx", "grp_on",
                                                                 "grp_off", "st_on", "st_off", "toggled",
                                                                 "gsx_status", "all_progress", "mode_conflict",
                                                                 "mode_rename", "mode_variant", "auto",
                                                                 "f_all", "f_new", "gsx_search_btn")]
            if gaps:
                missing[lang] = gaps
        self.assertEqual(missing, {}, "libellés non traduits")

    def test_old_name_not_used(self):
        for table in [i18n.EN] + list(i18n.TR.values()):
            for key, text in table.items():
                self.assertNotIn("Statics Manager", text.replace("Statics &amp; GSX Manager", ""), key)


class TestConfig(SandboxTest):

    def test_migration_from_v2(self):
        (self.data / "config.json").write_text(json.dumps({
            "version": 2, "manual_folders": ["E:/Scenes"], "known_scenes": ["k"],
            "gsx_folder": "", "gsx_choices": {"s": "gsx/lite"}}))
        c = m.Config()
        self.assertEqual(c.sim, "MSFS 2024")
        self.assertEqual(c.manual_folders, ["E:/Scenes"])
        self.assertEqual(c.gsx_choices, {"s": "gsx/lite"})
        self.assertFalse(c.first_run)

    def test_profiles_are_separate_per_simulator(self):
        c = m.Config()
        c.manual_folders = ["D:/2024"]
        c.sim = "MSFS 2020"
        self.assertEqual(c.manual_folders, [])
        c.manual_folders = ["D:/2020"]
        c.save()
        c2 = m.Config()
        self.assertEqual(c2.sim, "MSFS 2020")
        self.assertEqual(c2.manual_folders, ["D:/2020"])
        c2.sim = "MSFS 2024"
        self.assertEqual(c2.manual_folders, ["D:/2024"])


if __name__ == "__main__":
    unittest.main()


class TestTranslationChecker(unittest.TestCase):
    def test_no_blocking_translation_error(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "check_i18n", Path(__file__).resolve().parent.parent / "scripts" / "check_i18n.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        errors, _warnings = mod.check()
        self.assertEqual(errors, [])
