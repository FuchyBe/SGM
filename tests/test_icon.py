"""Icône de l'application (proposition C) : rendu à toutes les tailles et fichier .ico valide."""
import os, struct, sys, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtWidgets import QApplication
import statics_manager as sm

APP = QApplication.instance() or QApplication([])


class IconTest(unittest.TestCase):
    def test_rendu_toutes_tailles(self):
        for n in sm.ICON_SIZES:
            img = sm.logo_image(n)
            self.assertEqual((img.width(), img.height()), (n, n))
            # Coin transparent, centre peint
            self.assertEqual(img.pixelColor(0, 0).alpha(), 0)
            self.assertGreater(img.pixelColor(n // 2, n // 2).alpha(), 0)
        self.assertGreaterEqual(len(sm.make_icon().availableSizes()), len(sm.ICON_SIZES))

    def test_fichier_ico(self):
        path = os.path.join(ROOT, "assets", "SGM.ico")
        with open(path, "rb") as f:
            data = f.read()
        zero, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((zero, kind), (0, 1))
        sizes = set()
        for k in range(count):
            w, h, _, _, _, _, ln, off = struct.unpack("<BBBBHHII", data[6 + 16 * k: 22 + 16 * k])
            sizes.add(w or 256)
            self.assertEqual(data[off:off + 8], b"\x89PNG\r\n\x1a\n")
            self.assertLessEqual(off + ln, len(data))
        self.assertTrue({16, 32, 48, 256} <= sizes)


if __name__ == "__main__":
    unittest.main()
