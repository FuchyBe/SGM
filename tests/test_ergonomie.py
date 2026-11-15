# -*- coding: utf-8 -*-
"""Ergonomie v0.9.3 : menus Paramètres / Outils / Aide, raccourcis, question de mise à jour dans un bandeau,
colonne GSX allégée, fenêtre Dossiers en sections."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from helpers import SandboxTest, make_pkg, m  # noqa: E402

APP = QApplication.instance() or QApplication([])


class ErgonomieTest(SandboxTest):
    def window(self):
        w = m.MainWindow()
        self.addCleanup(lambda: (w.close(), w.deleteLater(), APP.processEvents()))
        return w

    def test_trois_menus_et_leur_contenu(self):
        w = self.window()
        titles = [a.text() for a in w.menuBar().actions()]
        self.assertEqual(titles, [m.tr("m_settings"), m.tr("m_tools"), m.tr("m_help")])
        tools = [a.data() for a in w.tools_menu.actions() if a.data()]
        for k in ("m_scan", "m_install_arch", "m_undo", "m_restore_all", "m_stats_report", "m_backups", "m_open_log"):
            self.assertIn(k, tools)
        helps = [a.data() for a in w.help_menu.actions() if a.data()]
        self.assertEqual(helps, ["m_guide", "m_report_bug", "m_suggest", "m_check_updates", "m_disclaimer",
                                 "m_licenses", "m_donate", "m_about"])
        sub = [a.menu() for a in w.tools_menu.actions() if a.menu()]
        self.assertEqual([x.title() for x in sub], [m.tr("btn_profiles")])
        sub[0].aboutToShow.emit()                              # profils de statics construits dans le sous-menu
        self.assertTrue(any(a.text() == m.tr("prof_save") for a in sub[0].actions()))

    def test_raccourcis(self):
        w = self.window()
        seqs = {a.shortcut().toString() for a in w.actions() + w.tools_menu.actions() + w.help_menu.actions()}
        for k in ("Ctrl+Z", "F5", "F1", QKeySequence(QKeySequence.Find).toString()):
            self.assertIn(k, seqs)
        self.assertIn(QKeySequence(Qt.Key_Escape).toString(), seqs)

    def test_echap_vide_la_recherche_puis_les_filtres(self):
        w = self.window()
        w.search.setText("ebbr")
        w.new_chip.setChecked(True)
        w.escape_pressed()
        self.assertEqual(w.search.text(), "")
        self.assertTrue(w.new_chip.isChecked())
        w.escape_pressed()
        self.assertFalse(w.new_chip.isChecked())
        w.focus_search()                                       # Ctrl+F

    def test_question_de_mise_a_jour_dans_un_bandeau(self):
        old, m.UPDATE_DISABLED = m.UPDATE_DISABLED, False
        asked, old_ask = [], m.ask
        m.ask = lambda *a, **k: asked.append(a) or True
        try:
            w = self.window()
            w.config.update_check = None
            w.check_updates = lambda manual: asked.append("check")
            w.maybe_check_updates()
            self.assertFalse(w.upd_banner.isHidden())          # pas de fenêtre bloquante au démarrage
            self.assertEqual(asked, [])
            w.answer_update_question(False)
            self.assertTrue(w.upd_banner.isHidden())
            self.assertIs(w.config.update_check, False)
            self.assertFalse(w.update_auto_act.isChecked())
            self.assertIs(m.Config().update_check, False)       # réponse enregistrée
        finally:
            m.UPDATE_DISABLED, m.ask = old, old_ask

    def test_colonne_gsx_allegee(self):
        make_pkg(self.community, "test-ebbr", "Brussels EBBR", [("scenery/EBBR_statics.bgl", b"S" * 40, True)])
        row = m.SceneRow(self.scan()["test-ebbr"], gsx_folder_fn=lambda: str(self.gsx))
        row.refresh_gsx()
        self.assertEqual(row.gsx_note._full, "")                # plus de seconde ligne « Rechercher … »
        btn = [b for b in row.gsx_btns if b.objectName() == "searchBtn"]
        self.assertEqual(len(btn), 1)
        self.assertIn("EBBR", btn[0].toolTip())                 # l'info reste dans l'infobulle

    def test_dossiers_en_sections(self):
        d = m.FoldersDialog(m.Config(), [])
        heads = [x.text() for x in d.findChildren(QLabel) if x.objectName() == "h2" and not x.isHidden()]
        self.assertEqual(heads[:2], [m.tr("sec_scenery"), m.tr("gsx_dest")])
        self.assertEqual(len(heads), 3)
        self.assertNotIn("—", heads[2])
        d.deleteLater()
        APP.processEvents()
        self.assertIn("QLabel#h2", m.QSS)
