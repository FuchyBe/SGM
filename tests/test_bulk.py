# -*- coding: utf-8 -*-
"""Tout ON / Tout OFF : seulement les cas simples, jamais les scènes « À vérifier »."""
from types import SimpleNamespace as NS

from helpers import SandboxTest, m


def row(state, check=False, toggleable=True, modes=("rename",)):
    scene = NS(state=state, toggleable=toggleable, groups=[NS(mode=x) for x in modes], title=state)
    key = "check" if check else {m.ON: "on", m.OFF: "off"}.get(state, "check")
    return NS(scene=scene, statics_state=lambda k=key: k)


class BulkTest(SandboxTest):
    def test_cas_simples_uniquement(self):
        rows = [row(m.ON), row(m.OFF), row(m.MIXED), row(m.CONFLICT, modes=("conflict",)),
                row(m.OFF), NS(scene=NS(state=m.NONE, toggleable=False, groups=[]), statics_state=lambda: "none")]
        targets, skipped = m.bulk_targets(rows, m.ON)
        self.assertEqual([s.state for s in targets], [m.OFF, m.OFF])
        self.assertEqual(skipped, 2)                     # mixte + conflit : à faire à la main
        targets, _ = m.bulk_targets(rows, m.OFF)
        self.assertEqual([s.state for s in targets], [m.ON])

    def test_conflit_dans_une_scene_on_off(self):
        targets, _ = m.bulk_targets([row(m.OFF, modes=("rename", "conflict"))], m.ON)
        self.assertEqual(targets, [])


if __name__ == "__main__":
    import unittest
    unittest.main()
