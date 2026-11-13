# -*- coding: utf-8 -*-
"""Outils communs aux tests : fausses scènes MSFS, dossiers temporaires isolés."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import statics_manager as m  # noqa: E402

FILETIME_EPOCH = 116444736000000000


def profile(tag: str) -> bytes:
    """Contenu minimal d'un profil GSX reconnu par SGM."""
    return f"[general]\n[section.1]\npushback={tag}\nmaxwingspan=80\n".encode()


def make_pkg(base: Path, folder: str, title: str, files=(), creator: str = "Test Studio",
             ctype: str = "SCENERY") -> Path:
    """Crée une scène : files = [(chemin relatif, contenu bytes, dans_layout bool)]."""
    root = base / folder
    root.mkdir(parents=True, exist_ok=True)
    content = []
    for rel, data, in_layout in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        if in_layout:
            st = p.stat()
            content.append({"path": rel, "size": st.st_size, "date": st.st_mtime_ns // 100 + FILETIME_EPOCH})
    (root / "layout.json").write_text(json.dumps({"content": content}, indent=2))
    total = sum(c["size"] for c in content)
    (root / "manifest.json").write_text(json.dumps({
        "title": title, "creator": creator, "content_type": ctype,
        "total_package_size": str(total).zfill(20)}, indent=2))
    return root


def read_layout(root: Path) -> list:
    return [c["path"] for c in json.loads((root / "layout.json").read_text())["content"]]


def manifest_size(root: Path) -> int:
    return int(json.loads((root / "manifest.json").read_text())["total_package_size"])


class SandboxTest(unittest.TestCase):
    """Chaque test travaille dans un dossier temporaire : données SGM, APPDATA et HOME isolés."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sgm_test_"))
        self.data = self.tmp / "SGM_data"
        self.data.mkdir()
        self._old_data = m._DATA_DIR
        m._DATA_DIR = self.data
        self._old_env = {k: os.environ.get(k) for k in ("APPDATA", "LOCALAPPDATA", "HOME")}
        os.environ["APPDATA"] = str(self.tmp / "roaming")
        os.environ["LOCALAPPDATA"] = str(self.tmp / "local")
        os.environ["HOME"] = str(self.tmp / "home")
        (self.tmp / "home" / "Downloads").mkdir(parents=True)
        self.gsx = self.tmp / "roaming" / "Virtuali" / "GSX" / "MSFS2024"
        self.gsx.mkdir(parents=True)
        self.community = self.tmp / "Community"
        self.community.mkdir()
        m._hash_cache.clear()
        m.set_lang("en")

    def tearDown(self):
        m._DATA_DIR = self._old_data
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self, path: Path | None = None):
        src = m.Source(m.MANUAL, path or self.community, False, True)
        return {s.folder: s for s in m.scan_all([src])}
