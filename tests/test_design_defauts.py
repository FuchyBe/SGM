# -*- coding: utf-8 -*-
"""Défauts d'interface relevés par le designer (2026-11-15)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from helpers import SandboxTest, m  # noqa: E402

APP = QApplication.instance() or QApplication([])


class DesignTest(SandboxTest):
    def test_en_tete_hors_de_la_zone_qui_defile(self):
        w = m.MainWindow()
        p, inside = w.col_header.parent(), False
        while p is not None:
            inside = inside or p is w.scroll
            p = p.parent()
        self.assertFalse(inside)                              # reste visible quand on fait défiler la liste
        w.resize(1280, 700)
        APP.processEvents()
        w.layout_columns()
        self.assertEqual(w.col_header.width(), w._avail_width())
        w.close()
        w.deleteLater()
        APP.processEvents()

    def test_contraste_des_petits_textes(self):
        for sel in ("QLabel#colHead {", "QLabel#note {", "QLabel#none {"):
            line = next(l for l in m.QSS.splitlines() if l.startswith(sel))
            self.assertIn(m.C["muted"], line)                 # 6:1 au lieu de 3:1

    def test_noms_de_fichiers_lisibles_en_arabe(self):
        s = m.ltr_fragments("إعادة تسمية  .bgl ↔ .bgl.off")
        self.assertIn("‪.bgl ↔ .bgl.off‬", s)
        self.assertEqual(m.ltr_fragments("Renommage"), "Renommage")

    def test_en_tete_court_en_fenetre_etroite(self):
        h = m.ColumnHeader()
        h.set_compact(True)
        self.assertEqual((h.bulk_btns[m.OFF].text(), h.bulk_btns[m.ON].text()), ("OFF", "ON"))
        h.set_compact(False)
        self.assertEqual(h.bulk_btns[m.OFF].text(), m.tr("btn_all_off"))

    def test_gsx_cede_avant_statics(self):
        ws, wg = m.fit_widths(900, (400, 300), (300, 150))
        self.assertEqual(ws, 400 - max(0, (400 + 300) - (900 - m.COL_SCENE_MIN - m.COL_OVERHEAD) - 150))
        self.assertLess(wg, 300)

    def test_case_cochee_avec_coche(self):
        cb = m.CheckBox("x")
        cb.setChecked(True)
        self.assertFalse(cb.grab().isNull())


if __name__ == "__main__":
    import unittest
    unittest.main()
