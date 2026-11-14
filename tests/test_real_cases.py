# -*- coding: utf-8 -*-
"""Familles de noms réels (rapport d'analyse du 2026-11-14, docs/analyses/BASE.md).
Noms de fichiers exacts, contenus factices. Chaque famille : détection, OFF, ON, restauration."""
import json
import unittest

from helpers import SandboxTest, m, make_pkg


class TestRealCases(SandboxTest):

    def files(self, root):
        import hashlib
        return {p.relative_to(root).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()[:10]
                for p in root.rglob("*") if p.is_file()}

    def layout(self, root):
        return {c["path"] for c in json.loads((root / "layout.json").read_text())["content"]}

    def cycle(self, folder, root, before):
        """OFF/ON/OFF/ON puis restauration : on doit retrouver exactement les fichiers d'origine (`before`)."""
        for target in (m.OFF, m.ON, m.OFF, m.ON):
            m.set_scene_state(self.scan()[folder], target)
            self.assertEqual(self.scan()[folder].state, target)
        m.restore_scene_statics(root)
        self.assertEqual(self.files(root), before)

    # A. iniBuilds, Orbx Suède, JetStream, UK2000, Drzewiecki… : extension remplacée par .off
    def test_extension_replaced_by_off(self):
        d = "Scenery/airport-inibuilds-dallas/inibuilds-scene"
        root = make_pkg(self.community, "inibuilds-airport-kdfw-dallas", "KDFW", [
            (f"{d}/kdfw-scene-statics.off", b"S" * 54, False), (f"{d}/kdfw-scene-airport.bgl", b"A" * 900, True)])
        orig = self.files(root)
        g = self.scan()["inibuilds-airport-kdfw-dallas"].groups[0]
        self.assertEqual((g.mode, g.state, g.off_form), ("rename", m.OFF, "off"))
        m.set_scene_state(self.scan()["inibuilds-airport-kdfw-dallas"], m.ON)
        self.assertTrue((root / f"{d}/kdfw-scene-statics.bgl").is_file())
        self.assertIn(f"{d}/kdfw-scene-statics.bgl", self.layout(root))
        m.set_scene_state(self.scan()["inibuilds-airport-kdfw-dallas"], m.OFF)
        self.assertTrue((root / f"{d}/kdfw-scene-statics.off").is_file())       # retour à la convention de l'éditeur
        self.assertNotIn(f"{d}/kdfw-scene-statics.bgl", self.layout(root))
        self.cycle("inibuilds-airport-kdfw-dallas", root, orig)

    # B. Drzewiecki Design : XXXX_Static.BGL (singulier, majuscules), actif
    def test_singular_static_uppercase(self):
        d = "scenery/Boeing Field Airport MSFS"
        root = make_pkg(self.community, "drzewieckidesign-airport-kbfi-boeing-field", "KBFI", [
            (f"{d}/KBFI_STATIC.BGL", b"S" * 80, True)])
        orig = self.files(root)
        g = self.scan()["drzewieckidesign-airport-kbfi-boeing-field"].groups[0]
        self.assertEqual((g.mode, g.state), ("rename", m.ON))
        self.cycle("drzewieckidesign-airport-kbfi-boeing-field", root, orig)

    # C. Drzewiecki EPWR : .BGL actif + copie .off identique
    def test_identical_twin(self):
        d = "scenery/EPWR Wroclaw Airport MSFS"
        root = make_pkg(self.community, "drzewieckidesign-airport-epwr-wroclaw", "EPWR", [
            (f"{d}/EPWR_Static.BGL", b"S" * 20, True), (f"{d}/EPWR_Static.off", b"S" * 20, False)])
        orig = self.files(root)
        sc = self.scan()["drzewieckidesign-airport-epwr-wroclaw"]
        self.assertEqual((sc.groups[0].mode, sc.state, sc.groups[0].twin), ("rename", m.ON, True))
        m.set_scene_state(sc, m.OFF)
        self.assertFalse((root / f"{d}/EPWR_Static.BGL").exists())
        self.assertTrue((root / f"{d}/EPWR_Static.off").is_file())
        self.cycle("drzewieckidesign-airport-epwr-wroclaw", root, orig)

    # D. Orbx / UK2000 / Drzewiecki PLC : X.bgl + X.bgl.nostatic
    def test_nostatic_swap(self):
        d = "scenery/world/scenery"
        root = make_pkg(self.community, "orbx-airport-lyni-nis", "LYNI", [
            (f"{d}/lyni_place.bgl", b"WITH" * 50, True), (f"{d}/lyni_place.bgl.nostatic", b"NO" * 40, False)])
        orig = self.files(root)
        g = self.scan()["orbx-airport-lyni-nis"].groups[0]
        self.assertEqual((g.mode, g.state), ("swap", m.ON))
        m.set_scene_state(self.scan()["orbx-airport-lyni-nis"], m.OFF)
        # règle de Fabian : X.bgl -> X.bgl.bak, puis copie de X.bgl.nostatic en X.bgl
        self.assertEqual((root / f"{d}/lyni_place.bgl").read_bytes(), b"NO" * 40)
        self.assertEqual((root / f"{d}/lyni_place.bgl.bak").read_bytes(), b"WITH" * 50)
        self.assertEqual((root / f"{d}/lyni_place.bgl.nostatic").read_bytes(), b"NO" * 40)
        self.assertEqual(self.scan()["orbx-airport-lyni-nis"].state, m.OFF)
        m.set_scene_state(self.scan()["orbx-airport-lyni-nis"], m.ON)
        self.assertEqual((root / f"{d}/lyni_place.bgl").read_bytes(), b"WITH" * 50)
        self.assertFalse((root / f"{d}/lyni_place.bgl.bak").exists())
        self.cycle("orbx-airport-lyni-nis", root, orig)

    # D1. UK2000 KHND : X.bgl (sans statics) + X.bgl.staticq (avec) -> règle de Fabian
    def test_staticq_swap(self):
        d = "scenery/UK2000Scenery/scenery"
        root = make_pkg(self.community, "uk2000scenery-airport-khnd", "KHND", [
            (f"{d}/khnd-airport.bgl", b"NO" * 200, True), (f"{d}/khnd-airport.bgl.staticq", b"WITH" * 100, False)])
        orig = self.files(root)
        g = self.scan()["uk2000scenery-airport-khnd"].groups[0]
        self.assertEqual((g.mode, g.state), ("swap", m.OFF))           # statics désactivés de base
        m.set_scene_state(self.scan()["uk2000scenery-airport-khnd"], m.ON)
        self.assertEqual((root / f"{d}/khnd-airport.bgl").read_bytes(), b"WITH" * 100)
        self.assertEqual((root / f"{d}/khnd-airport.bgl.bak").read_bytes(), b"NO" * 200)
        self.assertEqual((root / f"{d}/khnd-airport.bgl.staticq").read_bytes(), b"WITH" * 100)
        self.assertEqual(self.scan()["uk2000scenery-airport-khnd"].state, m.ON)
        m.set_scene_state(self.scan()["uk2000scenery-airport-khnd"], m.OFF)
        self.assertEqual(self.files(root), orig)
        self.cycle("uk2000scenery-airport-khnd", root, orig)

    def test_staticq_without_base_is_left_alone(self):
        make_pkg(self.community, "uk2000-x", "XXXX", [("s/x-airport.bgl.staticq", b"W" * 9, False)])
        self.assertEqual(self.scan()["uk2000-x"].groups[0].note, "note_swap_broken")

    # D2. Drzewiecki : XXXX_Static.off + XXXX_PLC.bgl.nostatic seuls (forme désactivée) -> renommer en .bgl
    def test_drzewiecki_static_and_plc(self):
        d = "scenery"
        root = make_pkg(self.community, "drzewieckidesign-airport-epkt", "EPKT", [
            ("scenery/EPKT Katowice Airport MSFS/EPKT_Static.off", b"S" * 300, False),
            (f"{d}/EPKT_PLC.bgl.nostatic", b"P" * 29, False), (f"{d}/EPKT_APT.bgl", b"A" * 99, True)])
        orig = self.files(root)
        sc = self.scan()["drzewieckidesign-airport-epkt"]
        self.assertEqual(sc.state, m.OFF)                    # plus « Mixte »
        self.assertEqual(sorted(g.mode for g in sc.groups), ["rename", "rename"])
        m.set_scene_state(sc, m.ON)
        self.assertTrue((root / f"{d}/EPKT_PLC.bgl").is_file())
        self.assertTrue((root / "scenery/EPKT Katowice Airport MSFS/EPKT_Static.bgl").is_file())
        self.assertIn(f"{d}/EPKT_PLC.bgl", self.layout(root))
        sc = self.scan()["drzewieckidesign-airport-epkt"]
        self.assertEqual(sc.state, m.ON)                     # PLC retrouvé grâce à la photo d'origine
        m.set_scene_state(sc, m.OFF)
        self.assertTrue((root / f"{d}/EPKT_PLC.bgl.nostatic").is_file())
        self.assertTrue((root / "scenery/EPKT Katowice Airport MSFS/EPKT_Static.off").is_file())
        self.cycle("drzewieckidesign-airport-epkt", root, orig)

    # F2. iniBuilds : .bgl.disabled seul -> ON = copie en .bgl (le .disabled reste), OFF = copie supprimée
    def test_disabled_is_copied(self):
        d = "Scenery/airport-lowi-innsbruck/lowi-scene"
        root = make_pkg(self.community, "inibuilds-airport-lowi2", "LOWI", [
            (f"{d}/lowi-scene-airport.bgl", b"A" * 9000, True),
            (f"{d}/lowi-scene-airport-statics.bgl.disabled", b"S" * 1595, False)])
        orig = self.files(root)
        g = self.scan()["inibuilds-airport-lowi2"].groups[0]
        self.assertEqual((g.mode, g.state), ("rename", m.OFF))
        m.set_scene_state(self.scan()["inibuilds-airport-lowi2"], m.ON)
        self.assertTrue((root / f"{d}/lowi-scene-airport-statics.bgl").is_file())
        self.assertTrue((root / f"{d}/lowi-scene-airport-statics.bgl.disabled").is_file())
        self.assertIn(f"{d}/lowi-scene-airport-statics.bgl", self.layout(root))
        m.set_scene_state(self.scan()["inibuilds-airport-lowi2"], m.OFF)
        self.assertFalse((root / f"{d}/lowi-scene-airport-statics.bgl").exists())
        self.assertEqual(self.files(root), orig)
        self.cycle("inibuilds-airport-lowi2", root, orig)

    # E. iniBuilds KPVD : X_nostatic.bgl actif + X_static.bgl.disabled
    def test_static_nostatic_pair(self):
        d = "Scenery/airport-inibuilds-providence/inibuilds-scene"
        root = make_pkg(self.community, "inibuilds-airport-kpvd", "KPVD", [
            (f"{d}/kpvd-scene-airport_nostatic.bgl", b"N" * 180, True),
            (f"{d}/kpvd-scene-airport_static.bgl.disabled", b"S" * 181, False)])
        orig = self.files(root)
        g = self.scan()["inibuilds-airport-kpvd"].groups[0]
        self.assertEqual((g.mode, g.state), ("pair", m.OFF))
        m.set_scene_state(self.scan()["inibuilds-airport-kpvd"], m.ON)
        self.assertTrue((root / f"{d}/kpvd-scene-airport_static.bgl").is_file())
        self.assertTrue((root / f"{d}/kpvd-scene-airport_nostatic.bgl.disabled").is_file())
        lay = self.layout(root)
        self.assertIn(f"{d}/kpvd-scene-airport_static.bgl", lay)
        self.assertNotIn(f"{d}/kpvd-scene-airport_nostatic.bgl", lay)    # jamais les deux aéroports chargés
        self.cycle("inibuilds-airport-kpvd", root, orig)

    # F. iniBuilds LOWI : aéroport complet « avec statics » qui remplace le fichier de base
    def test_full_airport_replacement(self):
        d = "Scenery/airport-lowi-innsbruck/lowi-scene"
        root = make_pkg(self.community, "inibuilds-airport-lowi", "LOWI", [
            (f"{d}/lowi-scene-airport.bgl", b"A" * 1500, True),
            (f"{d}/lowi-scene-airport-statics.bgl.disabled", b"S" * 1595, False)])
        orig = self.files(root)
        g = self.scan()["inibuilds-airport-lowi"].groups[0]
        self.assertEqual((g.mode, g.state), ("pair", m.OFF))
        m.set_scene_state(self.scan()["inibuilds-airport-lowi"], m.ON)
        lay = self.layout(root)
        self.assertIn(f"{d}/lowi-scene-airport-statics.bgl", lay)
        self.assertNotIn(f"{d}/lowi-scene-airport.bgl", lay)
        self.assertTrue((root / f"{d}/lowi-scene-airport.bgl.disabled").is_file())
        self.cycle("inibuilds-airport-lowi", root, orig)

    def test_small_statics_file_is_not_a_full_replacement(self):
        """Un petit fichier statics à côté d'un gros fichier de base reste un simple renommage."""
        d = "scenery"
        make_pkg(self.community, "x-scene", "XXXX", [
            (f"{d}/x-scene.bgl", b"A" * 5000, True), (f"{d}/x-scene-statics.off", b"S" * 20, False)])
        g = self.scan()["x-scene"].groups[0]
        self.assertEqual((g.mode, g.state), ("rename", m.OFF))

    # G. Homa Sim : X.bgl actif + X-statics + X-nostatics désactivés
    def test_three_way_variant(self):
        root = make_pkg(self.community, "homasim-airport-oiaw", "OIAW", [
            ("scenery/oiaw-airport.bgl", b"S" * 170, True),
            ("scenery/oiaw-airport-statics.bgl.off", b"S" * 170, False),
            ("scenery/oiaw-airport-nostatics.off", b"N" * 169, False)])
        orig = self.files(root)
        g = self.scan()["homasim-airport-oiaw"].groups[0]
        self.assertEqual((g.mode, g.state), ("variant", m.ON))
        m.set_scene_state(self.scan()["homasim-airport-oiaw"], m.OFF)
        self.assertEqual((root / "scenery/oiaw-airport.bgl").read_bytes(), b"N" * 169)
        self.assertEqual(len(list((root / "scenery").iterdir())), 3)    # aucun fichier ajouté ni chargé en double
        self.cycle("homasim-airport-oiaw", root, orig)

    def test_three_way_without_base_is_left_alone(self):
        make_pkg(self.community, "homasim-airport-oiie", "OIIE", [
            ("scenery/oiie-airport-statics.bgl.off", b"S" * 9, False),
            ("scenery/oiie-airport-nostatics.off", b"N" * 9, False)])
        sc = self.scan()["homasim-airport-oiie"]
        self.assertEqual((sc.state, sc.groups[0].note), (m.CONFLICT, "note_negation"))

    # H. Cas laissés à la main
    def test_cases_left_alone(self):
        make_pkg(self.community, "propair-ebci", "EBCI", [("scenery/EBCI_NoStaticAircraft.bgl", b"N" * 9, True)])
        make_pkg(self.community, "orbx-kbur", "KBUR", [
            ("scenery/Orbx/kbur/Xml_Placements_With_Static_Aircraft.bgl", b"S" * 9, False),
            ("scenery/Orbx/kbur/other.bgl", b"O" * 9, True)])
        make_pkg(self.community, "pyreegue-egaa", "EGAA", [
            ("Contrail/src/statics-off.config.off", b"", False), ("Contrail/src/statics-on.config", b"", False)])
        make_pkg(self.community, "atelic-lipz", "LIPZ", [("Scenery/atelic/modelib_People_static.BGL", b"P" * 9, True)])
        make_pkg(self.community, "orbx-katl", "KATL", [
            ("Scenery/katl/placement/placement_full_gse_rampguy_static_flatten.bgl", b"F" * 9, True)])
        scenes = self.scan()
        self.assertEqual(scenes["propair-ebci"].groups[0].note, "note_negation")
        self.assertEqual(scenes["orbx-kbur"].groups[0].note, "note_not_in_layout")
        for name in ("pyreegue-egaa", "atelic-lipz", "orbx-katl"):
            self.assertFalse(name in scenes and scenes[name].groups, name)


if __name__ == "__main__":
    unittest.main()
