# -*- coding: utf-8 -*-
"""
SGM — Statics & GSX Manager — MSFS 2024 / MSFS 2020 (application portable)
Auteur : Fabian Fuchs

Active ou désactive les avions statiques des scènes installées dans les
dossiers Community (et dans des dossiers ajoutés manuellement), et gère
les profils GSX livrés avec les scènes.

Statics, deux méthodes :
  1. Renommage : xxx_statics.bgl  <->  xxx_statics.bgl.off
  2. Variantes : statics_on.bgl + statics_off.bgl + statics.bgl (actif)
layout.json (et total_package_size du manifest.json) sont mis à jour
comme le ferait MSFSLayoutGenerator.

Portable : réglages et sauvegardes dans « SGM_data » à côté
de l'application. Chaque simulateur (2024 / 2020) a sa propre mémoire.
Interface en 12 langues (anglais par défaut) : voir i18n.py.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import logging
import logging.handlers
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus, urlencode
import platform
from pathlib import Path, PurePosixPath, PureWindowsPath

from PySide6.QtCore import (QEvent, Property, QEasingCurve, QPropertyAnimation, QRectF,
                            QSize, Qt, QThread, QTimer, QUrl, Signal)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QFontMetricsF,
                           QIcon, QKeySequence, QImage, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup, QCheckBox, QComboBox, QCompleter,
                               QInputDialog, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QPlainTextEdit, QProgressDialog,
                               QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QSizePolicy, QStyle, QStyleOptionButton,
                               QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

from i18n import LANGS, RTL_LANGS, get_lang, set_lang, tr

APP_NAME = "SGM"
APP_FULL = "Statics & GSX Manager"
APP_VERSION = "1.0"
APP_AUTHOR = "Fabian Fuchs"
# Lien de don public (PayPal.me)
DONATE_URL = "https://paypal.me/Fuchy"
# Signalements : Issues publiques du dépôt FuchyBe/SGM
ISSUES_NEW_URL = "https://github.com/FuchyBe/SGM/issues/new"

# Recherche de profils GSX : recherche web limitée à flightsim.to. Les recherches directes du site ne marchent
# pas depuis un lien (vérifié par Fabian le 2026-11-14 : /search/?keyword= ignore le mot-clé, /discover/… = 404).
SEARCH_URL = "https://www.google.com/search?q=site%3Aflightsim.to+{q}"


def search_url(query: str) -> str:
    return SEARCH_URL.format(q=quote_plus(query))


FILETIME_EPOCH = 116444736000000000  # 1601-01-01 -> 1970-01-01 en unités de 100 ns
MAX_BACKUPS_PER_SCENE = 10

ON, OFF, UNKNOWN, CONFLICT, MIXED, NONE = "on", "off", "unknown", "conflict", "mixed", "none"
GSX_MISSING, GSX_SAME, GSX_DIFF = "missing", "same", "diff"
GSX_MARKERS = ("pushback", "maxwingspan", "jetway", "parking", "deice", "stairs")
GSX_NAME_RE = re.compile(r"^[a-z0-9]{3,4}-[^.]+\.ini$", re.IGNORECASE)
MANUAL = "@manual"   # étiquette de source traduite à l'affichage

# Simulateurs pris en charge
SIMS = {
    "MSFS 2024": {
        "usercfg": [("LOCALAPPDATA", ("Packages", "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt")),
                    ("APPDATA", ("Microsoft Flight Simulator 2024", "UserCfg.opt"))],
        # MSFS 2024 lit Community (add-ons au format 2020) et Community2024
        "communities": ("Community", "Community2024"),
        "process": "flightsimulator2024.exe",
        "gsx": ("MSFS2024", "MSFS"),
    },
    "MSFS 2020": {
        "usercfg": [("LOCALAPPDATA", ("Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt")),
                    ("APPDATA", ("Microsoft Flight Simulator", "UserCfg.opt"))],
        "communities": ("Community",),
        "process": "flightsimulator.exe",
        "gsx": ("MSFS",),
    },
}
DEFAULT_SIM = "MSFS 2024"

# "statics_on", "Statics-OFF", "EBBR_staticsON", "statics.off"...
VARIANT_RE = re.compile(r"(statics)[ _\-.]*(on|off)(?![a-z0-9])", re.IGNORECASE)


def default_gsx_folder(sim: str) -> str:
    base = Path(os.environ.get("APPDATA") or str(Path.home() / ".config")) / "Virtuali" / "GSX"
    names = SIMS[sim]["gsx"]
    for n in names:
        if (base / n).is_dir():
            return str(base / n)
    return str(base / names[-1])


# ════════════════════════════════════════════════════════════════════════════
#  Configuration (portable, une mémoire par simulateur)
# ════════════════════════════════════════════════════════════════════════════

def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # exécutable PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


_DATA_DIR: Path | None = None


# ════════════════════════════════════════════════════════════════════════════
#  Journal local (SGM_data/logs/sgm.log) — jamais de chemin personnel
# ════════════════════════════════════════════════════════════════════════════

LOG = logging.getLogger("sgm")
LOG.addHandler(logging.NullHandler())
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 4                                   # sgm.log + 4 anciens = 5 Mo au maximum
_USERS_RE = re.compile(r"(?:[A-Za-z]:|[\\/]{2}[^\\/\s]+[\\/]+[A-Za-z]\$)[\\/]+Users[\\/]+[^\\/\r\n\"<>|:*?]+",
                       re.I)   # espaces et apostrophes permis ; aussi \\PC\c$\Users\nom
_HOME_RE = re.compile(r"(?<![\w.])/(?:home|Users)/[^/\s\"']+")


def scrub(text: str) -> str:
    """Retire du texte le dossier personnel (nom d'utilisateur Windows compris) : remplacé par « ~ »."""
    text = str(text)
    for home in {str(Path.home()), os.environ.get("USERPROFILE", "")}:
        if home and len(home) > 3:
            for h in {home, home.replace("\\", "/")}:
                text = re.sub(re.escape(h), "~", text, flags=re.I)
    text = _USERS_RE.sub("~", text)
    return _HOME_RE.sub("~", text)


class ScrubFormatter(logging.Formatter):
    def format(self, record):
        return scrub(super().format(record))


def log_dir() -> Path:
    return data_dir() / "logs"


def log_file() -> Path:
    return log_dir() / "sgm.log"


def setup_logging() -> bool:
    """Active le journal tournant. Sans effet si le dossier n'est pas inscriptible."""
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in LOG.handlers):
        return True
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(log_file(), maxBytes=LOG_MAX_BYTES,
                                                 backupCount=LOG_BACKUPS, encoding="utf-8")
    except OSError:
        return False
    h.setFormatter(ScrubFormatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
    LOG.addHandler(h)
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    previous = sys.excepthook

    def hook(kind, value, tb):
        LOG.critical("Erreur inattendue", exc_info=(kind, value, tb))
        previous(kind, value, tb)
    sys.excepthook = hook
    return True


def close_logging():
    for h in [h for h in LOG.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]:
        h.close()
        LOG.removeHandler(h)


def scene_label(scene) -> str:
    return f"{scene.title} [{scene.root.name}]"


def license_dir() -> Path:
    """Dossier « licenses » livré à côté du programme (ou dans le paquet PyInstaller)."""
    for base in (app_dir(), Path(getattr(sys, "_MEIPASS", app_dir()))):
        if (base / "licenses").is_dir():
            return base / "licenses"
    return app_dir() / "licenses"


# Version installée (installeur Inno Setup) : un fichier repère à côté de SGM.exe. Sans lui = version portable.
INSTALL_MARKER = "SGM.installed"
INSTALL_APP_ID = "{6F1C2B7E-5A43-4D2B-9C1E-7B3F0A9D4E21}"       # identique à installer/SGM.iss (AppId)
FRESH_DATA = False          # fixé par main() : aucune donnée SGM avant ce lancement


def is_installed() -> bool:
    return (app_dir() / INSTALL_MARKER).is_file()


def user_data_dir() -> Path:
    """Données de la version installée : %APPDATA%\\SGM."""
    return Path(os.environ.get("APPDATA") or str(Path.home() / ".config")) / "SGM"


def data_dir() -> Path:
    """Version portable : SGM_data à côté de l'application (repli sur %APPDATA% s'il n'est pas inscriptible).
    Version installée : toujours %APPDATA%\\SGM (le dossier du programme ne garde que le programme)."""
    global _DATA_DIR
    if _DATA_DIR is None:
        if is_installed():
            d = user_data_dir()
            d.mkdir(parents=True, exist_ok=True)
            _DATA_DIR = d
            return d
        d = app_dir() / "SGM_data"
        old = app_dir() / "StaticsManager_data"          # nom des premières betas
        if old.is_dir() and not d.exists():
            try:
                old.rename(d)
            except OSError:
                pass
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError:
            base = Path(os.environ.get("APPDATA") or str(Path.home() / ".config"))
            d = base / "SGM"
            if (base / "StaticsManager").is_dir() and not d.exists():
                try:
                    (base / "StaticsManager").rename(d)
                except OSError:
                    pass
            d.mkdir(parents=True, exist_ok=True)
        _DATA_DIR = d
    return _DATA_DIR


# ── Reprise des données d'une version portable (copie, jamais de déplacement) ──
IMPORT_SKIP = {"update", ".write_test"}               # téléchargements de mise à jour : inutiles


def find_portable_data(folder) -> Path | None:
    """Dossier SGM_data d'une version portable : le dossier choisi lui-même, ou SGM_data / StaticsManager_data
    à l'intérieur. Il doit contenir config.json. None sinon."""
    f = Path(folder)
    for cand in (f, f / "SGM_data", f / "StaticsManager_data"):
        try:
            if (cand / "config.json").is_file():
                return cand
        except OSError:
            continue
    return None


def has_user_data(d: Path) -> bool:
    return (Path(d) / "config.json").is_file()


def import_portable(src: Path, dst: Path) -> int:
    """Copie les données portables `src` dans `dst` (réglages, profils, sauvegardes, états d'origine, Annuler,
    journal). La source n'est jamais modifiée. Les fichiers de `dst` du même nom sont remplacés.
    Copie d'abord dans un dossier temporaire voisin : en cas d'erreur, `dst` reste tel quel. Rend le nombre
    de fichiers copiés."""
    src, dst = Path(src), Path(dst)
    if norm_key(src) == norm_key(dst) or norm_key(dst).startswith(norm_key(src) + os.sep):
        raise ValueError("same folder")
    dst.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / (dst.name + ".import-tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    n = 0
    try:
        for item in src.iterdir():
            if item.name in IMPORT_SKIP or item.is_symlink():
                continue
            if item.is_dir():
                shutil.copytree(item, tmp / item.name, symlinks=False, copy_function=shutil.copy2,
                                ignore=lambda _d, names: [x for x in names if x == ".write_test"])
            else:
                tmp.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, tmp / item.name)
        n = sum(1 for p in tmp.rglob("*") if p.is_file()) if tmp.exists() else 0
        if tmp.exists():
            shutil.copytree(tmp, dst, dirs_exist_ok=True, copy_function=shutil.copy2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n


def norm_key(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _empty_profile() -> dict:
    return {"manual_folders": [], "known_scenes": [], "gsx_folder": "", "gsx_choices": {}, "scanned": False,
            "statics_profiles": {}}


def _clean_statics_profiles(raw) -> dict:
    out = {}
    if isinstance(raw, dict):
        for name, states in list(raw.items())[:30]:
            if isinstance(states, dict) and str(name).strip():
                out[str(name).strip()[:40]] = {str(k): v for k, v in states.items() if v in ("on", "off")}
    return out


class Config:
    def __init__(self):
        self.file = data_dir() / "config.json"
        self.lang = "en"
        self.check_downloads = True
        self.archive_cleanup = "ask"          # après installation depuis Téléchargements : ask / auto / never
        self.seen_archives: list = []
        self.download_folders: list = []      # vide = dossier Téléchargements de Windows
        self.update_check = None              # None = à demander au 1er lancement ; True / False = choix
        self.update_last = 0.0
        self.update_skip = ""
        self.col_fs, self.col_fg = COL_STATICS_W / COL_REF_W, COL_GSX_W / COL_REF_W
        self.col_auto = True                  # colonnes ajustées au texte ; False après un réglage à la main
        self.sim = DEFAULT_SIM
        self.profiles: dict = {}
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if isinstance(data, dict):
            if int(data.get("version", 1)) >= 3:
                self.lang = str(data.get("lang") or "en")
                self.check_downloads = bool(data.get("check_downloads", True))
                if data.get("archive_cleanup") in ARCHIVE_CLEANUP:
                    self.archive_cleanup = data["archive_cleanup"]
                cols = data.get("columns") or {}
                self.col_auto = cols.get("auto", True) is not False
                try:
                    fs, fg = float(cols.get("statics", self.col_fs)), float(cols.get("gsx", self.col_fg))
                    if 0.1 <= fs <= 0.6 and 0.1 <= fg <= 0.7 and fs + fg <= 0.85:
                        self.col_fs, self.col_fg = fs, fg
                except (TypeError, ValueError):
                    pass
                self.seen_archives = [str(x) for x in data.get("seen_archives", [])][-300:]
                self.download_folders = [str(x) for x in data.get("download_folders", []) if str(x).strip()][:10]
                uc = data.get("update_check")
                self.update_check = uc if isinstance(uc, bool) else None
                try:
                    self.update_last = float(data.get("update_last") or 0)
                except (TypeError, ValueError):
                    self.update_last = 0.0
                self.update_skip = str(data.get("update_skip") or "")
                self.sim = data.get("sim") if data.get("sim") in SIMS else DEFAULT_SIM
                for sim, p in (data.get("profiles") or {}).items():
                    if sim in SIMS and isinstance(p, dict):
                        prof = _empty_profile()
                        prof.update({
                            "manual_folders": [str(x) for x in p.get("manual_folders", [])],
                            "known_scenes": [str(x) for x in p.get("known_scenes", [])],
                            "gsx_folder": str(p.get("gsx_folder") or ""),
                            "gsx_choices": {str(k): str(v) for k, v in (p.get("gsx_choices") or {}).items()},
                            "scanned": bool(p.get("scanned")),
                            "statics_profiles": _clean_statics_profiles(p.get("statics_profiles")),
                        })
                        self.profiles[sim] = prof
            else:   # ancienne version (MSFS 2024 uniquement) -> profil 2024
                prof = _empty_profile()
                prof.update({
                    "manual_folders": [str(x) for x in data.get("manual_folders", [])],
                    "known_scenes": [str(x) for x in data.get("known_scenes", [])],
                    "gsx_folder": str(data.get("gsx_folder") or ""),
                    "gsx_choices": {str(k): str(v) for k, v in (data.get("gsx_choices") or {}).items()},
                    "scanned": True,
                })
                self.profiles["MSFS 2024"] = prof

    # ── profil du simulateur actif
    @property
    def p(self) -> dict:
        return self.profiles.setdefault(self.sim, _empty_profile())

    @property
    def manual_folders(self) -> list:
        return self.p["manual_folders"]

    @manual_folders.setter
    def manual_folders(self, v):
        self.p["manual_folders"] = list(v)

    @property
    def known_scenes(self) -> list:
        return self.p["known_scenes"]

    @known_scenes.setter
    def known_scenes(self, v):
        self.p["known_scenes"] = list(v)

    @property
    def gsx_override(self) -> str:
        return self.p["gsx_folder"]

    @gsx_override.setter
    def gsx_override(self, v):
        self.p["gsx_folder"] = str(v or "")

    @property
    def gsx_choices(self) -> dict:
        return self.p["gsx_choices"]

    @property
    def statics_profiles(self) -> dict:
        """Profils de statics de ce simulateur : nom -> {clé de scène: "on" / "off"}."""
        return self.p.setdefault("statics_profiles", {})

    @property
    def first_run(self) -> bool:
        return not self.p["scanned"]

    @first_run.setter
    def first_run(self, v):
        self.p["scanned"] = not v

    def gsx_folder(self) -> str:
        return self.gsx_override or default_gsx_folder(self.sim)

    def download_dirs(self) -> list:
        """Dossiers où chercher les archives de profils GSX (le premier sert aussi de dossier par défaut)."""
        return [Path(f) for f in self.download_folders] or [downloads_dir()]

    def save(self):
        data = {"version": 3, "lang": self.lang, "sim": self.sim,
                "check_downloads": self.check_downloads, "seen_archives": self.seen_archives[-300:],
                "archive_cleanup": self.archive_cleanup, "download_folders": self.download_folders,
                "update_check": self.update_check, "update_last": self.update_last, "update_skip": self.update_skip,
                "columns": {"auto": self.col_auto, "statics": self.col_fs, "gsx": self.col_fg},
                "profiles": {}}
        for sim, p in self.profiles.items():
            q = dict(p)
            q["known_scenes"] = sorted(set(p["known_scenes"]))
            data["profiles"][sim] = q
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.file)


# ════════════════════════════════════════════════════════════════════════════
#  Dossiers sources
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Source:
    label: str
    path: Path
    auto: bool
    exists: bool = True


# ════════════════════════════════════════════════════════════════════════════
#  Points d'accroche pour une application hôte (3AM) — fiche docs/rd/2026-11-15-accroches-3am.md
#  Tous à None / False : aucun effet sur SGM seul.
# ════════════════════════════════════════════════════════════════════════════

HOST_REPLACE = None       # S1 : fonction(state) appelée au lieu de recréer la fenêtre (changement de langue…)
EXTRA_SOURCES = None      # S2 : [(étiquette, chemin)] ou fonction(config) -> [(étiquette, chemin)]
REAL_ROOTS = False        # S3 : analyser les paquets par leur chemin réel (liens / jonctions résolus)
HOST_CONFIRM_SIM = None   # S11 : fonction(parent) -> bool appelée avant chaque écriture, à la place du contrôle de SGM
HOST_HELP_ITEMS = None    # S12 : clés des entrées du menu Aide à garder (None = toutes)


def hosted() -> bool:
    """SGM est embarqué dans une application hôte (3AM)."""
    return HOST_REPLACE is not None


USERCFG_MAX = 256 * 1024


def parse_usercfg(cfg: Path) -> Path | None:
    """Dossier des paquets (InstalledPackagesPath) de UserCfg.opt. Fichier anormal ou chemin douteux : None (S9)."""
    try:
        if cfg.stat().st_size > USERCFG_MAX:
            return None
        text = cfg.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("installedpackagespath"):
            m = re.search(r'"([^"]+)"', s)
            if m:
                val = m.group(1)
            else:
                parts = s.split(None, 1)
                val = parts[1] if len(parts) == 2 else ""
            val = val.strip().strip('"').strip()
            if not val or len(val) > 260 or any(ord(ch) < 32 for ch in val) or "*" in val or "?" in val:
                return None
            path = Path(val)
            return path if (path.is_absolute() or os.name != "nt" and val.startswith("/")) else None
    return None


def find_sources(config: Config) -> list[Source]:
    sim = SIMS[config.sim]
    out, seen = [], set()
    for env, parts in sim["usercfg"]:
        base = os.environ.get(env)
        if not base:
            continue
        cfg = Path(base).joinpath(*parts)
        if not cfg.is_file():
            continue
        pkg = parse_usercfg(cfg)
        if not pkg:
            continue
        for i, name in enumerate(sim["communities"]):
            folder = pkg / name
            k = norm_key(folder)
            if k in seen:
                continue
            if i > 0 and not folder.is_dir():    # dossiers secondaires : seulement s'ils existent
                continue
            seen.add(k)
            out.append(Source(name, folder, True, folder.is_dir()))
    for f in config.manual_folders:
        k = norm_key(f)
        if k in seen:
            continue
        seen.add(k)
        out.append(Source(MANUAL, Path(f), False, Path(f).is_dir()))
    if EXTRA_SOURCES:                          # accroche S2 : bibliothèques de l'application hôte
        try:
            extra = EXTRA_SOURCES(config) if callable(EXTRA_SOURCES) else EXTRA_SOURCES
            for label, f in extra or []:
                k = norm_key(f)
                if k in seen:
                    continue
                seen.add(k)
                out.append(Source(str(label), Path(f), False, Path(f).is_dir()))
        except Exception as e:
            LOG.warning("Sources de l'hôte ignorées : %s", e)
    return out


def display_source(label: str) -> str:
    return label.replace(MANUAL, tr("manual"))


# ════════════════════════════════════════════════════════════════════════════
#  Analyse des scènes
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class StaticsGroup:
    mode: str              # "rename" | "variant" | "swap" | "pair" | "conflict"
    directory: Path
    active: Path           # fichier actuel (rename) / statics.bgl actif (variant) / X.bgl (swap, pair)
    state: str
    on_file: Path | None = None    # variant : variante ON / swap : X.bgl.static
    off_file: Path | None = None   # variant : variante OFF / swap : X.bgl.nostatic
    note: str = ""         # clé de traduction
    on_path: Path | None = None    # rename, pair : chemin activé (.bgl)
    off_path: Path | None = None   # rename, pair : chemin désactivé (.bgl.off, .off, .bgl.disabled…)
    alt_on: Path | None = None     # pair : fichier « sans statics » activé
    alt_off: Path | None = None    # pair : fichier « sans statics » désactivé
    twin: bool = False     # rename : copie désactivée identique présente à côté du .bgl actif
    alt_static: bool = False   # swap : la version de rechange est celle AVEC statics (UK2000 .bgl.staticq)

    @property
    def toggleable(self) -> bool:
        return self.mode in ("rename", "variant", "swap", "rswap", "pair")

    def paths(self) -> list:
        """Tous les fichiers concernés qui existent sur le disque."""
        out = []
        for p in (self.active, self.on_file, self.off_file, self.on_path, self.off_path, self.alt_on, self.alt_off):
            if p is not None and p.is_file() and p not in out:
                out.append(p)
        return out

    @property
    def off_form(self) -> str:
        if self.off_path is None:
            return ""
        return parse_form(self.off_path.name)[1] or ""


@dataclass
class Scene:
    root: Path
    folder: str
    title: str
    creator: str
    source: str
    groups: list = field(default_factory=list)
    is_new: bool = False
    gsx_files: list = field(default_factory=list)
    gsx_variants: list = field(default_factory=list)
    icao: str = ""              # code OACI détecté (EBBR…), vide si inconnu
    is_airport: bool = False

    @property
    def key(self) -> str:
        return norm_key(self.root)

    @property
    def toggleable(self) -> bool:
        return any(g.toggleable for g in self.groups)

    @property
    def state(self) -> str:
        if not self.groups:
            return NONE
        states = {g.state for g in self.groups if g.toggleable}
        if not states:
            return CONFLICT
        if states == {ON}:
            return ON
        if states == {OFF}:
            return OFF
        return MIXED


_hash_cache: dict = {}


def file_hash(p: Path) -> str:
    st = p.stat()
    k = (norm_key(p), st.st_size, st.st_mtime_ns)
    h = _hash_cache.get(k)
    if h is None:
        d = hashlib.sha1()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                d.update(chunk)
        h = d.hexdigest()
        _hash_cache[k] = h
    return h


def forget_hash(p: Path):
    """À appeler après toute écriture : la taille et la date ne suffisent pas
    (copy2 conserve la date, et les variantes ont souvent la même)."""
    k = norm_key(p)
    for key in [x for x in _hash_cache if x[0] == k]:
        del _hash_cache[key]


def same_content(a: Path, b: Path) -> bool:
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        return file_hash(a) == file_hash(b)
    except OSError:
        return False


def split_ext(name: str):
    low = name.lower()
    if low.endswith(".bgl.off"):
        return name[:-8], ".bgl.off"
    if low.endswith(".bgl"):
        return name[:-4], ".bgl"
    return None, None


# Règles de détection (base des cas réels : docs/analyses/BASE.md)
STATIC_WORD_RE = re.compile(r"static|parked", re.IGNORECASE)
NEG_RE = re.compile(r"(?:no|without)[ _\-]?(statics?)", re.IGNORECASE)          # nostatic, no_static, without_static
EXCLUDE_RE = re.compile(r"model[ _\-]?lib|modelib|library|flatten|exclu", re.IGNORECASE)   # bibliothèques, aplanissements
FORMS = ((".bgl.off", "bgl.off"), (".bgl.disabled", "bgl.disabled"), (".bgl.nostatic", "bgl.nostatic"),
         (".bgl.staticq", "bgl.staticq"), (".bgl.static", "bgl.static"),
         (".bgl", "bgl"), (".off", "off"), (".disabled", "disabled"))
ALT_FORMS = {"bgl.nostatic": False, "bgl.staticq": True, "bgl.static": True}   # version de rechange : avec statics ?
LAYOUT_STATIC, LAYOUT_NOSTATIC = "layout.json.static", "layout.json.nostatic"     # échange officiel Orbx / Drzewiecki
OFF_FORMS = ("bgl.off", "bgl.disabled", "off", "disabled")


def parse_form(name: str):
    """'X.bgl.off' -> ('X', 'bgl.off') ; 'X.off' -> ('X', 'off') ; autre -> (None, None)."""
    low = name.lower()
    for suffix, form in FORMS:
        if low.endswith(suffix):
            return name[:-len(suffix)], form
    return None, None


OTHER_EXT_RE = re.compile(r"\.(config|cfg|json|xml|txt|ini|py|js|html?|css|dds|png|ktx2|bin|gltf)$", re.IGNORECASE)


def is_statics_name(name: str) -> bool:
    stem, form = parse_form(name)
    if stem is None or EXCLUDE_RE.search(name):
        return False
    if form in ("off", "disabled") and OTHER_EXT_RE.search(stem):
        return False                              # ex. statics-off.config.off : réglage d'un outil, pas un .bgl
    return form in ALT_FORMS or bool(STATIC_WORD_RE.search(stem))


def _on_name(stem: str, form: str, name: str) -> str:
    """Nom activé (.bgl) d'un fichier désactivé."""
    if form in ("bgl.off", "bgl.disabled"):
        return name[:-(len(form) - 3)]           # retire .off / .disabled, garde la casse de .bgl
    return stem + ".bgl"


def _off_name(on_name: str, form: str) -> str:
    """Nom désactivé d'un .bgl, dans la même convention que `form`."""
    if form == "bgl.nostatic":
        return on_name + ".nostatic"
    if form in ("off", "disabled"):
        return on_name[:-4] + "." + form
    if form == "bgl.disabled":
        return on_name + ".disabled"
    return on_name + ".off"


STATIC_TOKEN_RE = re.compile(r"[ _\-.]?statics?", re.IGNORECASE)
FULL_SIZE_RATIO = 1.25        # fichier « aéroport complet avec statics » ≈ même taille que le fichier de base


def _find_any(listing: dict, directory: Path, stem: str):
    """Fichier `stem` en .bgl ou sous une forme désactivée : (chemin, forme) ou (None, None)."""
    for suffix, form in ((".bgl", "bgl"), (".bgl.off", "bgl.off"), (".bgl.disabled", "bgl.disabled"),
                         (".off", "off"), (".disabled", "disabled")):
        real = listing.get((stem + suffix).lower())
        if real:
            return directory / real, form
    return None, None


def _similar_size(a: Path, b: Path) -> bool:
    try:
        x, y = a.stat().st_size, b.stat().st_size
    except OSError:
        return False
    return min(x, y) > 0 and max(x, y) / min(x, y) <= FULL_SIZE_RATIO


def build_groups(directory: Path, files: list[str]) -> list[StaticsGroup]:
    groups, used = [], set()
    try:
        listing = {n.lower(): n for n in os.listdir(directory)}
    except OSError:
        listing = {}
    entries: dict = {}
    for name in files:
        stem, form = parse_form(name)
        if stem is None:
            continue
        entries.setdefault(stem.lower(), {"stem": stem, "forms": {}})["forms"][form] = name

    # 1. Version de rechange à côté du fichier actif
    #    Méthode officielle Orbx / Drzewiecki (notices LYNI, EPGD ; panneau Orbx Central) :
    #      X.bgl + X.bgl.nostatic = statics ON ; OFF : X.bgl -> X.bgl.static, X.bgl.nostatic -> X.bgl
    #      X.bgl + X.bgl.static   = statics OFF ; ON  : X.bgl -> X.bgl.nostatic, X.bgl.static -> X.bgl
    #      (+ même échange pour layout.json / layout.json.static / layout.json.nostatic, voir set_scene_state)
    #    X.bgl.nostatic seul (Drzewiecki XXXX_PLC sans XXXX_PLC.bgl) : forme désactivée, ON = renommer en X.bgl.
    #    UK2000 (règle de Fabian) : X.bgl (sans statics) + X.bgl.staticq (avec) ;
    #      ON = X.bgl -> X.bgl.bak puis copie de X.bgl.staticq nommée X.bgl ; OFF = copie supprimée, .bak -> X.bgl.
    #    Ancien état laissé par une version de test (X.bgl.bak + copie du .nostatic) : reconnu, ON remet l'original.
    for key, e in entries.items():
        f = e["forms"]
        alts = [fm for fm in f if fm in ALT_FORMS]
        if not alts:
            continue
        used.add(key)
        first = directory / f[alts[0]]
        main = directory / (f.get("bgl") or first.name[:-len(alts[0]) + 3])
        bak = directory / (main.name + ".bak")
        nost = directory / (main.name + ".nostatic")
        stat = directory / (main.name + ".static")
        statq = directory / (main.name + ".staticq")
        broken = lambda at: StaticsGroup("conflict", directory, at, CONFLICT, note="note_swap_broken")
        if "bgl.staticq" in alts:
            if len(alts) > 1 or not main.is_file():
                groups.append(broken(statq))
                continue
            applied = bak.is_file() and same_content(main, statq)
            original = not bak.exists() and not same_content(main, statq)
            if applied or original:
                groups.append(StaticsGroup("swap", directory, main, ON if applied else OFF, bak, statq,
                                           alt_static=True))
            else:
                groups.append(broken(main))
            continue
        has_n, has_s = nost.is_file(), stat.is_file()
        if main.is_file():
            if has_n and not has_s and bak.is_file() and same_content(main, nost):
                groups.append(StaticsGroup("swap", directory, main, OFF, bak, nost))       # ancien état .bak
            elif has_n and not has_s and not bak.exists():
                groups.append(StaticsGroup("rswap", directory, main, ON, stat, nost))
            elif has_s and not has_n and not bak.exists():
                groups.append(StaticsGroup("rswap", directory, main, OFF, stat, nost))
            else:
                groups.append(broken(main))
        elif has_n and not has_s and not bak.exists() and not NEG_RE.search(e["stem"]):
            groups.append(StaticsGroup("rename", directory, nost, OFF, on_path=main, off_path=nost))
        else:
            groups.append(broken(first))

    # 2. Variantes statics_on / statics_off (+ statics.bgl actif)
    variants: dict = {}
    plain: dict = {}
    for key, e in entries.items():
        if key in used:
            continue
        for form, name in e["forms"].items():
            if form not in ("bgl", "bgl.off") or not STATIC_WORD_RE.search(e["stem"]):
                continue
            m = VARIANT_RE.search(e["stem"])
            if m:
                base = e["stem"][:m.start()] + m.group(1) + e["stem"][m.end():]
                v = variants.setdefault(base.lower(), {"base": base})
                v.setdefault(m.group(2).lower(), name)
    pairs = {}
    for key, v in variants.items():
        if "on" in v and "off" in v:
            pairs[key] = v
    variant_names = {n.lower() for v in pairs.values() for n in (v["on"], v["off"])}
    for key, e in entries.items():
        if key in used or not STATIC_WORD_RE.search(e["stem"]):
            continue
        forms = {fm: n for fm, n in e["forms"].items() if n.lower() not in variant_names}
        if forms:
            plain[key] = {"stem": e["stem"], "forms": forms}

    for key, v in pairs.items():
        on_f, off_f = directory / v["on"], directory / v["off"]
        target = key if (key in plain and "bgl" in plain[key]["forms"]) else None
        if target is None and len(pairs) == 1:
            cands = [k for k, p in plain.items() if "bgl" in p["forms"] and not NEG_RE.search(p["stem"])]
            if len(cands) == 1:
                cand = directory / plain[cands[0]]["forms"]["bgl"]
                if same_content(cand, on_f) or same_content(cand, off_f):
                    target = cands[0]
                else:
                    # Autre fichier statics au nom différent, contenu inconnu : peut-être un autre
                    # jeu de statiques (véhicules…). Cas ambigu : on ne touche à rien.
                    used.add(cands[0])
                    used.add(key)
                    groups.append(StaticsGroup("conflict", directory, cand, CONFLICT, on_f, off_f,
                                               "note_ambiguous_active"))
                    continue
        if target:
            used.add(target)
            active = directory / plain[target]["forms"]["bgl"]
            if same_content(active, on_f):
                state, note = ON, ""
            elif same_content(active, off_f):
                state, note = OFF, ""
            else:
                state, note = UNKNOWN, "note_unknown_active"
        else:
            used.add(key)
            active = directory / (v["base"] + ".bgl")
            state, note = UNKNOWN, "note_no_active"
        groups.append(StaticsGroup("variant", directory, active, state, on_f, off_f, note))

    # 3. Paires « avec statics » / « sans statics » : X_static.bgl.disabled + X_nostatic.bgl
    for key, p in list(plain.items()):
        if key in used or not NEG_RE.search(p["stem"]):
            continue
        partner = NEG_RE.sub(lambda mm: mm.group(1), p["stem"]).lower()
        used.add(key)
        q = plain.get(partner)
        if q is None or partner in used:
            groups.append(StaticsGroup("conflict", directory, directory / next(iter(p["forms"].values())),
                                       CONFLICT, note="note_negation"))
            continue
        used.add(partner)
        s_forms, n_forms = q["forms"], p["forms"]
        s_on = "bgl" in s_forms and len(s_forms) == 1
        n_on = "bgl" in n_forms and len(n_forms) == 1
        s_off = len(s_forms) == 1 and next(iter(s_forms)) in OFF_FORMS
        n_off = len(n_forms) == 1 and next(iter(n_forms)) in OFF_FORMS
        if s_on and n_off:
            n_name = n_forms[next(iter(n_forms))]
            form = parse_form(n_name)[1]
            s_path = directory / s_forms["bgl"]
            groups.append(StaticsGroup("pair", directory, s_path, ON,
                                       on_path=s_path, off_path=directory / _off_name(s_path.name, form),
                                       alt_on=directory / _on_name(p["stem"], form, n_name), alt_off=directory / n_name))
        elif n_on and s_off:
            s_name = s_forms[next(iter(s_forms))]
            form = parse_form(s_name)[1]
            n_path = directory / n_forms["bgl"]
            groups.append(StaticsGroup("pair", directory, n_path, OFF,
                                       on_path=directory / _on_name(q["stem"], form, s_name), off_path=directory / s_name,
                                       alt_on=n_path, alt_off=directory / _off_name(n_path.name, form)))
        else:
            base_p, base_f = _find_any(listing, directory, STATIC_TOKEN_RE.sub("", q["stem"], count=1))
            if s_off and n_off and base_f == "bgl":
                # X.bgl actif + X-statics + X-nostatics désactivés : on copie la version choisie sur X.bgl
                s_file = directory / s_forms[next(iter(s_forms))]
                n_file = directory / n_forms[next(iter(n_forms))]
                if same_content(base_p, s_file):
                    state, note = ON, ""
                elif same_content(base_p, n_file):
                    state, note = OFF, ""
                else:
                    state, note = UNKNOWN, "note_unknown_active"
                groups.append(StaticsGroup("variant", directory, base_p, state, s_file, n_file, note))
            elif s_off and n_off and base_p is None:
                # Homa Sim : deux aéroports complets (avec / sans statics) tous deux désactivés -> aucun aéroport
                # chargé (souvent après une ancienne version de SGM). ON active la version avec statics,
                # OFF la version sans ; jamais les deux.
                s_name = s_forms[next(iter(s_forms))]
                n_name = n_forms[next(iter(n_forms))]
                s_form, n_form = parse_form(s_name)[1], parse_form(n_name)[1]
                groups.append(StaticsGroup("pair", directory, directory / s_name, UNKNOWN, note="note_pair_none",
                                           on_path=directory / _on_name(q["stem"], s_form, s_name),
                                           off_path=directory / s_name,
                                           alt_on=directory / _on_name(p["stem"], n_form, n_name),
                                           alt_off=directory / n_name))
            else:
                # les deux actifs, ou fichier actif introuvable : on ne touche à rien
                groups.append(StaticsGroup("conflict", directory, directory / next(iter(s_forms.values())),
                                           CONFLICT, note="note_negation"))

    # 3b. Aéroport complet « avec statics » qui remplace le fichier de base : X-statics ↔ X (tailles proches)
    for key, p in list(plain.items()):
        if key in used:
            continue
        base = STATIC_TOKEN_RE.sub("", p["stem"], count=1)
        if not base or base.lower() == key or STATIC_WORD_RE.search(base):
            continue
        base_p, base_f = _find_any(listing, directory, base)
        if base_p is None or len(p["forms"]) != 1:
            continue
        s_form, s_name = next(iter(p["forms"].items()))
        s_file = directory / s_name
        if not _similar_size(s_file, base_p):
            continue
        used.add(key)
        if s_form in OFF_FORMS and base_f == "bgl":
            groups.append(StaticsGroup("pair", directory, base_p, OFF,
                                       on_path=directory / _on_name(p["stem"], s_form, s_name), off_path=s_file,
                                       alt_on=base_p, alt_off=directory / _off_name(base_p.name, s_form)))
        elif s_form == "bgl" and base_f in OFF_FORMS:
            groups.append(StaticsGroup("pair", directory, s_file, ON,
                                       on_path=s_file, off_path=directory / _off_name(s_name, base_f),
                                       alt_on=directory / _on_name(base, base_f, base_p.name), alt_off=base_p))
        else:
            groups.append(StaticsGroup("conflict", directory, s_file, CONFLICT, note="note_negation"))

    # 4. Fichier simple : X.bgl <-> X.bgl.off / X.off / X.bgl.disabled / X.disabled
    for key, p in plain.items():
        if key in used:
            continue
        forms = p["forms"]
        offs = [fm for fm in forms if fm in OFF_FORMS]
        if "bgl" in forms and not offs:
            on = directory / forms["bgl"]
            groups.append(StaticsGroup("rename", directory, on, ON, on_path=on, off_path=directory / (on.name + ".off")))
        elif "bgl" not in forms and len(offs) == 1:
            off = directory / forms[offs[0]]
            on = directory / _on_name(p["stem"], offs[0], off.name)
            groups.append(StaticsGroup("rename", directory, off, OFF, on_path=on, off_path=off))
        elif "bgl" in forms and len(offs) == 1 and same_content(directory / forms["bgl"], directory / forms[offs[0]]):
            # copie désactivée identique : ON ; désactiver = supprimer le .bgl (son double reste)
            on = directory / forms["bgl"]
            groups.append(StaticsGroup("rename", directory, on, ON, on_path=on, off_path=directory / forms[offs[0]],
                                       twin=True))
        else:
            groups.append(StaticsGroup("conflict", directory, directory / (forms.get("bgl") or next(iter(forms.values()))),
                                       CONFLICT, note="note_conflict"))
    return groups


def read_manifest(root: Path) -> dict:
    try:
        return json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def is_gsx_profile(path: Path, rel: str) -> bool:
    if "gsx" in rel.lower():
        return True
    try:
        if path.stat().st_size > 512 * 1024:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    if "[section." in text and any(k in text for k in GSX_MARKERS):
        return True
    if GSX_NAME_RE.match(path.name) and ("[section." in text or "[general]" in text):
        return True
    return False


def find_gsx_files(root: Path, inis: list[Path]) -> list[Path]:
    out = []
    for ini in inis:
        if is_gsx_profile(ini, os.path.relpath(ini, root)):
            out.append(ini)
            py = ini.with_suffix(".py")
            if py.is_file():
                out.append(py)
    return out


@dataclass
class GsxVariant:
    label: str        # nom court (FULL, LITE…) ; "Standard" est traduit à l'affichage
    folder: Path
    files: list


_SEP_RE = re.compile(r"[\s_\-–—.]+")


def variant_labels(names: list[str]) -> list[str]:
    """« FULL - GSX VDGS », « LITE - GSX VDGS », « GSX VDGS »  ->  FULL, LITE, Standard."""
    toks = [[t for t in _SEP_RE.split(n) if t] for n in names]
    low = [[t.lower() for t in tk] for tk in toks]
    shortest = min(len(t) for t in low)
    pre = 0
    while pre < shortest and len({t[pre] for t in low}) == 1:
        pre += 1
    suf = 0
    while suf < shortest - pre and len({t[len(t) - 1 - suf] for t in low}) == 1:
        suf += 1
    labels = [" ".join(t[pre:len(t) - suf]) or "Standard" for t in toks]
    if len(set(l.lower() for l in labels)) != len(labels):
        return names
    return labels


def build_gsx_variants(root: Path, files: list[Path]) -> list[GsxVariant]:
    groups: dict = {}
    for f in files:
        groups.setdefault(f.parent, []).append(f)
    folders = sorted(groups, key=lambda d: str(d).lower())
    if len(folders) == 1:
        return [GsxVariant("", folders[0], groups[folders[0]])]
    names = [d.name for d in folders]
    if len(set(n.lower() for n in names)) != len(names):
        names = [os.path.relpath(d, root) for d in folders]
    labels = variant_labels(names)
    out = [GsxVariant(l, d, groups[d]) for l, d in zip(labels, folders)]
    out.sort(key=lambda v: (v.label != "Standard", v.label.lower()))
    return out


def vlabel(v: GsxVariant) -> str:
    return tr("standard") if v.label == "Standard" else v.label


ICAO_FIRST = set("ABCDEFGHKLMNOPRSTUVWYZ")       # premières lettres possibles d'un code OACI
ICAO_STOP = {"MSFS", "FULL", "LITE", "PACK", "VDGS", "FREE", "DEMO", "BETA", "PLUS", "CITY", "PORT",
             "BASE", "GATE", "ZONE", "MESH", "ORBX", "FSDT", "FSDG", "HDRP", "MOD", "EDIT", "TEST",
             "PART", "MINI", "LOW", "HIGH", "MAIN", "CORE", "LIVE", "PRO", "NEW", "OLD", "BETA"}
ICAO_TITLE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{4})(?![A-Za-z0-9])")
AIRPORT_WORDS = ("airport", "airfield", "aerodrome", "intl", "international", "airbase", "air base",
                 "aéroport", "aeroport", "aeropuerto", "aeroporto", "flughafen", "luchthaven", "lotnisko")
SKIP_CONTENT_TYPES = {"AIRCRAFT", "LIVERY", "INSTRUMENTS"}


def detect_icao(title: str, folder: str) -> str:
    """Code OACI : d'abord un mot de 4 majuscules dans le titre, sinon dans le nom de dossier
    si le titre évoque un aéroport."""
    for m in ICAO_TITLE_RE.finditer(title):
        c = m.group(1)
        if c[0] in ICAO_FIRST and c not in ICAO_STOP:
            return c
    if any(w in title.lower() for w in AIRPORT_WORDS):
        for tok in re.split(r"[-_ .]+", folder):
            c = tok.upper()
            if len(c) == 4 and c.isalpha() and c[0] in ICAO_FIRST and c not in ICAO_STOP:
                return c
    return ""


def _check_layout(root: Path, groups: list) -> list:
    """Un .bgl actif absent de layout.json n'est pas chargé par MSFS : l'éditeur gère alors ses statics
    autrement (échange de layout.json…). Cas ambigu : on ne touche à rien."""
    try:
        layout = json.loads((root / "layout.json").read_text(encoding="utf-8-sig"))
        listed = {str(e.get("path", "")).replace("\\", "/").lower() for e in layout.get("content", [])}
    except Exception:
        return groups
    if not listed:
        return groups
    out = []
    for g in groups:
        on = g.on_path if g.mode in ("rename", "pair") and g.state == ON else (
            g.alt_on if g.mode == "pair" else (g.active if g.mode in ("swap", "rswap") else None))
        if on is not None and on.is_file() and Path(os.path.relpath(on, root)).as_posix().lower() not in listed:
            out.append(StaticsGroup("conflict", g.directory, on, CONFLICT, note="note_not_in_layout"))
        else:
            out.append(g)
    return out


def _use_origin_off_names(root: Path, groups: list):
    """Un fichier livré désactivé (ex. X.off) et activé par SGM redevient X.off, pas X.bgl.off :
    on garde la convention de l'éditeur, retrouvée dans la photo d'origine."""
    rec = origin_dir(root) / "origin.json"
    if not rec.is_file():
        return
    try:
        names = {Path(r).as_posix().lower(): r for r in json.loads(rec.read_text(encoding="utf-8")).get("files", {})}
    except (OSError, ValueError):
        return
    covered = {norm_key(p) for g in groups for p in g.paths()}
    for low, rel in names.items():
        # X.bgl.nostatic d'origine renommé en X.bgl par SGM : le nom ne contient pas « static »,
        # on le retrouve grâce à la photo d'origine
        if low.endswith(".bgl.nostatic"):
            nost, main = root / rel, root / rel[:-len(".nostatic")]
            if main.is_file() and not nost.exists() and norm_key(main) not in covered:
                groups.append(StaticsGroup("rename", main.parent, main, ON, on_path=main, off_path=nost))
    def origin_off(on_path):
        on_rel = Path(os.path.relpath(on_path, root)).as_posix()
        for alt in (on_rel + ".off", on_rel[:-4] + ".off", on_rel[:-4] + ".disabled", on_rel + ".disabled",
                    on_rel + ".nostatic"):
            if alt.lower() in names and alt.lower() != on_rel.lower():
                return root / names[alt.lower()]
        return None

    for g in groups:
        if g.mode == "rename" and g.state == ON and not g.twin:
            g.off_path = origin_off(g.on_path) or g.off_path
        elif g.mode == "pair":
            if g.on_path is not None and g.on_path.is_file():
                g.off_path = origin_off(g.on_path) or g.off_path
            if g.alt_on is not None and g.alt_on.is_file():
                g.alt_off = origin_off(g.alt_on) or g.alt_off


def scan_package(root: Path, source_label: str) -> Scene | None:
    man = read_manifest(root)
    ctype = str(man.get("content_type") or "").upper()
    if ctype in SKIP_CONTENT_TYPES:          # avions, livrées… : rien à gérer, on évite de les parcourir
        return None
    title = str(man.get("title") or root.name).strip() or root.name
    creator = str(man.get("creator") or "").strip()
    icao = detect_icao(title, root.name)
    by_dir: dict = {}
    inis: list[Path] = []
    for dirpath, _dirs, filenames in os.walk(root, followlinks=True):
        for fn in filenames:
            low = fn.lower()
            if is_statics_name(fn):
                if not EXCLUDE_RE.search(os.path.relpath(dirpath, root)):
                    by_dir.setdefault(dirpath, []).append(fn)
            elif low.endswith(".ini"):
                inis.append(Path(dirpath) / fn)
    groups = []
    for d in sorted(by_dir):
        groups += build_groups(Path(d), sorted(by_dir[d], key=str.lower))
    groups = _check_layout(root, groups)
    _use_origin_off_names(root, groups)
    gsx = find_gsx_files(root, sorted(inis))
    is_airport = bool(icao) and ctype in ("SCENERY", "")
    if not groups and not gsx and not is_airport:
        return None
    return Scene(root, root.name, title, creator, source_label, groups,
                 gsx_files=gsx, gsx_variants=build_gsx_variants(root, gsx) if gsx else [],
                 icao=icao, is_airport=is_airport)


MAX_SEARCH_DEPTH = 8
SKIP_DIRS = {"$recycle.bin", "system volume information", ".git", "__pycache__"}


def find_packages(folder: Path, depth: int = MAX_SEARCH_DEPTH, _seen: set | None = None) -> list[Path]:
    """Scènes (dossiers contenant manifest.json) sur plusieurs niveaux, sans descendre dans une scène."""
    if _seen is None:
        _seen = set()
        if (folder / "manifest.json").is_file():
            return [folder]
    real = norm_key(os.path.realpath(folder))
    if real in _seen:
        return []
    _seen.add(real)
    out = []
    try:
        entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
    except OSError:
        return out
    for e in entries:
        if e.name.lower() in SKIP_DIRS or e.name.startswith("."):
            continue
        try:
            if not e.is_dir():
                continue
        except OSError:
            continue
        p = Path(e.path)
        if (p / "manifest.json").is_file():
            out.append(p)
        elif depth > 1:
            out += find_packages(p, depth - 1, _seen)
    return out


def source_label(src: Source, pkg: Path) -> str:
    try:
        rel = pkg.parent.relative_to(src.path)
    except ValueError:
        return src.label
    parts = [x for x in rel.parts if x not in (".", "")]
    return " › ".join([src.label] + parts) if parts else src.label


def scan_all(sources: list[Source], progress=None) -> list[Scene]:
    pkgs = []
    for s in sources:
        if s.exists:
            pkgs += [(s, p) for p in find_packages(s.path)]
    scenes: dict = {}
    for i, (s, p) in enumerate(pkgs):
        if progress:
            progress(i + 1, len(pkgs), p.name)
        real = norm_key(os.path.realpath(p))
        if real in scenes:
            continue
        try:
            sc = scan_package(Path(os.path.realpath(p)) if REAL_ROOTS else p, source_label(s, p))
        except Exception:
            sc = None
        if sc:
            scenes[real] = sc
    return list(scenes.values())


# ════════════════════════════════════════════════════════════════════════════
#  Modification (renommage / copie + layout.json)
# ════════════════════════════════════════════════════════════════════════════

class ToggleError(Exception):
    pass


def write_atomic(path: Path, text: str):
    tmp = path.with_name(path.name + ".sm-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class PackageMeta:
    """Mise à jour de layout.json et du total_package_size (comme MSFSLayoutGenerator)."""

    def __init__(self, root: Path):
        self.root = root
        self.layout_file = root / "layout.json"
        self.manifest_file = root / "manifest.json"
        self.layout = None
        self.delta = 0
        self.changed = False
        if self.layout_file.is_file():
            try:
                self.layout = json.loads(self.layout_file.read_text(encoding="utf-8-sig"))
            except Exception as e:
                raise ToggleError(tr("err_layout", err=e))

    def rel(self, p: Path) -> str:
        return Path(os.path.relpath(p, self.root)).as_posix()

    def _find(self, rel: str):
        for i, e in enumerate(self.layout.get("content", [])):
            if str(e.get("path", "")).replace("\\", "/").lower() == rel.lower():
                return i
        return None

    def remove(self, p: Path):
        if self.layout is None:
            return
        i = self._find(self.rel(p))
        if i is not None:
            e = self.layout["content"].pop(i)
            self.delta -= int(e.get("size", 0))
            self.changed = True

    def upsert(self, p: Path):
        if self.layout is None:
            return
        st = os.stat(p)
        date = st.st_mtime_ns // 100 + FILETIME_EPOCH
        i = self._find(self.rel(p))
        if i is None:
            self.layout.setdefault("content", []).append({"path": self.rel(p), "size": st.st_size, "date": date})
            self.delta += st.st_size
        else:
            e = self.layout["content"][i]
            self.delta += st.st_size - int(e.get("size", 0))
            e["size"], e["date"] = st.st_size, date
        self.changed = True

    def save(self):
        if self.layout is None or not self.changed:
            return
        write_atomic(self.layout_file, json.dumps(self.layout, indent=2, ensure_ascii=False))
        if self.delta and self.manifest_file.is_file():
            raw = self.manifest_file.read_text(encoding="utf-8-sig")

            def repl(m):
                old = m.group(2)
                new = max(0, int(old) + self.delta)
                return m.group(1) + str(new).zfill(len(old)) + m.group(3)

            new_raw = re.sub(r'("total_package_size"\s*:\s*")(\d+)(")', repl, raw, count=1)
            if new_raw != raw:
                write_atomic(self.manifest_file, new_raw)


def package_root(path: Path) -> Path:
    """Dossier du paquet MSFS qui contient `path` (celui qui a layout.json ou manifest.json), sinon son dossier."""
    path = Path(path)
    for d in list(path.parents)[:8]:
        if (d / "layout.json").is_file() or (d / "manifest.json").is_file():
            return d
    return path.parent


def backup_files(root: Path, files: list[Path]):
    """Copie de sauvegarde, rangée sous le nom du PAQUET et avec l'arborescence relative (sécurité G4 : deux
    fichiers de même nom ne s'écrasent plus, et la sauvegarde d'une scène n'efface pas celles d'une autre)."""
    tag = hashlib.sha1(norm_key(root).encode("utf-8")).hexdigest()[:6]    # deux paquets de même nom (2020 / 2024)
    safe = re.sub(r'[<>:"/\\|?*]', "_", root.name)
    base = data_dir() / "backups" / f"{safe}-{tag}"
    dest = base / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.is_file():
            try:
                rel = Path(f).relative_to(root)
            except ValueError:
                rel = Path(Path(f).name)
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / rel)
    old = sorted([d for d in base.iterdir() if d.is_dir()])
    for d in old[:-MAX_BACKUPS_PER_SCENE]:
        shutil.rmtree(d, ignore_errors=True)


# ── Annuler la dernière action ──
# Chaque action de l'utilisateur (bascule, Tout ON/OFF, profil GSX, restauration) note l'état AVANT de chaque
# fichier qu'elle touche (empreinte, et copie si petit), puis l'état APRÈS. Annuler n'agit que si les fichiers
# sont encore exactement dans l'état APRÈS : sinon rien n'est modifié.

UNDO_MAX = 10                       # actions gardées
UNDO_COPY_MAX = 8 * 1024 * 1024     # au-delà, pas de copie : le contenu est retrouvé par empreinte (renommage)
UNDO_TOTAL_MAX = 500 * 1024 * 1024  # plafond de toutes les copies d'annulation (S8) ; au-delà : empreinte seule


class UndoError(Exception):
    pass


def undo_dir() -> Path:
    return data_dir() / "undo"


class UndoRecorder:
    def __init__(self, label: str):
        self.label = label
        self.before: dict = {}      # clé -> (chemin, empreinte ou None, copie ou None)
        self.tmp = Path(tempfile.mkdtemp(prefix="sgm-undo-", dir=str(data_dir())))
        try:
            self.used = sum(f.stat().st_size for f in undo_dir().rglob("*") if f.is_file())
        except OSError:
            self.used = 0

    def watch(self, *paths):
        for p in paths:
            if p is None:
                continue
            p = Path(p)
            k = norm_key(p)
            if k in self.before:
                continue
            h, copy, size = None, None, 0
            if p.is_file():
                h = file_hash(p)
                size = p.stat().st_size
                meta = p.name.lower() in ("layout.json", "manifest.json")
                if meta or (size <= UNDO_COPY_MAX and self.used + size <= UNDO_TOTAL_MAX):
                    copy = f"{len(self.before)}_{p.name}"
                    shutil.copy2(p, self.tmp / copy)
                    self.used += size
            self.before[k] = (p, h, copy, size)

    def finish(self) -> bool:
        files = []
        for p, h, copy, size in self.before.values():
            forget_hash(p)
            after = file_hash(p) if p.is_file() else None
            if after != h:
                files.append({"path": str(p), "before": h, "after": after, "copy": copy, "size": size})
        # G6 : contenu seulement déplacé (renommage) = retrouvable par empreinte, la copie est inutile.
        # Une seule copie évitée par fichier présent après (doubles identiques : la suivante reste copiée).
        spare = [f["after"] for f in files if f["after"]]
        for f in files:
            if f["copy"] and f["before"] in spare and f["path"].lower().rsplit(".", 1)[-1] != "json":
                spare.remove(f["before"])
                f["copy"] = None
        if not files:
            shutil.rmtree(self.tmp, ignore_errors=True)
            return False
        uid = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        d = undo_dir() / uid
        d.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.tmp, d)
        keep = {f["copy"] for f in files if f["copy"]}
        for f in d.iterdir():                       # copies inutiles (fichiers inchangés)
            if f.name not in keep:
                f.unlink()
        write_atomic(d / "undo.json", json.dumps({"label": self.label, "files": files}, indent=1,
                                                 ensure_ascii=False))
        stack = undo_stack() + [uid]
        for old in stack[:-UNDO_MAX]:
            shutil.rmtree(undo_dir() / old, ignore_errors=True)
        _save_undo_stack(stack[-UNDO_MAX:])
        LOG.info("Annulation possible : %s (%d fichier(s))", self.label, len(files))
        return True

    def discard(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


_UNDO: UndoRecorder | None = None


def undo_watch(*paths):
    """Appelée par le moteur juste avant de modifier des fichiers."""
    if _UNDO is not None:
        _UNDO.watch(*paths)


@contextmanager
def undoable(label: str):
    """Regroupe tout ce qui est modifié dans le bloc en une action annulable."""
    global _UNDO
    if _UNDO is not None:                            # déjà dans une action : on la complète
        yield _UNDO
        return
    rec = UndoRecorder(label)
    _UNDO = rec
    try:
        yield rec
    finally:
        _UNDO = None
        try:
            rec.finish()
        except OSError:
            rec.discard()


def undo_stack() -> list:
    try:
        stack = json.loads((undo_dir() / "stack.json").read_text(encoding="utf-8"))
        return [s for s in stack if (undo_dir() / s / "undo.json").is_file()]
    except (OSError, ValueError):
        return []


def _save_undo_stack(stack: list):
    undo_dir().mkdir(parents=True, exist_ok=True)
    write_atomic(undo_dir() / "stack.json", json.dumps(stack))


def undo_paths() -> list:
    """Fichiers concernés par la dernière action annulable."""
    stack = undo_stack()
    if not stack:
        return []
    try:
        return [Path(f["path"]) for f in
                json.loads((undo_dir() / stack[-1] / "undo.json").read_text(encoding="utf-8"))["files"]]
    except (OSError, ValueError, KeyError):
        return []


def undo_label() -> str:
    """Nom de la dernière action annulable, ou ""."""
    stack = undo_stack()
    if not stack:
        return ""
    try:
        return json.loads((undo_dir() / stack[-1] / "undo.json").read_text(encoding="utf-8"))["label"]
    except (OSError, ValueError, KeyError):
        return ""


class _Tx:
    """Opérations de fichiers réversibles. Tout ou rien : rollback() remet chaque fichier à sa place,
    commit() efface seulement les anciennes versions mises de côté (« .sgm-old »)."""

    def __init__(self):
        self.done, self.created, self.aside = [], [], []

    def move(self, a: Path, b: Path):
        os.replace(a, b)
        self.done.append((b, a))

    def set_aside(self, p: Path):                  # fichier remplacé ou supprimé : gardé jusqu'au commit
        if p.exists():
            q = p.with_name(p.name + ".sgm-old")
            self.move(p, q)
            self.aside.append(q)

    def prepare(self, src: Path, dst: Path) -> Path:
        tmp = dst.with_name(dst.name + ".sm-tmp")
        shutil.copy2(src, tmp)
        self.created.append(tmp)
        return tmp

    def place(self, tmp: Path, dst: Path):
        self.set_aside(dst)
        self.move(tmp, dst)

    def rollback(self) -> bool:
        ok = True
        for cur, orig in reversed(self.done):
            try:
                if cur.exists() and not orig.exists():
                    os.rename(cur, orig)
            except OSError:
                ok = False
        for t in self.created:
            try:
                if t.exists():
                    t.unlink()
            except OSError:
                ok = False
        return ok

    def commit(self):
        for q in self.aside:
            try:
                q.unlink()
            except OSError:
                pass


def undo_last() -> str:
    """Remet les fichiers de la dernière action dans leur état d'avant. Tout ou rien (UndoError)."""
    stack = undo_stack()
    if not stack:
        raise UndoError(tr("undo_nothing"))
    d = undo_dir() / stack[-1]
    rec = json.loads((d / "undo.json").read_text(encoding="utf-8"))
    files = rec["files"]
    paths = {norm_key(f["path"]): Path(f["path"]) for f in files}
    cur = {}
    for k, p in paths.items():
        forget_hash(p)
        cur[k] = file_hash(p) if p.is_file() else None
    changed = [p.name for f in files for k, p in [(norm_key(f["path"]), Path(f["path"]))] if cur[k] != f["after"]]
    if changed:
        raise UndoError(tr("undo_changed", files="\n".join(f"• {n}" for n in sorted(set(changed))[:15])))

    # 1. Plan : chaque fichier d'avant vient de sa copie, sinon d'un fichier actuel de même empreinte (renommé)
    copies, moves, from_target, used = [], [], [], set()
    for f in files:
        if f["before"] is None:
            continue
        dst = Path(f["path"])
        if f["copy"] and (d / f["copy"]).is_file():
            copies.append((d / f["copy"], dst))
            continue
        src = next((k for k, h in cur.items() if h == f["before"] and k not in used), None)
        if src is not None:
            used.add(src)
            moves.append((paths[src], dst))
            continue
        # deux fichiers identiques avant (doubles) : le second est recopié depuis le premier remis en place
        twin = next((dd for s, dd in moves if cur.get(norm_key(s)) == f["before"]), None)
        if twin is None:                             # double identique resté intact à côté (.staticq, .off…)
            for sib in (dst.parent.iterdir() if dst.parent.is_dir() else []):
                try:
                    if sib.is_file() and sib.stat().st_size == f.get("size", -1) and file_hash(sib) == f["before"]:
                        copies.append((sib, dst))
                        twin = sib
                        break
                except OSError:
                    continue
            if twin is not None:
                continue
        if twin is None:
            raise UndoError(tr("undo_changed", files=f"• {dst.name}"))
        from_target.append((twin, dst))
    deletes = [paths[k] for k, f in ((norm_key(f["path"]), f) for f in files)
               if f["before"] is None and k not in used and paths[k].exists()]

    # 2. Exécution (sauvegarde de l'état actuel d'abord)
    by_root = {}
    for p in paths.values():
        if p.is_file():
            by_root.setdefault(package_root(p), []).append(p)
    for parent, ps in by_root.items():
        backup_files(parent, ps)
    tx = _Tx()
    try:
        prepared = [(tx.prepare(s, dd), dd) for s, dd in copies]     # avant tout renommage (sources intactes)
        staged = []
        for s, dd in moves:                          # d'abord vers des noms temporaires (échanges de noms)
            tmp = s.with_name(s.name + ".sgm-undo")
            tx.move(s, tmp)
            staged.append((tmp, dd))
        for q in deletes:
            tx.set_aside(q)
        for tmp, dd in staged:
            tx.place(tmp, dd)
        for tmp, dd in prepared:
            tx.place(tmp, dd)
        for s, dd in from_target:
            tx.place(tx.prepare(s, dd), dd)
    except OSError as e:
        back = tx.rollback()
        for pth in paths.values():
            forget_hash(pth)
        LOG.warning("Annulation interrompue (retour arrière %s) : %s", "complet" if back else "partiel", e)
        raise UndoError(tr("undo_failed", err=e) if back else tr("err_access", file=getattr(e, "filename", None) or e))
    tx.commit()
    for p in paths.values():
        forget_hash(p)
    shutil.rmtree(d, ignore_errors=True)
    _save_undo_stack(stack[:-1])
    LOG.info("Action annulée : %s", rec["label"])
    return rec["label"]


# ── État d'origine (photo prise avant la toute première modification, jamais effacée) ──

class RestoreError(Exception):
    pass


def _safe_name(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]', "_", text)[:60]


def origin_dir(root: Path) -> Path:
    key = hashlib.sha1(norm_key(root).encode("utf-8")).hexdigest()[:10]
    return data_dir() / "origin" / f"{_safe_name(root.name)}-{key}"


def has_origin(root: Path) -> bool:
    return (origin_dir(root) / "origin.json").is_file()


def _pkg_version(root: Path) -> str:
    return str(read_manifest(root).get("package_version") or "")


def statics_paths(scene: Scene) -> list[Path]:
    """Tous les fichiers statics d'une scène (actifs, variantes, renommés)."""
    out = []
    for g in scene.groups:
        for p in g.paths():
            if p not in out:
                out.append(p)
    return out


def snapshot_scene(scene: Scene):
    """Photo de l'état d'origine, une seule fois par scène : liste des fichiers statics avec leur empreinte,
    copie de layout.json, manifest.json et des fichiers dont le contenu pourrait être remplacé."""
    d = origin_dir(scene.root)
    if (d / "origin.json").is_file():
        return
    files_dir = d / "files"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)          # photo incomplète d'une tentative précédente
    files_dir.mkdir(parents=True, exist_ok=True)
    rel = lambda p: Path(os.path.relpath(p, scene.root)).as_posix()
    record = {"root": str(scene.root), "created": datetime.now().isoformat(timespec="seconds"),
              "version": _pkg_version(scene.root), "files": {}, "copied": []}
    for p in statics_paths(scene):
        record["files"][rel(p)] = file_hash(p)
    to_copy = [g.active for g in scene.groups if g.mode == "variant" and g.active.is_file()]
    to_copy += [scene.root / "layout.json", scene.root / "manifest.json"]
    for n in (LAYOUT_STATIC, LAYOUT_NOSTATIC):
        if (scene.root / n).is_file():
            to_copy.append(scene.root / n)
            record["files"][n] = file_hash(scene.root / n)
    if not record["files"]:                         # rien trouvé (scène déplacée…) : pas de photo vide
        shutil.rmtree(d, ignore_errors=True)
        return
    for p in to_copy:
        if p.is_file():
            target = files_dir / rel(p)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            record["copied"].append(rel(p))
    write_atomic(d / "origin.json", json.dumps(record, indent=2, ensure_ascii=False))


def _restore_scene_statics(root: Path):
    """Remet les fichiers statics, layout.json et manifest.json comme avant SGM.
    Tout ou rien : si un fichier ne correspond pas à l'origine, rien n'est modifié (RestoreError)."""
    d = origin_dir(root)
    try:
        record = json.loads((d / "origin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RestoreError(tr("restore_none"))
    if not root.is_dir():
        raise RestoreError(tr("folder_missing_msg", path=root))
    if record.get("version", "") != _pkg_version(root):
        shutil.rmtree(d, ignore_errors=True)          # la scène a été mise à jour : la photo n'est plus valable
        raise RestoreError(tr("restore_updated"))
    files_dir = d / "files"
    current = scan_package(root, "")
    cur_paths = statics_paths(current) if current else []
    wanted = record.get("files", {})
    copied = set(record.get("copied", []))
    known = set(wanted.values())
    if current:
        for g in current.groups:
            for v in (g.on_file, g.off_file):
                if v is not None and v.is_file():
                    known.add(file_hash(v))

    # 1. Plan, sans rien toucher. Chaque fichier d'origine est retrouvé par son empreinte, quel que soit
    #    son nom actuel (renommé .off, .disabled, échangé avec sa version « sans statics »…).
    cur = {norm_key(p): p for p in cur_paths}
    for n in (LAYOUT_STATIC, LAYOUT_NOSTATIC):         # fichiers layout échangés (méthode officielle)
        if (root / n).is_file():
            cur.setdefault(norm_key(root / n), root / n)
    if "layout.json" in copied and (files_dir / "layout.json").is_file():
        known.add(file_hash(files_dir / "layout.json"))
    for r in wanted:
        if (root / r).is_file():
            cur.setdefault(norm_key(root / r), root / r)
    hashes = {k: file_hash(p) for k, p in cur.items()}
    rel_of = lambda p: Path(os.path.relpath(p, root)).as_posix()
    ok = {norm_key(root / r) for r, h in wanted.items() if hashes.get(norm_key(root / r)) == h}
    moves, copies, deletes, left, sources = [], [], [], [], set()
    for r, h in wanted.items():
        dst = root / r
        if norm_key(dst) in ok:
            continue
        if r in copied and (files_dir / r).is_file():
            copies.append((files_dir / r, dst))
            continue
        src = next((k for k, hh in hashes.items() if hh == h and k not in ok and k not in sources), None)
        if src is not None:
            moves.append((cur[src], dst))
            sources.add(src)
            continue
        src = next((k for k, hh in hashes.items() if hh == h and k in ok), None)
        if src is not None:
            copies.append((cur[src], dst))
            continue
        twin = next((d2 for s2, d2 in moves if hashes.get(norm_key(s2)) == h), None)
        if twin is not None:                     # deux fichiers identiques à l'origine : copie du premier remis
            copies.append((twin, dst))
            continue
        left.append(r)
    targets = {norm_key(dd) for _s, dd in moves + copies}
    for _s, dd in moves + copies:
        k = norm_key(dd)
        if str(_s).startswith(str(files_dir)):
            continue                              # remis depuis la photo d'origine (layout.json échangé…)
        if dd.exists() and k in cur and k not in sources:
            if hashes[k] in known:
                deletes.append(dd)
            else:
                left.append(rel_of(dd))
    for k, q in cur.items():
        if rel_of(q) in wanted or k in sources or k in targets:
            continue
        if hashes[k] in known:
            deletes.append(q)
        else:
            left.append(rel_of(q))
    if left:
        raise RestoreError(tr("restore_left", files="\n".join(f"• {r}" for r in sorted(set(left)))))

    # 2. Exécution, après sauvegarde de l'état actuel
    undo_watch(root / "layout.json", root / "manifest.json", *cur.values(), *(root / r for r in wanted))
    backup_files(root, [root / "layout.json", root / "manifest.json"] + list(cur.values()))
    tx = _Tx()
    try:
        prepared = [(tx.prepare(s, dd), dd) for s, dd in copies if s.is_relative_to(files_dir)]
        later = [(s, dd) for s, dd in copies if not s.is_relative_to(files_dir)]
        staged = []
        for s, dd in moves:                      # d'abord vers des noms temporaires (échanges de noms)
            tmp = s.with_name(s.name + ".sgm-restore")
            tx.move(s, tmp)
            staged.append((tmp, dd))
        for q in deletes:
            tx.set_aside(q)
        for tmp, dd in staged:
            tx.place(tmp, dd)
        for tmp, dd in prepared:
            tx.place(tmp, dd)
        for s, dd in later:                      # copies d'un fichier déjà remis en place (doubles)
            tx.place(tx.prepare(s, dd), dd)
        for r in ("layout.json", "manifest.json"):
            if r in copied and (files_dir / r).is_file():
                tx.place(tx.prepare(files_dir / r, root / r), root / r)
    except OSError as e:
        tx.rollback()
        for p in list(cur.values()) + [root / r for r in wanted]:
            forget_hash(p)
        raise RestoreError(tr("err_access", file=getattr(e, "filename", None) or e))
    tx.commit()
    for p in list(cur.values()) + [root / r for r in wanted]:
        forget_hash(p)
    # La photo d'origine est GARDÉE : elle décrit toujours l'état d'origine (et « Annuler » une restauration
    # doit retrouver la même photo). Une mise à jour de la scène l'invalide (version de l'éditeur).


def origin_roots() -> list[Path]:
    base = data_dir() / "origin"
    out = []
    if base.is_dir():
        for d in sorted(base.iterdir()):
            try:
                out.append(Path(json.loads((d / "origin.json").read_text(encoding="utf-8"))["root"]))
            except (OSError, ValueError, KeyError):
                continue
    return out


# ── Rapport d'analyse des fichiers statics (lecture seule) ──
# But : constituer une base réelle de noms de fichiers pour améliorer les règles de détection.
# Aucun chemin complet ni nom d'utilisateur : uniquement des chemins relatifs au paquet de la scène.

REPORT_SCHEMA = 1
REPORT_EXTS = (".bgl", ".off", ".bak", ".disabled", ".old", ".orig", ".inactive")
REPORT_NOISE = re.compile(r"\.(dds|ktx2|png|jpg|jpeg|tif|tga|bmp|bin|gltf|glb|xml|spb|pck|svg|wav|ogg|js|css|html)(\.json)?$")
REPORT_WORDS = re.compile(r"static|parked|parking_?ai|(?<![a-z])(off|disabled?|deactivated?|inactive|without|nostatics?|"
                          r"no[_ \-]?statics?|empty|bak)(?![a-z])", re.IGNORECASE)


def _report_file(root: Path, p: Path, layout_paths: set) -> dict:
    rel = Path(os.path.relpath(p, root)).as_posix()
    try:
        size = p.stat().st_size
        h = file_hash(p)[:12]
    except OSError:
        size, h = -1, ""
    return {"path": rel, "size": size, "sha1": h, "in_layout": rel.lower() in layout_paths}


def report_scene(root: Path, source: str) -> dict | None:
    """Description d'une scène pour le rapport, ou None si aucun fichier intéressant."""
    man = read_manifest(root)
    ctype = str(man.get("content_type") or "").upper()
    if ctype in SKIP_CONTENT_TYPES:
        return None
    try:
        layout = json.loads((root / "layout.json").read_text(encoding="utf-8-sig"))
        layout_paths = {str(e.get("path", "")).replace("\\", "/").lower() for e in layout.get("content", [])}
    except Exception:
        layout_paths = set()
    files, bgl_count, bgl_dirs = [], 0, set()
    for dirpath, _dirs, filenames in os.walk(root, followlinks=True):
        for fn in filenames:
            low = fn.lower()
            if low.endswith(".bgl"):
                bgl_count += 1
                bgl_dirs.add(Path(os.path.relpath(dirpath, root)).as_posix())
            if REPORT_NOISE.search(low):
                continue                           # textures, modèles 3D : jamais des interrupteurs de statics
            if not ((any(low.endswith(e) for e in REPORT_EXTS) and REPORT_WORDS.search(fn.rsplit(".", 1)[0] if "." in fn else fn))
                    or "static" in low):
                continue
            files.append(_report_file(root, Path(dirpath) / fn, layout_paths))
            stem, _form = parse_form(fn)
            cands = []
            for suffix in (".nostatic", ".staticq", ".static"):
                if low.endswith(".bgl" + suffix):
                    cands.append(fn[:-len(suffix)])             # fichier actif + sa sauvegarde
                    cands.append(fn[:-len(suffix)] + ".bak")
            if stem:
                base = STATIC_TOKEN_RE.sub("", stem, count=1)   # ex. lowi-scene-airport-statics -> lowi-scene-airport
                if base and base.lower() != stem.lower():
                    cands += [base + ".bgl", base + ".bgl.disabled", base + ".off"]
            for c in cands:
                if (Path(dirpath) / c).is_file():
                    files.append(_report_file(root, Path(dirpath) / c, layout_paths))
    if not files:
        return None
    sc = scan_package(root, source)
    groups = []
    for g in (sc.groups if sc else []):
        groups.append({"mode": g.mode, "state": g.state, "note": g.note,
                       "paths": [Path(os.path.relpath(x, root)).as_posix() for x in g.paths()],
                       "active": Path(os.path.relpath(g.active, root)).as_posix(),
                       "on": Path(os.path.relpath(g.on_file, root)).as_posix() if g.on_file else "",
                       "off": Path(os.path.relpath(g.off_file, root)).as_posix() if g.off_file else ""})
    detected = {gp.lower() for g in groups if g["mode"] != "conflict" for gp in g["paths"]}
    seen_paths = set()
    uniq = []
    for f in files:
        if f["path"] in seen_paths:
            continue
        seen_paths.add(f["path"])
        f["used_by_sgm"] = f["path"].lower() in detected
        uniq.append(f)
    files = uniq
    return {"folder": root.name, "title": str(man.get("title") or ""), "creator": str(man.get("creator") or ""),
            "version": str(man.get("package_version") or ""), "content_type": ctype,
            "icao": detect_icao(str(man.get("title") or root.name), root.name), "source": source,
            "bgl_count": bgl_count, "bgl_dirs": sorted(bgl_dirs)[:20], "files": sorted(files, key=lambda f: f["path"]),
            "sgm_groups": groups,
            "sgm_state": sc.state if sc else NONE}


def build_statics_report(sources: list, sim: str, progress=None) -> dict:
    pkgs = []
    for s in sources:
        if s.exists:
            pkgs += [(s, p) for p in find_packages(s.path)]
    scenes, seen = [], set()
    for i, (s, p) in enumerate(pkgs):
        if progress:
            progress(i + 1, len(pkgs), p.name)
        real = norm_key(os.path.realpath(p))
        if real in seen:
            continue
        seen.add(real)
        try:
            r = report_scene(p, source_label(s, p))
        except Exception as e:                     # une scène illisible ne bloque pas le rapport
            r = {"folder": p.name, "error": type(e).__name__}
        if r:
            scenes.append(r)
    states: dict = {}
    for r in scenes:
        st = r.get("sgm_state", "error")
        states[st] = states.get(st, 0) + 1
    unused = sum(1 for r in scenes for f in r.get("files", []) if not f.get("used_by_sgm"))
    return {"schema": REPORT_SCHEMA, "app": f"SGM v{APP_VERSION}", "sim": sim,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"), "packages_scanned": len(seen),
            "summary": {"scenes_with_candidates": len(scenes), "by_sgm_state": states,
                        "candidate_files_not_used_by_sgm": unused},
            "scenes": scenes}


def write_statics_report(report: dict) -> Path:
    d = data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"sgm-statics-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    write_atomic(out, json.dumps(report, indent=1, ensure_ascii=False))
    LOG.info("Rapport d'analyse créé : %s (%s scènes avec fichiers statics)", out.name,
             report.get("summary", {}).get("scenes_with_candidates", "?"))
    return out


# ── Journal GSX : état d'origine de chaque fichier que SGM écrit ou retire ──

def _gsx_journal_dir(dest_dir: Path) -> Path:
    key = hashlib.sha1(norm_key(dest_dir).encode("utf-8")).hexdigest()[:10]
    return data_dir() / "origin" / "_GSX" / key


def _gsx_load(dest_dir: Path) -> dict:
    try:
        return json.loads((_gsx_journal_dir(dest_dir) / "journal.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"dest": str(dest_dir), "files": {}}


def gsx_record(dest_dir: Path, names: list[str]):
    """Avant d'écrire ou de retirer ces fichiers dans GSX : note leur état d'origine (une seule fois)."""
    j = _gsx_load(dest_dir)
    jd = _gsx_journal_dir(dest_dir)
    changed = False
    for n in names:
        k = n.lower()
        if k in j["files"]:
            continue
        p = dest_dir / n
        if p.is_file():
            (jd / "files").mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, jd / "files" / n)
            j["files"][k] = {"name": n, "existed": True}
        else:
            j["files"][k] = {"name": n, "existed": False}
        changed = True
    if changed:
        jd.mkdir(parents=True, exist_ok=True)
        write_atomic(jd / "journal.json", json.dumps(j, indent=2, ensure_ascii=False))


def gsx_mark_written(dest_dir: Path, names: list[str]):
    """Après une écriture ou un retrait par SGM : note l'empreinte laissée par SGM (None = fichier retiré).
    La restauration ne touchera un fichier que s'il est encore exactement dans cet état (sécurité G1)."""
    j = _gsx_load(dest_dir)
    changed = False
    for n in names:
        e = j["files"].get(n.lower())
        if e is None:
            continue
        p = dest_dir / e["name"]
        forget_hash(p)
        e["written"] = file_hash(p) if p.is_file() else None
        changed = True
    if changed:
        jd = _gsx_journal_dir(dest_dir)
        jd.mkdir(parents=True, exist_ok=True)
        write_atomic(jd / "journal.json", json.dumps(j, indent=2, ensure_ascii=False))


def gsx_has_origin(dest_dir: Path, names) -> bool:
    files = _gsx_load(dest_dir)["files"]
    return any(n.lower() in files for n in names)


def _gsx_restore(dest_dir: Path, names=None, skipped: list | None = None) -> int:
    """Remet les fichiers GSX notés dans le journal (tous, ou seulement `names`). Renvoie le nombre traité.
    Un profil modifié depuis le passage de SGM (retouché dans l'éditeur GSX, remplacé à la main…) n'est jamais
    supprimé ni écrasé : il reste tel quel, son nom est ajouté à `skipped` et il reste dans le journal (G1)."""
    j = _gsx_load(dest_dir)
    jd = _gsx_journal_dir(dest_dir)
    keys = [k for k in j["files"] if names is None or k in {n.lower() for n in names}]
    ok_keys = []
    for k in keys:
        e = j["files"][k]
        p = dest_dir / e["name"]
        forget_hash(p)
        cur = file_hash(p) if p.is_file() else None
        orig = jd / "files" / e["name"]
        orig_h = (file_hash(orig) if orig.is_file() else "?") if e["existed"] else None
        if cur == orig_h:                                  # déjà dans l'état d'origine
            ok_keys.append(k)
        elif "written" in e and cur == e["written"]:      # encore exactement ce que SGM a laissé
            ok_keys.append(k)
        elif skipped is not None:
            skipped.append(e["name"])
    keys = ok_keys
    if not keys:
        return 0
    current = [dest_dir / j["files"][k]["name"] for k in keys if (dest_dir / j["files"][k]["name"]).is_file()]
    undo_watch(*(dest_dir / j["files"][k]["name"] for k in keys))
    if current:
        bdir = data_dir() / "backups" / "_GSX" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        bdir.mkdir(parents=True, exist_ok=True)
        for p in current:
            shutil.copy2(p, bdir / p.name)
    done = 0
    for k in keys:
        e = j["files"][k]                     # le journal d'origine est GARDÉ (Annuler une restauration le retrouve)
        p = dest_dir / e["name"]
        forget_hash(p)
        cur = file_hash(p) if p.is_file() else None
        if e["existed"]:
            src = jd / "files" / e["name"]
            if src.is_file() and cur != file_hash(src):
                shutil.copy2(src, p)
                done += 1
        elif p.is_file():
            p.unlink()
            done += 1
        forget_hash(p)
    return done


def gsx_journal_dests() -> list[Path]:
    base = data_dir() / "origin" / "_GSX"
    out = []
    if base.is_dir():
        for d in base.iterdir():
            try:
                out.append(Path(json.loads((d / "journal.json").read_text(encoding="utf-8"))["dest"]))
            except (OSError, ValueError, KeyError):
                continue
    return out


def _move(src: Path, dst: Path):
    if dst.exists():
        raise ToggleError(tr("err_exists", name=dst.name))
    undo_watch(src, dst)
    os.rename(src, dst)
    LOG.info("  renommé %s -> %s", src.name, dst.name)
    forget_hash(src)
    forget_hash(dst)


def _swap_layout_files(root: Path, groups: list, target: str):
    """Méthode officielle Orbx / Drzewiecki : layout.json est échangé avec layout.json.nostatic (OFF)
    ou layout.json.static (ON), pour rester cohérent avec le panneau Orbx Central."""
    if not any(g.mode == "rswap" for g in groups):
        return
    lj, ljs, ljn = root / "layout.json", root / LAYOUT_STATIC, root / LAYOUT_NOSTATIC

    def valid(f: Path) -> bool:                   # jamais d'échange vers un layout illisible
        try:
            return isinstance(json.loads(f.read_text(encoding="utf-8-sig")).get("content"), list)
        except Exception:
            return False

    if not lj.is_file():
        return
    if target == OFF and ljn.is_file() and not ljs.exists() and valid(ljn):
        os.rename(lj, ljs)
        os.rename(ljn, lj)
    elif target == ON and ljs.is_file() and not ljn.exists() and valid(ljs):
        os.rename(lj, ljn)
        os.rename(ljs, lj)


def _set_scene_state(scene: Scene, target: str):
    groups = [g for g in scene.groups if g.toggleable and g.state != target]
    if not groups:
        return
    snapshot_scene(scene)
    meta = PackageMeta(scene.root)
    undo_watch(meta.layout_file, meta.manifest_file, *(scene.root / n for n in (LAYOUT_STATIC, LAYOUT_NOSTATIC)))
    for g in groups:
        undo_watch(g.active, g.on_file, g.off_file, g.on_path, g.off_path, g.alt_on, g.alt_off)
        if g.mode == "swap" and g.active is not None:
            undo_watch(g.active.with_name(g.active.name + ".bak"))
    to_backup = [meta.layout_file, meta.manifest_file]
    to_backup += [g.active for g in groups if g.mode == "variant" and g.state == UNKNOWN and g.active.exists()]
    to_backup += [g.on_path for g in groups if g.mode == "rename" and g.twin and g.on_path.is_file()]
    to_backup += [scene.root / n for n in (LAYOUT_STATIC, LAYOUT_NOSTATIC) if (scene.root / n).is_file()]
    backup_files(scene.root, to_backup)
    _swap_layout_files(scene.root, groups, target)
    if any(g.mode == "rswap" for g in groups):
        LOG.info("  layout.json échangé (méthode officielle .static / .nostatic)")
    meta = PackageMeta(scene.root)              # relu : layout.json a pu être échangé
    try:
        for g in groups:
            if g.mode == "rename":
                if target == OFF:
                    if g.twin and g.off_path.is_file() and same_content(g.on_path, g.off_path):
                        g.on_path.unlink()               # son double désactivé identique reste en place
                        forget_hash(g.on_path)
                    else:
                        _move(g.on_path, g.off_path)
                    meta.remove(g.on_path)
                elif g.off_form == "bgl.disabled":
                    # iniBuilds : le .disabled d'origine reste en place, on active une copie
                    if g.on_path.exists():
                        raise ToggleError(tr("err_exists", name=g.on_path.name))
                    shutil.copy2(g.off_path, g.on_path)
                    forget_hash(g.on_path)
                    meta.upsert(g.on_path)
                else:
                    _move(g.off_path, g.on_path)
                    meta.upsert(g.on_path)
            elif g.mode == "rswap":
                main, stat, nost = g.active, g.on_file, g.off_file
                if target == OFF:                         # X.bgl -> X.bgl.static, X.bgl.nostatic -> X.bgl
                    _move(main, stat)
                    _move(nost, main)
                else:                                     # X.bgl -> X.bgl.nostatic, X.bgl.static -> X.bgl
                    _move(main, nost)
                    _move(stat, main)
                meta.upsert(main)
            elif g.mode == "swap":
                main, bak, alt = g.active, g.on_file, g.off_file
                apply_alt = (target == ON) if g.alt_static else (target == OFF)
                if apply_alt:                             # X.bgl -> X.bgl.bak, copie de la version de rechange en X.bgl
                    _move(main, bak)
                    shutil.copy2(alt, main)
                    forget_hash(main)
                else:                                     # copie supprimée (vérifiée), X.bgl.bak -> X.bgl
                    if not same_content(main, alt):
                        raise ToggleError(tr("err_exists", name=main.name))
                    main.unlink()
                    forget_hash(main)
                    _move(bak, main)
                meta.upsert(main)
            elif g.mode == "pair":
                # toujours désactiver d'abord, puis activer : jamais les deux versions chargées
                if target == OFF:                         # avec statics désactivé, sans statics activé
                    if g.on_path.is_file():
                        _move(g.on_path, g.off_path)
                        meta.remove(g.on_path)
                    _move(g.alt_off, g.alt_on)
                    meta.upsert(g.alt_on)
                else:
                    if g.alt_on.is_file():
                        _move(g.alt_on, g.alt_off)
                        meta.remove(g.alt_on)
                    _move(g.off_path, g.on_path)
                    meta.upsert(g.on_path)
            else:
                src = g.on_file if target == ON else g.off_file
                tmp = g.active.with_name(g.active.name + ".sm-tmp")
                shutil.copy2(src, tmp)
                os.replace(tmp, g.active)
                forget_hash(g.active)
                meta.upsert(g.active)
    except PermissionError as e:
        raise ToggleError(tr("err_access", file=e.filename))
    finally:
        meta.save()


# ── GSX ────────────────────────────────────────────────────────────────────

def gsx_status(files: list, dest_dir: Path) -> str:
    if not files:
        return ""
    status = GSX_SAME
    for f in files:
        d = dest_dir / f.name
        if not d.is_file():
            return GSX_MISSING
        if not same_content(f, d):
            status = GSX_DIFF
    return status


def variant_id(scene: Scene, v: GsxVariant) -> str:
    return os.path.relpath(v.folder, scene.root).replace("\\", "/").lower()


VAR_CHOSEN, VAR_NONE, VAR_CHECK = "chosen", "none", "check"


def gsx_variant_state(scene: Scene, dest: Path, saved: str | None):
    """(état, index actif, raison, nom) ; raison = clé de traduction, "auto" ou ""."""
    stats = [gsx_status(v.files, dest) for v in scene.gsx_variants]
    same = [i for i, st in enumerate(stats) if st == GSX_SAME]
    ids = [variant_id(scene, v) for v in scene.gsx_variants]
    if saved in ids:
        i = ids.index(saved)
        if stats[i] == GSX_SAME:
            return VAR_CHOSEN, i, "", ""
        return VAR_CHECK, None, "reason_drift", vlabel(scene.gsx_variants[i])
    if len(same) == 1:
        return VAR_CHOSEN, same[0], "auto", ""
    if len(same) > 1:
        return VAR_CHECK, None, "reason_multi", ""
    if any((dest / f.name).is_file() for v in scene.gsx_variants for f in v.files):
        return VAR_CHECK, None, "reason_unknown", ""
    return VAR_NONE, None, "", ""


def gsx_dest_index(dest: Path) -> list[str]:
    """Noms des profils .ini présents dans le dossier GSX."""
    try:
        return sorted(e.name for e in os.scandir(dest) if e.is_file() and e.name.lower().endswith(".ini"))
    except OSError:
        return []


def gsx_manual_profiles(scene: Scene, dest_names: list[str]) -> list[str]:
    """Profils du dossier GSX qui correspondent à l'OACI de la scène sans venir de la scène."""
    if not scene.icao:
        return []
    own = {f.name.lower() for f in scene.gsx_files}
    ic = scene.icao.lower()
    return [n for n in dest_names
            if (n.lower().startswith(ic + "-") or n.lower() == ic + ".ini" or n.lower().startswith(ic + "_"))
            and n.lower() not in own]


def gsx_search_query(scene: Scene) -> str:
    return f"{scene.icao} GSX" if scene.icao else f"{scene.title} GSX"


def gsx_other_installed(scene: Scene, variant: GsxVariant, dest_dir: Path) -> list[Path]:
    """Fichiers d'autres variantes présents dans GSX à retirer pour activer `variant`."""
    keep = {f.name.lower() for f in variant.files}
    out = []
    for v in scene.gsx_variants:
        if v is variant:
            continue
        for f in v.files:
            d = dest_dir / f.name
            if f.name.lower() not in keep and d.is_file() and same_content(f, d):
                out.append(d)
    return out


def _copy_gsx(scene: Scene, variant: GsxVariant, dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    replaced = [dest_dir / f.name for f in variant.files
                if (dest_dir / f.name).is_file() and not same_content(f, dest_dir / f.name)]
    removed = gsx_other_installed(scene, variant, dest_dir)
    undo_watch(*(dest_dir / f.name for f in variant.files), *removed)
    gsx_record(dest_dir, [f.name for f in variant.files] + [r.name for r in removed])
    if replaced or removed:
        bdir = data_dir() / "backups" / "_GSX" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        bdir.mkdir(parents=True, exist_ok=True)
        for r in replaced + removed:
            shutil.copy2(r, bdir / r.name)
    for r in removed:
        r.unlink()
        forget_hash(r)
    copied = []
    for f in variant.files:
        shutil.copy2(f, dest_dir / f.name)
        forget_hash(dest_dir / f.name)
        copied.append(f.name)
    gsx_mark_written(dest_dir, copied + [r.name for r in removed])
    return copied


# ── Archives de profils GSX ─────────────────────────────────────────────────

ARCHIVE_EXT = (".zip", ".7z", ".rar")
MAX_MEMBER_SIZE = 4 * 1024 * 1024        # un profil GSX fait quelques Ko : au-delà, on ignore
MAX_ARCHIVE_MEMBERS = 20000              # sécurité G5 : plafonds vérifiés AVANT toute extraction
MAX_PROFILE_FILES = 2000
MAX_PROFILE_TOTAL = 64 * 1024 * 1024
MAX_ARCHIVE_SCAN = 40                    # nombre d'archives récentes examinées dans Téléchargements
DOWNLOAD_MAX_AGE_DAYS = 60


class ArchiveError(Exception):
    def __init__(self, key: str, **kw):
        super().__init__(key)
        self.key, self.kw = key, kw


def find_7z() -> str | None:
    exe = shutil.which("7z") or shutil.which("7z.exe") or shutil.which("7zz") or shutil.which("7za")
    if exe:
        return exe
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramW6432")):
        if base and (Path(base) / "7-Zip" / "7z.exe").is_file():
            return str(Path(base) / "7-Zip" / "7z.exe")
    return None


def _safe_rel(name: str) -> Path | None:
    """Chemin relatif sûr (pas de .., pas de lecteur, pas de chemin absolu)."""
    norm = name.replace("\\", "/")
    if norm.startswith("/") or PureWindowsPath(name).anchor or ":" in norm:
        return None                                   # absolu, lecteur, partage réseau //serveur/… (sécurité)
    parts = [p for p in PurePosixPath(norm).parts if p not in ("", ".")]
    if not parts or any(p == ".." or p.startswith("/") for p in parts):
        return None
    return Path(*parts)


def check_archive_limits(entries, archive_name: str):
    """entries : [(nom, taille décompressée)]. Refuse une archive anormale avant d'extraire (sécurité G5)."""
    entries = list(entries)
    if len(entries) > MAX_ARCHIVE_MEMBERS:
        raise ArchiveError("arch_error", name=archive_name, err=f"{len(entries)} files")
    wanted = [(n, s) for n, s in entries if n.lower().endswith((".ini", ".py")) and s <= MAX_MEMBER_SIZE]
    if len(wanted) > MAX_PROFILE_FILES or sum(s for _n, s in wanted) > MAX_PROFILE_TOTAL:
        raise ArchiveError("arch_error", name=archive_name, err="too many / too large profile files")


def _list_7z(exe: str, archive: Path) -> list:
    res = subprocess.run([exe, "l", "-ba", "-slt", str(archive)], capture_output=True, timeout=60,
                         creationflags=0x08000000 if os.name == "nt" else 0)
    out, name = [], None
    for line in res.stdout.decode("utf-8", "ignore").splitlines():
        if line.startswith("Path = "):
            name = line[7:].strip()
        elif line.startswith("Size = ") and name is not None:
            try:
                out.append((name, int(line[7:].strip() or 0)))
            except ValueError:
                out.append((name, 0))
            name = None
    return out


def extract_profiles(archive: Path, dest: Path):
    """Extrait uniquement les .ini et .py d'une archive dans `dest`."""
    ext = archive.suffix.lower()
    if ext == ".zip":
        try:
            with zipfile.ZipFile(archive) as zf:
                check_archive_limits([(i.filename, i.file_size) for i in zf.infolist() if not i.is_dir()],
                                     archive.name)
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith((".ini", ".py")):
                        continue
                    if info.file_size > MAX_MEMBER_SIZE:
                        continue
                    rel = _safe_rel(info.filename)
                    if rel is None:
                        continue
                    target = dest / rel
                    if not target.resolve().is_relative_to(dest.resolve()):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target, "wb") as out:
                        out.write(src.read(MAX_MEMBER_SIZE + 1)[:MAX_MEMBER_SIZE])
        except (zipfile.BadZipFile, OSError, RuntimeError) as e:
            raise ArchiveError("arch_error", name=archive.name, err=e)
        return
    if ext in (".7z", ".rar"):
        exe = find_7z()
        if not exe:
            raise ArchiveError("arch_need_7z", name=archive.name, ext=ext)
        try:
            entries = _list_7z(exe, archive)
        except Exception as e:
            raise ArchiveError("arch_error", name=archive.name, err=e)
        check_archive_limits(entries, archive.name)
        big = [n for n, s in entries if n.lower().endswith((".ini", ".py")) and s > MAX_MEMBER_SIZE]
        if big:
            raise ArchiveError("arch_error", name=archive.name, err=f"{Path(big[0]).name}: too large")
        try:
            res = subprocess.run([exe, "x", "-y", f"-o{dest}", str(archive), "*.ini", "*.py", "-r"],
                                 capture_output=True, timeout=120,
                                 creationflags=0x08000000 if os.name == "nt" else 0)
        except Exception as e:
            raise ArchiveError("arch_error", name=archive.name, err=e)
        if res.returncode not in (0, 1):
            raise ArchiveError("arch_error", name=archive.name,
                               err=res.stderr.decode("utf-8", "ignore").strip()[:300] or res.returncode)
        # garde-fou : rien en dehors de `dest`, rien de trop gros
        for f in list(dest.rglob("*")):
            if f.is_file() and (f.stat().st_size > MAX_MEMBER_SIZE or not f.resolve().is_relative_to(dest.resolve())):
                f.unlink()
        return
    raise ArchiveError("arch_error", name=archive.name, err=ext)


def profiles_in_folder(root: Path) -> list[GsxVariant]:
    files = find_gsx_files(root, sorted(root.rglob("*.ini")))
    return build_gsx_variants(root, files) if files else []


def icaos_of(files: list[Path]) -> set[str]:
    return {f.name[:4].upper() for f in files if f.suffix.lower() == ".ini" and GSX_NAME_RE.match(f.name)}


def _install_profile_files(files: list[Path], dest_dir: Path) -> list[str]:
    """Copie des fichiers de profil dans GSX ; sauvegarde ce qui est remplacé."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    replaced = [dest_dir / f.name for f in files
                if (dest_dir / f.name).is_file() and not same_content(f, dest_dir / f.name)]
    undo_watch(*(dest_dir / f.name for f in files))
    gsx_record(dest_dir, [f.name for f in files])
    if replaced:
        bdir = data_dir() / "backups" / "_GSX" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        bdir.mkdir(parents=True, exist_ok=True)
        for r in replaced:
            shutil.copy2(r, bdir / r.name)
    copied = []
    for f in files:
        shutil.copy2(f, dest_dir / f.name)
        forget_hash(dest_dir / f.name)
        copied.append(f.name)
    gsx_mark_written(dest_dir, copied)
    return copied


def downloads_dir() -> Path:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]
            u = uuid.UUID("374DE290-123F-4565-9164-39C4925E467B")
            g = GUID(u.fields[0], u.fields[1], u.fields[2], (wintypes.BYTE * 8)(*u.bytes[8:]))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) == 0:
                path = out.value
                ctypes.windll.ole32.CoTaskMemFree(out)
                return Path(path)
        except Exception:
            pass
    return Path.home() / "Downloads"


def _names_in_archive(archive: Path) -> list[str]:
    ext = archive.suffix.lower()
    if ext == ".zip":
        with zipfile.ZipFile(archive) as zf:
            return zf.namelist()
    exe = find_7z()
    if not exe:
        return []
    res = subprocess.run([exe, "l", "-ba", "-slt", str(archive)], capture_output=True, timeout=30,
                         creationflags=0x08000000 if os.name == "nt" else 0)
    return [l[7:].strip() for l in res.stdout.decode("utf-8", "ignore").splitlines() if l.startswith("Path = ")]


def archive_key(archive: Path) -> str:
    try:
        return f"{norm_key(archive)}|{archive.stat().st_mtime_ns}"
    except OSError:
        return norm_key(archive)


def find_download_archives(seen: set, folders=None, installed=None) -> list[Path]:
    """Archives récentes des dossiers de téléchargement qui semblent contenir un profil GSX.
    `installed` : noms des .ini déjà présents dans GSX ; une archive dont tous les profils y sont déjà est ignorée."""
    cands = []
    for folder in (folders or [downloads_dir()]):
        try:
            cands += [p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in ARCHIVE_EXT]
        except OSError:
            continue
    installed = {n.lower() for n in (installed or ())}
    limit = time.time() - DOWNLOAD_MAX_AGE_DAYS * 86400
    cands = sorted((p for p in cands if p.stat().st_mtime >= limit), key=lambda p: -p.stat().st_mtime)
    out = []
    for p in cands[:MAX_ARCHIVE_SCAN]:
        if archive_key(p) in seen:
            continue
        try:
            names = _names_in_archive(p)
        except Exception:
            continue
        inis = set()
        for n in names:
            low = n.replace("\\", "/").lower()
            base = low.rsplit("/", 1)[-1]
            if base.endswith(".ini") and (GSX_NAME_RE.match(base) or "gsx" in low):
                inis.add(base)
        if inis and not inis <= installed:
            out.append(p)
    return out


ARCHIVE_CLEANUP = ("ask", "auto", "never")
ARCH_OK, ARCH_CANCEL, ARCH_ERROR = "ok", "cancel", "error"


def in_downloads(path: Path, downloads=None) -> bool:
    """L'archive est directement dans un dossier de téléchargement (jamais dans un sous-dossier ni ailleurs).
    `downloads` : un dossier ou une liste de dossiers (par défaut : Téléchargements de Windows)."""
    if downloads is None:
        downloads = [downloads_dir()]
    elif isinstance(downloads, (str, Path)):
        downloads = [downloads]
    try:
        parent = Path(path).resolve().parent
        return any(parent == Path(d).resolve() for d in downloads)
    except OSError:
        return False


def cleanup_candidates(outcomes: dict, downloads=None) -> list:
    """Archives à proposer à la suppression : installées sans erreur (ou déjà installées à l'identique)
    ET situées dans Téléchargements. Une archive en erreur ou annulée n'est jamais supprimée."""
    return [Path(a) for a, st in outcomes.items() if st == ARCH_OK and in_downloads(a, downloads)]


DRIVE_FIXED = 3


def drive_is_fixed(path: Path) -> bool:
    """Disque fixe (interne ou disque dur USB) : seul cas où la Corbeille de Windows garde le fichier.
    Clé USB, carte mémoire, disque réseau : Windows effacerait définitivement (sécurité G2)."""
    if os.name != "nt":
        return True
    import ctypes
    root = Path(path).resolve().anchor
    if not root:
        return False
    return ctypes.windll.kernel32.GetDriveTypeW(root if root.endswith("\\") else root + "\\") == DRIVE_FIXED


class NotRecyclable(OSError):
    pass


def send_to_trash(path: Path):
    """Envoie un fichier dans la Corbeille de Windows (récupérable). Lève OSError en cas d'échec,
    NotRecyclable si le fichier n'est pas sur un disque fixe (il est alors gardé).
    Hors Windows (tests) : déplacé dans SGM_data/trash."""
    path = Path(path)
    if not path.is_file():
        raise OSError(f"{path.name}: introuvable")
    if not drive_is_fixed(path):
        raise NotRecyclable(tr("trash_not_fixed", name=path.name))
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort),
                        ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", wintypes.LPCWSTR)]
        # SILENT | NOCONFIRMATION | ALLOWUNDO | NOERRORUI | WANTNUKEWARNING (avertir avant tout effacement définitif)
        fo_delete, flags = 3, 0x0004 | 0x0010 | 0x0040 | 0x0400 | 0x4000
        op = SHFILEOPSTRUCTW(None, fo_delete, str(path) + "\0", None, flags, False, None, None)
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if res != 0 or op.fAnyOperationsAborted or path.exists():
            raise OSError(f"{path.name}: {res}")
        return
    trash = data_dir() / "trash"
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / path.name
    n = 1
    while target.exists():
        target = trash / f"{path.stem} ({n}){path.suffix}"
        n += 1
    shutil.move(str(path), str(target))


def trash_archives(paths: list) -> list:
    """Envoie les archives à la Corbeille ; renvoie [(nom, erreur)] pour celles qui ont échoué."""
    failed = []
    for p in paths:
        try:
            send_to_trash(p)
            LOG.info("Archive mise à la corbeille : %s", Path(p).name)
        except NotRecyclable as e:
            LOG.warning("Archive gardée (pas sur un disque fixe) : %s", Path(p).name)
            failed.append((Path(p).name, str(e)))
        except OSError as e:
            LOG.warning("Archive non supprimée : %s (%s)", Path(p).name, e)
            failed.append((Path(p).name, str(e)))
    return failed


# ── Enveloppes journalisées des opérations sur les fichiers ──

def _group_desc(g) -> str:
    names = [x.name for x in (g.active, g.on_path, g.off_path, g.on_file, g.off_file, g.alt_on, g.alt_off) if x]
    return f"{g.mode}[{', '.join(dict.fromkeys(names))}]"


def scene_unchanged(scene: Scene, groups) -> bool:
    """La scène est encore exactement comme à l'analyse (relue sur le disque) : mêmes groupes, mêmes états."""
    if not scene.root.is_dir():
        return False
    try:
        fresh = scan_package(scene.root, scene.source)
    except Exception:
        return False
    if fresh is None:
        return False
    sig = lambda g: (g.mode, str(g.active), g.state, tuple(str(q) for q in g.paths()))
    now = {sig(g) for g in fresh.groups}
    return all(sig(g) in now for g in groups)


def set_scene_state(scene: Scene, target: str):
    groups = [g for g in scene.groups if g.toggleable and g.state != target]
    if not groups:
        return
    # scène déplacée ou modifiée depuis l'analyse : on ne touche à rien (et aucune photo d'origine vide)
    if not scene_unchanged(scene, groups):
        LOG.warning("Bascule refusée, fichiers introuvables : %s", scene_label(scene))
        raise ToggleError(tr("err_scene_gone", name=scene.title))
    LOG.info("Statics %s : %s -> %s ; %s", scene_label(scene), scene.state, target,
             " ; ".join(_group_desc(g) for g in groups))
    try:
        _set_scene_state(scene, target)
    except Exception:
        LOG.exception("Échec de la bascule %s", scene_label(scene))
        raise
    LOG.info("  terminé")


def restore_scene_statics(root: Path):
    LOG.info("Restauration de l'origine : %s", root.name)
    try:
        _restore_scene_statics(root)
    except RestoreError as e:
        LOG.warning("  restauration refusée : %s", e)
        raise
    except Exception:
        LOG.exception("  échec de la restauration")
        raise
    LOG.info("  terminé")


def copy_gsx(scene: Scene, variant: GsxVariant, dest_dir: Path) -> list[str]:
    LOG.info("GSX %s : copie de %s", scene_label(scene), ", ".join(f.name for f in variant.files))
    try:
        out = _copy_gsx(scene, variant, dest_dir)
    except Exception:
        LOG.exception("  échec de la copie GSX")
        raise
    LOG.info("  copié : %s", ", ".join(map(str, out)) or "rien")
    return out


def install_profile_files(files: list[Path], dest_dir: Path) -> list[str]:
    LOG.info("GSX : installation de %s", ", ".join(f.name for f in files))
    try:
        out = _install_profile_files(files, dest_dir)
    except Exception:
        LOG.exception("  échec de l'installation")
        raise
    LOG.info("  installé : %s", ", ".join(map(str, out)) or "rien")
    return out


def gsx_restore(dest_dir: Path, names=None, skipped: list | None = None) -> int:
    skipped = [] if skipped is None else skipped
    n = _gsx_restore(dest_dir, names, skipped)
    if skipped:
        LOG.warning("GSX : profil(s) modifié(s) depuis SGM, laissé(s) tel(s) quel(s) : %s", ", ".join(skipped))
    if n:
        LOG.info("GSX : %d profil(s) remis à l'origine", n)
    return n


ISSUE_FIELDS = {
    "bug": (("what", "What happened?"), ("expected", "What did you expect?"), ("steps", "Steps to reproduce"),
            ("scene", "Scenery concerned (name, developer, ICAO)"), ("message", "Message shown by SGM (if any)")),
    "idea": (("idea", "Your idea"), ("why", "Why would it help you?")),
}
ISSUE_BODY_MAX = 5000          # le texte passe dans l'adresse de la page GitHub : rester bien sous 8 000 caractères


def issue_text(kind: str, sim: str, lang: str, fields: dict | None = None, summary: str = "",
               attachment=(), limit: int | None = ISSUE_BODY_MAX) -> tuple:
    """(titre, texte) de l'issue. Titres de sections en anglais (suivi public), texte de l'utilisateur tel quel,
    dossier personnel retiré. `limit` raccourcit chaque réponse si le total dépasse (texte complet dans le .zip)."""
    kind = "bug" if kind == "bug" else "idea"
    fields = {k: scrub(v).strip() for k, v in (fields or {}).items() if v and str(v).strip()}
    title = ("Bug: " if kind == "bug" else "Idea: ") + scrub(summary).strip()
    names = [attachment] if isinstance(attachment, str) else list(attachment)
    names = [n for n in names if n]
    foot = ("---\n"
            f"SGM v{APP_VERSION} · {sim} · {platform.system()} {platform.release()} · UI language: {lang}\n"
            "_Please do not post personal information (e-mail, full file paths with your user name)._")
    files = ""
    if names:
        files = ("### Files from SGM\n"
                 "Please drag " + ", ".join(f"`{n}`" for n in names) +
                 " (folder opened by SGM) into this box.\n\n")

    def build(cap):
        out = ""
        for key, head in ISSUE_FIELDS[kind]:
            txt = fields.get(key, "")
            if key == "steps" and not txt:
                txt = "1. \n2. "
            if cap is not None and len(txt) > cap:
                txt = txt[:cap].rstrip() + " […] _(full text in the attached file)_"
            out += f"### {head}\n{txt}\n\n"
        return out + files + foot

    body = build(None)
    if limit and len(body) > limit:
        cap = 2000
        while cap > 100 and len(build(cap)) > limit:
            cap = int(cap * 0.8)
        body = build(cap)
    return title, body


def report_url(kind: str, sim: str, lang: str, attachment=(), fields: dict | None = None,
               summary: str = "") -> str:
    """Lien « nouvelle issue » prérempli. Aucune donnée personnelle : ni chemin, ni nom d'utilisateur."""
    title, body = issue_text(kind, sim, lang, fields, summary, attachment)
    return ISSUES_NEW_URL + "?" + urlencode({"title": title, "body": body,
                                            "labels": "bug" if kind == "bug" else "enhancement"})


def build_report_package(kind: str, sim: str, lang: str, fields: dict | None = None, summary: str = "",
                         report: dict | None = None, include_log: bool = False) -> Path:
    """Fichier .zip à glisser dans l'issue : message complet, rapport d'analyse, journal (sans chemin personnel)."""
    d = data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = d / f"sgm-{'bug' if kind == 'bug' else 'idea'}-{stamp}.zip"
    title, body = issue_text(kind, sim, lang, fields, summary, limit=None)
    tmp = out.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("message.md", f"# {title}\n\n{body}\n")
        if report is not None:
            z.writestr("statics-report.json", scrub(json.dumps(report, indent=1, ensure_ascii=False)))
        if include_log:
            for h in LOG.handlers:
                h.flush()
            for f in (log_file().with_name("sgm.log.1"), log_file()):     # précédent puis actuel
                if f.is_file():
                    z.writestr(f.name, scrub(f.read_text(encoding="utf-8", errors="replace")))
    os.replace(tmp, out)
    LOG.info("Paquet de signalement créé : %s (rapport : %s, journal : %s)", out.name,
             "oui" if report is not None else "non", "oui" if include_log else "non")
    return out


# ════════════════════════════════════════════════════════════════════════════
#  Mise à jour automatique (seule connexion Internet de SGM, acceptée par l'utilisateur)
#  Décision de Fabian du 2026-11-15 : GitHub Releases (Fabian publie), vérification au lancement
#  demandée au 1er lancement, téléchargement + empreinte SHA-256 + remplacement après fermeture.
# ════════════════════════════════════════════════════════════════════════════

RELEASES_API = "https://api.github.com/repos/FuchyBe/SGM/releases/latest"
RELEASES_PAGE = "https://github.com/FuchyBe/SGM/releases/latest"
DOWNLOAD_PREFIX = "https://github.com/FuchyBe/SGM/releases/download/"
UPDATE_EVERY = 24 * 3600              # au plus une vérification automatique par jour
UPDATE_MAX_BYTES = 400 * 1024 * 1024
UPDATE_TIMEOUT = 15
UPDATE_DISABLED = bool(os.environ.get("SGM_NO_UPDATE"))   # tests et captures : jamais de réseau


class UpdateError(Exception):
    pass


def parse_version(text: str) -> tuple:
    """« v0.10 », « beta v0.8.1 », « 0.8 » -> (0, 10) / (0, 8, 1) / (0, 8). Vide si illisible."""
    text = str(text or "")
    m = (re.search(r"(?i)\bv(\d+(?:\.\d+)*)", text)          # « v0.10 » d'abord (« SGM 2024 beta v0.10 »)
         or re.search(r"(\d+\.\d+(?:\.\d+)*)", text) or re.fullmatch(r"\s*(\d+)\s*", text))
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def is_newer(remote: str, local: str = APP_VERSION) -> bool:
    r, l = parse_version(remote), parse_version(local)
    if not r or not l:
        return False
    n = max(len(r), len(l))
    return r + (0,) * (n - len(r)) > l + (0,) * (n - len(l))


def should_check_updates(enabled, last_check: float, now: float | None = None) -> bool:
    """`enabled` : None = pas encore demandé, True / False = choix de l'utilisateur."""
    now = time.time() if now is None else now
    return enabled is True and now - float(last_check or 0) >= UPDATE_EVERY


def release_info(data: dict) -> dict | None:
    """Release GitHub -> {version, notes, zip_url, sha_url, page, size}. None si pas une version utilisable :
    brouillon, préversion, pas de .zip SGM, ou adresse de téléchargement hors du dépôt FuchyBe/SGM."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    version = ".".join(map(str, parse_version(data.get("tag_name") or data.get("name") or "")))
    if not version:
        return None
    zips, sha_a = [], None
    for a in data.get("assets") or []:
        name = str(a.get("name") or "")
        url = str(a.get("browser_download_url") or "")
        if not url.startswith(DOWNLOAD_PREFIX) or ".." in url or "/" in name or "\\" in name or ".." in name:
            continue
        low = name.lower()
        if low.startswith("sgm") and low.endswith(".zip"):
            zips.append(a)
        elif low.endswith(".sha256") or low in ("sha256sums.txt", "sha256sums"):
            sha_a = a
    # le paquet de l'application : SGM_vX.Y(.Z).zip (SGM_beta_vX.Y avant la 1.0) ; sinon un seul .zip SGM,
    # jamais un choix au hasard
    exact = [a for a in zips if re.fullmatch(r"sgm_(?:beta_)?v[\d.]+\.zip", str(a["name"]).lower())]
    zip_a = exact[0] if len(exact) == 1 else (zips[0] if len(zips) == 1 else None)
    if zip_a is None:
        return None
    return {"version": version, "notes": str(data.get("body") or "")[:20000],
            "zip_name": zip_a["name"], "zip_url": zip_a["browser_download_url"], "size": int(zip_a.get("size") or 0),
            "sha_url": sha_a["browser_download_url"] if sha_a else "",
            "page": str(data.get("html_url") or RELEASES_PAGE)}


def _http_get(url: str, limit: int = 2 * 1024 * 1024, progress=None) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": f"SGM/{APP_VERSION}",
                                               "Accept": "application/vnd.github+json, */*"})
    with urllib.request.urlopen(req, timeout=UPDATE_TIMEOUT) as r:
        total = int(r.headers.get("Content-Length") or 0)
        if total > limit:
            raise UpdateError("too large")
        out = bytearray()
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            out += chunk
            if len(out) > limit:
                raise UpdateError("too large")
            if progress:
                progress(len(out), total)
    return bytes(out)


def fetch_latest_release(getter=None) -> dict | None:
    """Dernière version publiée, ou None s'il n'y en a pas encore (GitHub répond 404 tant qu'aucune release
    n'est publiée : un brouillon ne compte pas). Autre problème réseau : UpdateError."""
    getter = getter or _http_get
    try:
        data = json.loads(getter(RELEASES_API).decode("utf-8"))
    except UpdateError:
        raise
    except Exception as e:
        if getattr(e, "code", None) == 404:
            return None
        raise UpdateError(str(e))
    return release_info(data)


def expected_sha256(text: str, zip_name: str) -> str:
    """Empreinte attendue dans un fichier « <hash>  <nom> » (ou un hash seul)."""
    for line in str(text).splitlines():
        parts = line.strip().split()
        if not parts or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            continue
        if len(parts) == 1 or parts[-1].lstrip("*").lower() == zip_name.lower():
            return parts[0].lower()
    return ""


def unpack_update(zip_path: Path, dest: Path) -> Path:
    """Extrait la nouvelle version (chemins sûrs uniquement) et rend le dossier qui contient SGM.exe."""
    with zipfile.ZipFile(zip_path) as z:
        total = 0
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in PurePosixPath(name).parts or ":" in name:
                raise UpdateError(f"unsafe path: {name}")
            total += info.file_size
            if total > UPDATE_MAX_BYTES * 2:
                raise UpdateError("too large")
        z.extractall(dest)
    exe = [p for p in dest.rglob("SGM.exe") if "SGM_data" not in p.parts]
    if len(exe) != 1:
        raise UpdateError("SGM.exe not found in the archive")
    return exe[0].parent


def _bat(path) -> str:
    """Chemin pour un script .bat : les % sont doublés (sinon lus comme variables)."""
    return str(path).replace("%", "%%")


def updater_script(src: Path, dst: Path, pid: int, backup: Path, log: Path, reg_version: str = "") -> str:
    """Script Windows lancé après la fermeture de SGM : sauvegarde des SEULS éléments que la nouvelle version
    remplace, copie de la nouvelle version (SGM_data jamais touché), retour à l'ancienne en cas d'échec, relance.
    `src` doit exister (liste des éléments à remplacer). Version installée (`reg_version`) : le numéro affiché dans
    « Applications installées » de Windows est mis à jour aussi (clé de l'utilisateur, aucune élévation)."""
    items = sorted(p.name for p in Path(src).iterdir() if p.name.lower() != "sgm_data")
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "setlocal DisableDelayedExpansion",
        f'set "SRC={_bat(src)}"',
        f'set "DST={_bat(dst)}"',
        f'set "BAK={_bat(backup)}"',
        f'set "LOG={_bat(log)}"',
        f'echo SGM : mise a jour en attente de la fermeture (PID {int(pid)}) > "%LOG%"',
        ":wait",
        f'tasklist /FI "PID eq {int(pid)}" /FI "IMAGENAME eq SGM.exe" /NH 2>nul | find /I "SGM.exe" >nul '
        '&& (timeout /t 1 /nobreak >nul & goto wait)',
    ]
    copy = '/R:3 /W:1 /NFL /NDL /NJH /NJS >> "%LOG%"'
    for it in items:                                   # 1. sauvegarde de ce qui va être remplacé
        n = _bat(it)
        if (Path(src) / it).is_dir():
            lines.append(f'if exist "%DST%\\{n}\\" robocopy "%DST%\\{n}" "%BAK%\\{n}" /E {copy}')
        else:
            lines.append(f'if exist "%DST%\\{n}" robocopy "%DST%" "%BAK%" "{n}" {copy}')
        lines.append("if %ERRORLEVEL% GEQ 8 goto fail")
    for it in items:                                   # 2. copie de la nouvelle version
        n = _bat(it)
        if (Path(src) / it).is_dir():
            lines.append(f'robocopy "%SRC%\\{n}" "%DST%\\{n}" /E {copy}')
        else:
            lines.append(f'robocopy "%SRC%" "%DST%" "{n}" {copy}')
        lines.append("if %ERRORLEVEL% GEQ 8 goto rollback")
    lines.append('echo OK >> "%LOG%"')
    ver = re.sub(r"[^0-9.]", "", str(reg_version or ""))
    if ver:
        key = f"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{INSTALL_APP_ID}_is1"
        lines.append(f'reg add "{key}" /v DisplayVersion /t REG_SZ /d "{ver}" /f >nul 2>&1')
    lines += ['start "" "%DST%\\SGM.exe"', "goto end", ":rollback",
              'echo ECHEC : retour a la version precedente >> "%LOG%"',
              'robocopy "%BAK%" "%DST%" /E /R:5 /W:1 /NFL /NDL /NJH /NJS >> "%LOG%"',
              ":fail", 'start "" "%DST%\\SGM.exe"', ":end", "endlocal", ""]
    return "\r\n".join(lines)


def prepare_update(info: dict, progress=None, getter=None, base: Path | None = None) -> dict:
    """Télécharge le .zip et son empreinte, vérifie le SHA-256, extrait, écrit le script de remplacement.
    Ne modifie pas encore l'application. UpdateError("sha") si l'empreinte ne correspond pas."""
    getter = getter or _http_get
    if not info.get("sha_url"):
        raise UpdateError("no_sha")
    base = base or (data_dir() / "update")
    work = base / info["version"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    want = expected_sha256(getter(info["sha_url"]).decode("utf-8", "replace"), info["zip_name"])
    if not want:
        raise UpdateError("no_sha")
    data = getter(info["zip_url"], UPDATE_MAX_BYTES, progress)
    if hashlib.sha256(data).hexdigest() != want:
        raise UpdateError("sha")
    zp = work / info["zip_name"]
    zp.write_bytes(data)
    src = unpack_update(zp, work / "new")
    script = base / "sgm-update.bat"
    log = base / "update.log"
    backup = base / f"backup-v{APP_VERSION}"
    shutil.rmtree(backup, ignore_errors=True)
    script.write_text(updater_script(src, app_dir(), os.getpid(), backup, log,
                                     reg_version=info["version"] if is_installed() else ""), encoding="utf-8")
    LOG.info("Mise à jour v%s préparée (SHA-256 vérifié)", info["version"])
    return {"version": info["version"], "script": script, "src": src}


def running_sims() -> list | None:
    """Simulateurs MSFS en cours d'exécution (les deux versions : origin/, undo/ et _GSX leur sont communs).
    None si la liste des programmes n'a pas pu être lue (état inconnu, sécurité G3)."""
    if os.name != "nt":
        return []
    try:
        res = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                             timeout=10, creationflags=0x08000000)
        if res.returncode != 0:
            return None
        out = res.stdout.decode("utf-8", errors="ignore").lower()
    except Exception:
        return None
    return [s for s in SIMS if f'"{SIMS[s]["process"]}"' in out]


SIM_OPEN, SIM_CLOSED, SIM_UNKNOWN = "ouvert", "fermé", "inconnu"


def sim_state(sim: str) -> str:
    """État du simulateur à trois états (accroche S7)."""
    running = running_sims()
    if running is None:
        return SIM_UNKNOWN
    return SIM_OPEN if sim in running else SIM_CLOSED


def sim_running(sim: str) -> bool:
    return sim_state(sim) == SIM_OPEN


# ════════════════════════════════════════════════════════════════════════════
#  Interface
# ════════════════════════════════════════════════════════════════════════════

C = {
    "bg": "#0E1014", "surface": "#161920", "surface2": "#1C2029", "border": "#232833",
    "border2": "#2D3441", "text": "#E7E9ED", "muted": "#8B93A5", "faint": "#5E6678",
    "accent": "#4CC9A0", "accent_dark": "#0A1A14", "warn": "#E3B266", "blue": "#7AA7F5",
    "heart": "#E2677A",
    # Jetons de thème (accroche S4 pour une application hôte) : valeurs = rendu sombre actuel de SGM
    "text2": "#C9CED8", "doc_text": "#C9CED8", "hover": "#232835", "sel": "#232835", "pressed": "#1A1E27",
    "accent_hover": "#5DD6AE", "accent_dis_bg": "#2A4A40", "accent_dis_fg": "#5E7A70", "accent_soft": "#12241E",
    "accent_line": "#2B5A4B", "accent_pressed": "#183026",
    "off_text": "#E07A72", "off_text_hover": "#F09088", "off_line": "#5A2D2A", "off_soft": "#1F1413",
    "off_soft_hover": "#2A1817",
    "warn_soft": "#221C12", "warn_line": "#4A3A1E", "warn_soft_hover": "#2C2416",
    "blue_soft": "#141C2A", "blue_soft2": "#172235", "blue_line": "#2E4670", "banner_line": "#263A5C",
    "danger": "#B5443D", "danger_hover": "#C85149", "danger_pressed": "#9E3A34", "danger_dis_bg": "#4A2725",
    "danger_dis_fg": "#8A6360", "on_danger": "#FFF4F3",
    "row_hover": "#181C24", "scroll_hover": "#3A4352", "heart_hover": "#F07F90",
    "knob": "#F3F5F7", "switch_off": "#2A303C", "track_dis": "#20242D", "knob_dis": "#4A5161", "menubar": "#0E1014",
}
SWITCH_MARKS = False        # accroche S5 : l'hôte peut dessiner ✓ / ✗ dans les interrupteurs

def build_qss(C: dict, font_scale: float = 1.0) -> str:
    """Feuille de style à partir des jetons de couleur (accroche S4). SGM seul : build_qss(C) = rendu actuel."""
    def px(n: int) -> str:
        return f"{max(1, round(n * font_scale))}px"
    return f"""
* {{ font-size: {px(13)}; }}
QMainWindow, QDialog, QWidget#central, QWidget#list {{ background: {C['bg']}; color: {C['text']}; }}
QLabel {{ background: transparent; color: {C['text']}; }}
QLabel#h1 {{ font-size: {px(21)}; font-weight: 600; letter-spacing: 0.3px; }}
QLabel#h2 {{ font-size: {px(14)}; font-weight: 600; color: {C['text']}; }}
QLabel#subtitle, QLabel#sub, QLabel#status, QLabel#hint {{ color: {C['muted']}; }}
QLabel#sub {{ font-size: {px(12)}; }}
QLabel#status {{ font-size: {px(12)}; }}
QLabel#stats {{ color: {C['muted']}; font-size: {px(12)}; }}
QLabel#title {{ font-size: {px(14)}; font-weight: 600; }}
QLabel#empty {{ color: {C['faint']}; font-size: {px(14)}; padding: 40px; }}
QLabel#fullname {{ color: {C['muted']}; font-size: {px(15)}; font-weight: 500; padding-bottom: 2px; }}
QLabel#simPill {{ color: {C['blue']}; border: 1px solid {C['blue_line']}; background: {C['blue_soft']}; border-radius: 5px;
                  padding: 2px 8px; font-size: {px(11)}; font-weight: 700; letter-spacing: 0.6px; }}
QLabel#credit {{ color: {C['faint']}; font-size: {px(11)}; padding: 0 6px; }}
QMenuBar {{ background: {C['menubar']}; color: {C['muted']}; border-bottom: 1px solid {C['border']}; padding: 2px 8px; }}
QMenuBar::item {{ background: transparent; padding: 5px 10px; border-radius: 5px; }}
QMenuBar::item:selected {{ background: {C['surface2']}; color: {C['text']}; }}
QMenu {{ background: {C['surface']}; color: {C['text']}; border: 1px solid {C['border2']}; padding: 5px; }}
QMenu::item {{ padding: 6px 26px 6px 22px; border-radius: 5px; }}
QMenu::item:selected {{ background: {C['surface2']}; }}
QMenu::item:disabled {{ color: {C['faint']}; }}
QMenu::separator {{ height: 1px; background: {C['border']}; margin: 5px 8px; }}
QToolButton#cornerBtn {{ background: transparent; border: 1px solid transparent; border-radius: 5px;
                         color: {C['muted']}; padding: 2px 6px; font-size: {px(11)}; font-weight: 700; letter-spacing: 0.5px; }}
QToolButton#cornerBtn:hover {{ background: {C['surface2']}; border-color: {C['border2']}; color: {C['text']}; }}
QToolButton#cornerBtn::menu-indicator {{ image: none; width: 0; }}
QPushButton#varChip {{ background: transparent; color: {C['muted']}; border: 1px solid {C['border2']};
                      border-radius: 6px; padding: 4px 10px; font-size: {px(12)}; }}
QPushButton#varChip:hover {{ color: {C['text']}; background: {C['surface2']}; }}
QPushButton#varChip[vstate="active"] {{ color: {C['accent']}; border-color: {C['accent_line']}; background: {C['accent_soft']}; font-weight: 600; }}
QPushButton#varChip[vstate="inactive"] {{ color: {C['off_text']}; border-color: {C['off_line']}; background: {C['off_soft']}; }}
QPushButton#varChip[vstate="inactive"]:hover {{ color: {C['off_text_hover']}; background: {C['off_soft_hover']}; }}
QPushButton#varChip[vstate="check"] {{ color: {C['warn']}; border-color: {C['warn_line']}; background: {C['warn_soft']}; }}
QPushButton#varChip[vstate="check"]:hover {{ background: {C['warn_soft_hover']}; }}
QComboBox {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']};
             border-radius: 6px; padding: 3px 8px; font-size: {px(12)}; }}
QComboBox QAbstractItemView {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']};
                               selection-background-color: {C['sel']}; }}
QLabel#note[ok="true"] {{ color: {C['accent']}; }}
QLabel#gsxManual {{ color: {C['accent']}; border: 1px solid {C['accent_line']}; background: {C['accent_soft']}; border-radius: 6px;
                   padding: 4px 10px; font-size: {px(12)}; }}
QPushButton#searchBtn {{ background: transparent; color: {C['muted']}; border: 1px dashed {C['border2']};
                        border-radius: 6px; padding: 4px 9px; font-size: {px(12)}; }}
QPushButton#searchBtn:hover {{ color: {C['blue']}; border-color: {C['blue_line']}; background: {C['blue_soft']}; }}
QComboBox#catCombo {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 9px;
                      padding: 8px 34px 8px 12px; font-size: {px(13)}; min-width: 190px; }}
QComboBox#catCombo:hover {{ border-color: {C['border2']}; }}
QComboBox#colFilter {{ background: transparent; border: 1px solid {C['border']}; border-radius: 7px;
                      padding: 2px 26px 2px 9px; color: {C['muted']}; font-size: {px(11)}; font-weight: 600; min-height: 20px; }}
QComboBox#colFilter:hover {{ border-color: {C['border2']}; color: {C['text']}; }}
QComboBox#colFilter[active="true"] {{ border-color: {C['accent']}; color: {C['accent']}; background: {C['surface']}; }}
QComboBox#colFilter::drop-down {{ border: none; width: 22px; }}
QComboBox#colFilter::down-arrow {{ image: none; width: 0; height: 0; }}
QPushButton#linkBtn {{ background: transparent; border: none; color: {C['accent']}; padding: 4px 6px; }}
QPushButton#linkBtn:hover {{ text-decoration: underline; }}
QFrame#colHandle {{ background: transparent; border: none; }}
QComboBox#catCombo::drop-down {{ border: none; width: 30px; }}
QComboBox#catCombo::down-arrow {{ image: none; width: 0; height: 0; }}
QPushButton#folderBtn {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
                        padding: 0; min-width: 26px; max-width: 26px; min-height: 24px; max-height: 24px; }}
QPushButton#folderBtn:hover {{ background: {C['surface2']}; border-color: {C['border2']}; }}
QPushButton#folderBtn:pressed {{ background: {C['hover']}; }}
QLabel#badgeNew {{ color: {C['blue']}; border: 1px solid {C['blue_line']}; background: {C['blue_soft2']};
                   border-radius: 4px; padding: 1px 6px; font-size: {px(10)}; font-weight: 700; letter-spacing: 0.8px; }}
QLabel#chip {{ color: {C['faint']}; border: 1px solid {C['border2']}; border-radius: 4px;
               padding: 1px 6px; font-size: {px(11)}; }}
QLabel#state {{ font-size: {px(12)}; font-weight: 600; min-width: 92px; }}
QLabel#state[state="on"] {{ color: {C['accent']}; }}
QLabel#state[state="off"] {{ color: {C['muted']}; }}
QLabel#state[state="none"] {{ color: {C['faint']}; font-weight: 400; }}
QLabel#state[state="mixed"], QLabel#state[state="conflict"] {{ color: {C['warn']}; }}
QLabel#src {{ color: {C['muted']}; font-size: {px(11)}; font-weight: 700; letter-spacing: 0.6px; min-width: 70px; }}
QLabel#path {{ color: {C['text']}; }}
QLabel#missing {{ color: {C['warn']}; font-size: {px(11)}; }}
QLineEdit {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 8px;
             padding: 7px 11px; color: {C['text']}; selection-background-color: {C['accent']}; }}
QLineEdit:focus {{ border-color: {C['border2']}; background: {C['surface2']}; }}
QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']};
               border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: {C['hover']}; border-color: {C['border2']}; }}
QPushButton:pressed {{ background: {C['pressed']}; }}
QPushButton:disabled {{ color: {C['faint']}; background: {C['surface']}; }}
QPushButton#primary {{ background: {C['accent']}; color: {C['accent_dark']}; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: {C['accent_hover']}; }}
QPushButton#primary:disabled {{ background: {C['accent_dis_bg']}; color: {C['accent_dis_fg']}; }}
QPushButton#danger {{ background: {C['danger']}; color: {C['on_danger']}; border: none; font-weight: 600; }}
QPushButton#danger:hover {{ background: {C['danger_hover']}; }}
QPushButton#danger:pressed {{ background: {C['danger_pressed']}; }}
QPushButton#danger:disabled {{ background: {C['danger_dis_bg']}; color: {C['danger_dis_fg']}; }}
QPushButton#chipBtn {{ background: transparent; border: 1px solid transparent; color: {C['muted']};
                       padding: 5px 11px; border-radius: 7px; }}
QPushButton#chipBtn:hover {{ color: {C['text']}; }}
QPushButton#chipBtn:checked {{ background: {C['surface2']}; border-color: {C['border2']}; color: {C['text']}; }}
QPushButton#gsx {{ background: transparent; color: {C['blue']}; border: 1px solid {C['blue_line']};
                  border-radius: 6px; padding: 4px 10px; font-size: {px(12)}; }}
QPushButton#gsx:hover {{ background: {C['blue_soft2']}; }}
QPushButton#gsx[gsx="same"] {{ color: {C['muted']}; border-color: {C['border2']}; }}
QPushButton#gsx[gsx="diff"] {{ color: {C['warn']}; border-color: {C['warn_line']}; }}
QFrame#vsep {{ background: {C['border']}; min-width: 1px; max-width: 1px; border: none; }}
QFrame#vsepHidden {{ background: transparent; min-width: 1px; max-width: 1px; border: none; }}
QLabel#colHead {{ color: {C['muted']}; font-size: {px(10)}; font-weight: 700; letter-spacing: 1.2px; }}
QLabel#colHead[plain="true"] {{ font-size: {px(11)}; letter-spacing: 0px; }}
QLabel#note {{ color: {C['muted']}; font-size: {px(11)}; }}
QLabel#note[warn="true"] {{ color: {C['warn']}; }}
QLabel#none {{ color: {C['muted']}; font-size: {px(12)}; }}
QPushButton#ghost {{ background: transparent; border: none; color: {C['muted']}; padding: 4px 8px; }}
QPushButton#ghost:hover {{ color: {C['text']}; }}
QFrame#chips {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 9px; }}
QFrame#row {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 10px; }}
QFrame#row:hover {{ border-color: {C['border2']}; background: {C['row_hover']}; }}
QFrame#banner {{ background: {C['blue_soft']}; border: 1px solid {C['banner_line']}; border-radius: 9px; }}
QFrame#banner[kind="warn"] {{ background: {C['warn_soft']}; border-color: {C['warn_line']}; }}
QFrame#sep {{ background: {C['border']}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#folderRow {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['border2']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C['scroll_hover']}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QToolTip {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']}; padding: 6px; }}
QMessageBox {{ background: {C['surface']}; }}
QPlainTextEdit {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 8px;
                  padding: 5px 8px; color: {C['text']}; selection-background-color: {C['accent']}; }}
QPlainTextEdit:focus {{ border-color: {C['border2']}; background: {C['surface2']}; }}
QPlainTextEdit#preview {{ color: {C['muted']}; font-family: Consolas, "Cascadia Mono", monospace; font-size: {px(11)}; }}
QFrame#bulkSeg {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 13px;
                  min-height: 24px; max-height: 24px; }}
QFrame#bulkSeg:hover {{ border-color: {C['border2']}; }}
QFrame#bulkDiv {{ background: {C['border2']}; min-width: 1px; max-width: 1px; border: none; margin: 5px 0; }}
QPushButton#bulkOff, QPushButton#bulkOn {{ background: transparent; border: none; border-radius: 11px;
    padding: 0 7px; min-height: 22px; max-height: 22px; font-size: {px(11)}; font-weight: 600; color: {C['muted']}; }}
QPushButton#bulkOff:hover {{ color: {C['off_text']}; background: {C['off_soft']}; }}
QPushButton#bulkOn:hover {{ color: {C['accent']}; background: {C['accent_soft']}; }}
QPushButton#bulkOff:pressed {{ background: {C['off_soft_hover']}; }}
QPushButton#bulkOn:pressed {{ background: {C['accent_pressed']}; }}
QPushButton#bulkOff:disabled, QPushButton#bulkOn:disabled {{ color: {C['faint']}; }}
QLabel#fieldLabel {{ color: {C['muted']}; font-size: {px(12)}; }}
QCheckBox {{ color: {C['text']}; spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {C['border2']}; border-radius: 4px;
                        background: {C['surface']}; }}
QCheckBox::indicator:checked {{ background: {C['accent']}; border-color: {C['accent']}; }}
QTextBrowser#doc {{ background: {C['surface']}; color: {C['text']}; border: 1px solid {C['border']};
                    border-radius: 10px; padding: 14px 18px; font-size: {px(13)}; }}
"""


QSS = build_qss(C)

def build_doc_css(C: dict, font_scale: float = 1.0) -> str:
    """Style des fenêtres de documentation (guide, licences) à partir des jetons (accroche S4)."""
    def px(n: int) -> str:
        return f"{max(1, round(n * font_scale))}px"
    return f"""
h2 {{ color: {C['text']}; font-size: {px(18)}; margin: 0 0 8px 0; }}
h3 {{ color: {C['accent']}; font-size: {px(14)}; margin: 16px 0 4px 0; }}
p, li {{ color: {C['text2']}; line-height: 140%; }}
i {{ color: {C['muted']}; }}
b {{ color: {C['text']}; }}
a {{ color: {C['blue']}; }}
"""


DOC_CSS = build_doc_css(C)


def blend(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def ask(parent, text: str, default_yes=True) -> bool:
    """Question Oui / Non avec des boutons traduits."""
    box = QMessageBox(parent)
    box.setWindowTitle(APP_NAME)
    box.setText(text)
    box.setIcon(QMessageBox.Question)
    yes = box.addButton(tr("yes"), QMessageBox.YesRole)
    no = box.addButton(tr("no"), QMessageBox.NoRole)
    box.setDefaultButton(yes if default_yes else no)
    box.exec()
    return box.clickedButton() is yes


def warn(parent, text: str):
    LOG.warning("Alerte affichée : %s", " ".join(str(text).split()))
    QMessageBox.warning(parent, APP_NAME, text)


class Switch(QAbstractButton):
    """Interrupteur animé."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._knob = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _get_knob(self):
        return self._knob

    def _set_knob(self, v):
        self._knob = v
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def set_checked_silent(self, checked: bool):
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._anim.stop()
        self._knob = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        track = blend(QColor(C["switch_off"]), QColor(C["accent"]), self._knob)
        knob = QColor(C["knob"])
        if not self.isEnabled():
            track, knob = QColor(C["track_dis"]), QColor(C["knob_dis"])
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = self.height() - 6
        t = self._knob if self.layoutDirection() == Qt.LeftToRight else 1 - self._knob
        x = 3 + t * (self.width() - 6 - d)
        p.setBrush(knob)
        p.drawEllipse(QRectF(x, 3, d, d))
        if SWITCH_MARKS:                       # accroche S5 : ✓ / ✗ dans la piste, côté opposé au bouton
            on = self._knob >= 0.5
            ltr = self.layoutDirection() == Qt.LeftToRight
            side = 3 if on == ltr else self.width() - 3 - d
            draw_check_mark(p, QRectF(side, 3, d, d), on, knob)

    def sizeHint(self):
        return self.size()


def draw_check_mark(p: QPainter, box: QRectF, on: bool, color):
    """Petit ✓ (on) ou ✗ (off) dessiné dans `box` (accroche S5, utilisée si SWITCH_MARKS)."""
    pen = QPen(QColor(color), max(1.4, box.width() / 8))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.save()
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    m = box.width() * 0.28
    b = box.adjusted(m, m, -m, -m)
    path = QPainterPath()
    if on:
        path.moveTo(b.left(), b.center().y())
        path.lineTo(b.left() + b.width() * 0.4, b.bottom())
        path.lineTo(b.right(), b.top())
    else:
        path.moveTo(b.topLeft())
        path.lineTo(b.bottomRight())
        path.moveTo(b.topRight())
        path.lineTo(b.bottomLeft())
    p.drawPath(path)
    p.restore()


class ChevronCombo(QComboBox):
    """Liste déroulante avec une petite flèche dessinée (le style sombre masque celle d'origine)."""

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(C["muted"]), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        cx = 18 if self.layoutDirection() == Qt.RightToLeft else self.width() - 18
        cy = self.height() / 2 + 1
        path = QPainterPath()
        path.moveTo(cx - 4.5, cy - 2.5)
        path.lineTo(cx, cy + 2)
        path.lineTo(cx + 4.5, cy - 2.5)
        p.drawPath(path)


class CheckBox(QCheckBox):
    """Case à cocher avec une vraie coche dessinée (l'état ne passe pas seulement par la couleur)."""

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self.isChecked():
            return
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        r = self.style().subElementRect(QStyle.SE_CheckBoxIndicator, opt, self)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_check_mark(p, QRectF(r).adjusted(-1, -1, 1, 1), True, C["accent_dark"])
        p.end()


_LTR_RE = re.compile(r"[\w*.\-]*\.[\w.*\-]+(?:\s*(?:↔|->|→)\s*[\w*.\-]*\.[\w.*\-]+)?")


def ltr_fragments(text: str) -> str:
    """Interface de droite à gauche : noms de fichiers (.bgl ↔ .bgl.off) isolés en gauche-à-droite."""
    return _LTR_RE.sub(lambda m: "\u202a" + m.group(0) + "\u202c", text)   # LRE … PDF (rendu sûr dans Qt)


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self._refresh()

    def setFullText(self, t: str):
        self._full = t
        self._refresh()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()

    def _refresh(self):
        full = ltr_fragments(self._full) if get_lang() in RTL_LANGS else self._full
        super().setText(self.fontMetrics().elidedText(full, Qt.ElideRight, max(10, self.width())))


def state_text(st: str) -> str:
    return tr({ON: "st_on", OFF: "st_off", MIXED: "st_mixed", CONFLICT: "st_conflict", NONE: "st_none"}[st])


GROUP_STATE_KEY = {ON: "grp_on", OFF: "grp_off", UNKNOWN: "grp_unknown", CONFLICT: "grp_conflict"}
MODE_KEY = {"rename": "mode_rename", "variant": "mode_variant", "swap": "mode_swap", "rswap": "mode_swap", "pair": "mode_pair",
            "conflict": "mode_conflict"}
MODE_NOTE_KEY = {"rename": "note_rename", "variant": "note_variant", "swap": "note_swap", "rswap": "note_swap", "pair": "note_pair",
                 "conflict": "note_conflict"}


def mode_note(groups: list, mode: str) -> str:
    if mode == "rswap":
        return tr("note_swap_x", alt=".bgl.nostatic / .static")
    if mode == "swap":
        alts = sorted({"." + parse_form(g.off_file.name)[1] for g in groups if g.mode == "swap" and g.off_file})
        return tr("note_swap_x", alt=" / ".join(alts))
    if mode == "rename":
        forms = {g.off_form for g in groups if g.mode == "rename" and g.off_form}
        if forms and forms != {"bgl.off"}:
            return tr("note_rename_x", off=" / ".join("." + f for f in sorted(forms)))
    return tr(MODE_NOTE_KEY[mode])
GSX_TEXT_KEY = {GSX_MISSING: "gsx_copy", GSX_SAME: "gsx_same", GSX_DIFF: "gsx_diff"}
GSX_INFO_KEY = {GSX_MISSING: "gsx_info_missing", GSX_SAME: "gsx_info_same", GSX_DIFF: "gsx_info_diff"}

FILTER_KEYS = ("all", "on", "off", "new", "check")
CATEGORY_KEYS = ("all", "statics", "gsx_scene", "gsx_manual", "gsx_none")

COL_STATICS_W = 330          # largeurs de départ (×1,5 depuis la v0.7)
COL_GSX_W = 450
COL_STATICS_MIN = 250        # minimums : bascule, boutons et icônes toujours visibles
COL_GSX_MIN = 320
COL_SCENE_MIN = 230
COMPACT_BELOW = 1040         # largeur de liste sous laquelle l'en-tête passe en version courte
COL_REF_W = 1200             # largeur de liste de référence pour les proportions par défaut
STATICS_FILTERS = ("all", "on", "off", "check", "none")
GSX_FILTERS = ("all", "installed", "todo", "manual", "none", "check")


ROW_MARGINS = (16, 11, 14, 11)
ROW_SPACING = 16
COL_OVERHEAD = ROW_MARGINS[0] + ROW_MARGINS[2] + 4 * ROW_SPACING + 4


def fit_widths(avail: int, natural: tuple, floors: tuple) -> tuple[int, int]:
    """Mode automatique : chaque colonne prend la largeur de son texte sur une ligne, la colonne scène
    garde tout le reste. Fenêtre trop étroite : réduction proportionnelle, jamais sous `floors`."""
    ns, ng = max(natural[0], floors[0]), max(natural[1], floors[1])
    room = avail - COL_SCENE_MIN - COL_OVERHEAD
    if ns + ng <= room:
        return ns, ng
    extra_s, extra_g = ns - floors[0], ng - floors[1]
    cut = min(ns + ng - room, extra_s + extra_g)
    if extra_s + extra_g <= 0:
        return ns, ng
    cg = min(cut, extra_g)                     # la colonne GSX cède d'abord : le nom de la scène reste lisible
    return ns - (cut - cg), ng - cg


def column_widths(avail: int, fs: float, fg: float, mins=(COL_STATICS_MIN, COL_GSX_MIN)) -> tuple[int, int]:
    """Largeurs des colonnes Statics et GSX pour une liste de `avail` px, proportions fs / fg,
    minimums respectés et colonne scène jamais sous son minimum."""
    ms, mg = mins
    ws, wg = max(ms, round(avail * fs)), max(mg, round(avail * fg))
    excess = ws + wg + COL_SCENE_MIN + COL_OVERHEAD - avail
    if excess > 0:                         # fenêtre étroite : on réduit Statics et GSX jusqu'à leurs minimums
        room_s, room_g = ws - ms, wg - mg
        room = room_s + room_g
        if room > 0:
            cut = min(excess, room)
            ws -= round(cut * room_s / room)
            wg -= cut - round(cut * room_s / room)
    return ws, wg


def vsep(visible=True) -> QFrame:
    f = QFrame()
    f.setObjectName("vsep" if visible else "vsepHidden")
    return f


def polish(w, **props):
    for k, v in props.items():
        w.setProperty(k, v)
    w.style().unpolish(w)
    w.style().polish(w)


def column(width: int):
    w = QWidget()
    w.setFixedWidth(width)
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(5)
    return w, v


def simple_statics(scene) -> bool:
    """Scène basculable en bloc sans risque : entièrement ON ou OFF, aucun fichier ambigu."""
    return (scene.toggleable and scene.state in (ON, OFF)
            and not any(g.mode == "conflict" for g in scene.groups))


def profile_from_scenes(scenes) -> dict:
    """État actuel des scènes simples, à enregistrer comme profil."""
    return {s.key: ("on" if s.state == ON else "off") for s in scenes if simple_statics(s)}


def profile_plan(profile: dict, scenes) -> tuple:
    """(liste (scène, cible) à basculer, scènes du profil à vérifier, scènes du profil introuvables).
    Les scènes absentes du profil ne sont jamais touchées."""
    by_key = {s.key: s for s in scenes}
    todo, check, missing = [], 0, 0
    for key, want in profile.items():
        s = by_key.get(key)
        if s is None:
            missing += 1
        elif not simple_statics(s):
            check += 1
        elif s.state != (ON if want == "on" else OFF):
            todo.append((s, ON if want == "on" else OFF))
    return todo, check, missing


def bulk_targets(rows, target: str) -> tuple:
    """Tout ON / Tout OFF : seulement les cas simples (scène entièrement ON ou OFF, aucun fichier à vérifier).
    Rend (scènes à basculer, nombre de scènes « À vérifier » laissées telles quelles)."""
    targets, skipped = [], 0
    for r in rows:
        st = r.statics_state()
        if st == "check":
            skipped += 1
        elif st in ("on", "off") and r.scene.state != target and r.scene.toggleable \
                and not any(g.mode == "conflict" for g in r.scene.groups):
            targets.append(r.scene)
    return targets, skipped


class ColHandle(QFrame):
    """Séparateur d'en-tête qu'on peut tirer pour régler la largeur des colonnes."""
    dragged = Signal(int)
    released = Signal()
    reset = Signal()                           # double-clic : retour à l'ajustement automatique

    def __init__(self):
        super().__init__()
        self.setObjectName("colHandle")
        self.setCursor(Qt.SplitHCursor)
        self.setFixedWidth(9)
        self.setToolTip(tr("tip_col_resize"))
        self._x = None

    def mousePressEvent(self, e):
        self._x = e.globalPosition().x()

    def mouseMoveEvent(self, e):
        if self._x is None:
            return
        x = e.globalPosition().x()
        dx = round(x - self._x)
        if dx:
            self._x = x
            self.dragged.emit(-dx if self.layoutDirection() == Qt.RightToLeft else dx)

    def mouseReleaseEvent(self, _e):
        self._x = None
        self.released.emit()

    def mouseDoubleClickEvent(self, _e):
        self._x = None
        self.reset.emit()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        # trait au centre, exactement sous le séparateur des lignes ; plus épais et coloré au survol
        p = QPainter(self)
        hover = self.underMouse() or self._x is not None
        w = 2 if hover else 1
        p.fillRect(QRectF((self.width() - w) / 2, 4, w, self.height() - 8),
                   QColor(C["accent"] if hover else C["border"]))


class ColumnHeader(QWidget):
    """En-têtes alignés sur les colonnes des lignes, avec un filtre identique pour Statics et GSX
    et des poignées pour régler les largeurs."""
    filter_changed = Signal(str, str)          # colonne ("statics" / "gsx"), clé du filtre
    bulk_requested = Signal(str)               # Tout OFF / Tout ON (cas simples affichés)

    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self)
        l, _t, r, _b = ROW_MARGINS
        h.setContentsMargins(l + 1, 0, r + 1, 0)
        h.setSpacing(ROW_SPACING - 4)        # poignée de 9 px : son trait central tombe sur le séparateur des lignes
        scene = QLabel(tr("col_scene"))
        scene.setObjectName("colHead")
        # Arabe, chinois, japonais : pas de capitales ; l'espacement des lettres casserait la liaison arabe
        plain = get_lang() in ("ar", "zh", "ja")
        scene.setProperty("plain", plain)
        h.addWidget(scene, 1)
        self.handles = [ColHandle(), ColHandle()]
        self.boxes, self.combos = {}, {}
        for i, (col, key, filters) in enumerate((("statics", "col_statics", STATICS_FILTERS),
                                                  ("gsx", "col_gsx", GSX_FILTERS))):
            h.addWidget(self.handles[i])
            box = QWidget()
            bl = QHBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(8)
            lbl = QLabel(tr(key))
            lbl.setObjectName("colHead")
            lbl.setProperty("plain", plain)
            combo = ChevronCombo()
            combo.setObjectName("colFilter")
            # largeur réduite (le texte choisi est court) ; la liste déroulante garde la largeur de ses entrées
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(7)
            combo.setCursor(Qt.PointingHandCursor)
            combo.setToolTip(tr("tip_col_filter"))
            prefix = "fst_" if col == "statics" else "fgx_"
            for k in filters:
                combo.addItem(tr(prefix + k), k)
            combo.currentIndexChanged.connect(lambda _i, c=col, cb=combo: self._changed(c, cb))
            combo.view().setMinimumWidth(combo.view().sizeHintForColumn(0) + 36)
            bl.addWidget(lbl)
            bl.addWidget(combo)
            bl.addStretch()
            if col == "statics":
                self.bulk_btns = {}
                seg = QFrame()
                seg.setObjectName("bulkSeg")
                seg.setAttribute(Qt.WA_Hover)
                sl = QHBoxLayout(seg)
                sl.setContentsMargins(1, 1, 1, 1)
                sl.setSpacing(0)
                for target, key, tip, name in ((OFF, "btn_all_off", "tip_all_off", "bulkOff"),
                                               (ON, "btn_all_on", "tip_all_on", "bulkOn")):
                    if target == ON:
                        div = QFrame()
                        div.setObjectName("bulkDiv")
                        sl.addWidget(div)
                    b = QPushButton("\u2009" + tr(key))     # espace fine : un peu d'air entre la pastille et le texte
                    b.setObjectName(name)
                    b.setIcon(dot_icon(C["off_text"] if target == OFF else C["accent"]))
                    b.setIconSize(QSize(6, 6))
                    b.setCursor(Qt.PointingHandCursor)
                    b.setToolTip(tr(tip))
                    b.clicked.connect(lambda _c=False, tg=target: self.bulk_requested.emit(tg))
                    sl.addWidget(b)
                    self.bulk_btns[target] = b
                bl.addWidget(seg)
            h.addWidget(box)
            self.boxes[col], self.combos[col] = box, combo

    def _changed(self, col, combo):
        key = combo.currentData() or "all"
        polish(combo, active=key != "all")
        self.filter_changed.emit(col, key)

    def set_filter(self, col: str, key: str):
        combo = self.combos[col]
        i = max(0, combo.findData(key))
        combo.blockSignals(True)
        combo.setCurrentIndex(i)
        combo.blockSignals(False)
        polish(combo, active=(combo.currentData() or "all") != "all")

    _compact = False

    def set_compact(self, on: bool):
        """Fenêtre étroite : « Tout OFF / Tout ON » deviennent « OFF / ON » (l'infobulle garde le sens complet)."""
        if on == self._compact or not hasattr(self, "bulk_btns"):
            return
        self._compact = on
        for target, key in ((OFF, "btn_all_off"), (ON, "btn_all_on")):
            self.bulk_btns[target].setText(("OFF" if target == OFF else "ON") if on else tr(key))

    def natural_widths(self) -> tuple[int, int]:
        """Largeur minimale lisible de chaque en-tête (titre + filtre)."""
        out = []
        for col in ("statics", "gsx"):
            lay = self.boxes[col].layout()
            ws = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget()]
            out.append(sum(w.sizeHint().width() for w in ws) + lay.spacing() * (len(ws) - 1))
        return out[0], out[1]

    def set_widths(self, ws: int, wg: int):
        self.boxes["statics"].setFixedWidth(ws)
        self.boxes["gsx"].setFixedWidth(wg)


class SceneRow(QFrame):
    toggle_requested = Signal(object, bool)
    gsx_requested = Signal(object, int, str)    # scène, index de variante, dossier GSX
    search_requested = Signal(object)
    restore_requested = Signal(object)

    def __init__(self, scene: Scene, gsx_folder_fn=None, choices: dict | None = None, on_auto_choice=None,
                 gsx_index_fn=None):
        super().__init__()
        self.setObjectName("row")
        self.gsx_folder_fn = gsx_folder_fn
        self.gsx_index_fn = gsx_index_fn
        self.manual: list = []
        self.choices = choices if choices is not None else {}
        self.on_auto_choice = on_auto_choice
        h = QHBoxLayout(self)
        h.setContentsMargins(*ROW_MARGINS)
        h.setSpacing(ROW_SPACING)

        # ── Colonne scène
        text = QVBoxLayout()
        text.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title = ElidedLabel()
        self.title.setObjectName("title")
        self.badge = QLabel(tr("badge_new"))
        self.badge.setObjectName("badgeNew")
        self.folder_btn = QPushButton()
        self.folder_btn.setObjectName("folderBtn")
        self.folder_btn.setIcon(folder_icon())
        self.folder_btn.setIconSize(QSize(16, 16))
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.setToolTip(tr("tip_open_folder"))
        self.folder_btn.clicked.connect(self.open_folder)
        top.addWidget(self.folder_btn)
        top.addWidget(self.title, 1)
        top.addWidget(self.badge)
        self.sub = ElidedLabel()
        self.sub.setObjectName("sub")
        text.addLayout(top)
        text.addWidget(self.sub)
        h.addLayout(text, 1)
        h.addWidget(vsep())

        # ── Colonne statics
        col, cv = column(COL_STATICS_W)
        self.st_col = col
        line = QHBoxLayout()
        line.setSpacing(10)
        self.state_lbl = QLabel()
        self.state_lbl.setObjectName("state")
        self.switch = Switch()
        sp = self.switch.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.switch.setSizePolicy(sp)
        self.switch.clicked.connect(lambda c: self.toggle_requested.emit(self.scene, c))
        # Cas ambigu : pas de bascule automatique, on propose de le faire à la main
        self.st_folder_btn = QPushButton()
        self.st_folder_btn.setObjectName("folderBtn")
        self.st_folder_btn.setIcon(folder_icon())
        self.st_folder_btn.setIconSize(QSize(16, 16))
        self.st_folder_btn.setCursor(Qt.PointingHandCursor)
        self.st_folder_btn.clicked.connect(self.open_statics_folder)
        line.addWidget(self.state_lbl, 1)
        line.addWidget(self.st_folder_btn)
        line.addWidget(self.switch)
        self.st_note = ElidedLabel()
        self.st_note.setObjectName("note")
        cv.addLayout(line)
        cv.addWidget(self.st_note)
        h.addWidget(col)
        h.addWidget(vsep())

        # ── Colonne GSX
        col, gv = column(COL_GSX_W)
        self.gsx_col = col
        self.gsx_state = "none"
        self.gsx_line = QHBoxLayout()
        self.gsx_line.setSpacing(6)
        self.gsx_none = QLabel(tr("gsx_none"))
        self.gsx_none.setObjectName("none")
        self.gsx_line.addWidget(self.gsx_none)
        self.gsx_btns: list = []
        self.gsx_line.addStretch()
        self.gsx_note = ElidedLabel()
        self.gsx_note.setObjectName("note")
        gv.addLayout(self.gsx_line)
        gv.addWidget(self.gsx_note)
        h.addWidget(col)

        self.refresh(scene)

    # ---------------------------------------------------------------
    def refresh(self, scene: Scene):
        self.scene = scene
        self.title.setFullText(scene.title)
        bits = [scene.folder]
        if scene.creator:
            bits.append(scene.creator)
        bits.append(display_source(scene.source))
        self.sub.setFullText("   ·   ".join(bits))
        self.badge.setVisible(scene.is_new)
        self.setToolTip(f"<b>{scene.title}</b><br><span style='color:{C['muted']}'>{scene.root}</span>"
                        f"<br><br><span style='color:{C['faint']}'>{tr('tip_dblclick')}</span>")
        self.refresh_statics()
        self.refresh_gsx()

    def refresh_statics(self):
        s = self.scene
        st = s.state
        self.state_lbl.setText(state_text(st))
        polish(self.state_lbl, state=st)
        self.switch.setEnabled(s.toggleable)
        self.switch.setVisible(st != NONE)
        self.switch.set_checked_silent(st == ON)

        is_warn = False
        if not s.groups:
            note = tr("note_none")
        else:
            notes = [g.note for g in s.groups if g.note]
            modes = {g.mode for g in s.groups}
            if notes:
                note, is_warn = tr(notes[0]), True
            elif len(modes) == 1:
                note = mode_note(s.groups, modes.pop())
                is_warn = "conflict" in {g.mode for g in s.groups}
            else:
                note = tr("note_mixed_methods")
            if len(s.groups) > 1:
                note = f"{tr('note_nfiles', n=len(s.groups))}  ·  {note}"
        self.st_note.setFullText(note)
        polish(self.st_note, warn="true" if is_warn else "false")

        tip = []
        for g in s.groups:
            rel = os.path.relpath(g.active, s.root)
            line = f"• {rel} — {tr(MODE_KEY[g.mode])}, <b>{tr(GROUP_STATE_KEY.get(g.state, 'grp_unknown'))}</b>"
            if g.note:
                line += f"<br>&nbsp;&nbsp;<span style='color:{C['warn']}'>{tr(g.note)}</span>"
            tip.append(line)
        tip_html = f"<b>{tr('statics_tip')}</b><br>" + ("<br>".join(tip) if tip else tr("no_file"))
        for w in (self.state_lbl, self.st_note, self.switch):
            w.setToolTip(tip_html)
        manual = self.manual_groups()
        self.st_folder_btn.setVisible(bool(manual))
        if manual:
            self.st_folder_btn.setToolTip(f"<b>{tr('tip_manual')}</b><br><span style='color:{C['muted']}'>"
                                          f"{os.path.relpath(manual[0].directory, s.root)}</span>")

    def _clear_gsx(self):
        for b in self.gsx_btns:
            self.gsx_line.removeWidget(b)
            b.deleteLater()
        self.gsx_btns = []

    def _add_gsx_widget(self, w):
        self.gsx_line.insertWidget(1 + len(self.gsx_btns), w)
        self.gsx_btns.append(w)

    def _note(self, text, is_warn=False, ok=False, tip=""):
        self.gsx_note.setFullText(text)
        polish(self.gsx_note, warn="true" if is_warn else "false", ok="true" if ok else "false")
        self.gsx_note.setToolTip(tip)

    def _search_button(self):
        s = self.scene
        q = gsx_search_query(s)
        b = QPushButton(tr("gsx_search_btn"))
        b.setObjectName("searchBtn")
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tr("gsx_search_tip", q=q))
        b.clicked.connect(lambda _=False: self.search_requested.emit(self.scene))
        self._add_gsx_widget(b)

    def natural_widths(self, notes: bool = True) -> tuple[int, int]:
        """Largeur de chaque colonne quand tout son texte tient sur une ligne (sans les notes si notes=False :
        la ligne principale — état, interrupteur, boutons — doit toujours rester entière)."""
        def line(lay) -> int:
            ws = [lay.itemAt(i).widget() for i in range(lay.count())]
            ws = [w for w in ws if w is not None and (not w.isHidden() or w is self.switch)]
            return sum(w.sizeHint().width() for w in ws) + lay.spacing() * max(0, len(ws) - 1)

        def note(lbl) -> int:
            return lbl.fontMetrics().horizontalAdvance(lbl._full) + 2 if lbl._full else 0
        st_line = self.st_col.layout().itemAt(0).layout()
        if not notes:
            return line(st_line) + 2, line(self.gsx_line) + 2
        return (max(line(st_line), note(self.st_note)) + 2,
                max(line(self.gsx_line), note(self.gsx_note)) + 2)

    def set_col_widths(self, ws: int, wg: int):
        self.st_col.setFixedWidth(ws)
        self.gsx_col.setFixedWidth(wg)

    def statics_state(self) -> str:
        """Clé du filtre Statics : on / off / check / none."""
        s = self.scene
        if not s.groups:
            return "none"
        return {ON: "on", OFF: "off"}.get(s.state, "check")

    def refresh_gsx(self):
        s = self.scene
        self._clear_gsx()
        self.gsx_state = "none"
        self.manual = gsx_manual_profiles(s, self.gsx_index_fn()) if self.gsx_index_fn else []
        if self.gsx_folder_fn is None:
            self.gsx_none.show()
            self._note("")
            return
        if not s.gsx_variants:
            # ── Aucun profil fourni avec la scène : profil installé à la main ? sinon recherche
            if self.manual:
                self.gsx_state = "manual"
                self.gsx_none.hide()
                lbl = QLabel(tr("gsx_manual_lbl"))
                lbl.setObjectName("gsxManual")
                tip = tr("gsx_manual_tip") + "<br>" + "<br>".join(f"• {n}" for n in self.manual)
                lbl.setToolTip(tip)
                self._add_gsx_widget(lbl)
                self._note(", ".join(self.manual), tip=tip)
            else:
                self.gsx_none.show()
                self._note("")              # colonne allégée : la recherche est dans l'infobulle du bouton
            if s.icao:
                self._search_button()
            return
        self.gsx_none.hide()
        self._refresh_scene_profile()
        if self.manual:      # un autre profil pour le même aéroport : GSX risque de choisir le mauvais
            self.gsx_state = "check"
            txt = tr("gsx_other_installed", files=", ".join(self.manual))
            self._note(txt, is_warn=True, tip=txt)

    def _refresh_scene_profile(self):
        s = self.scene
        folder = self.gsx_folder_fn()
        dest = Path(folder)
        missing_dir = "" if dest.is_dir() else f"<br><span style='color:{C['warn']}'>{tr('gsx_dir_missing')}</span>"
        dest_tip = f"<br><br><span style='color:{C['faint']}'>→ {folder}</span>{missing_dir}"

        def files_html(v):
            return "<br>".join(f"• {os.path.relpath(f, s.root)}" for f in v.files)

        def short_names(v):
            ini = [f.name for f in v.files if f.suffix.lower() == ".ini"]
            return ", ".join(ini) + ("  + .py" if any(f.suffix.lower() == ".py" for f in v.files) else "")

        # ── Une seule version
        if len(s.gsx_variants) == 1:
            v = s.gsx_variants[0]
            st = gsx_status(v.files, dest)
            self.gsx_state = {GSX_SAME: "installed", GSX_MISSING: "todo"}.get(st, "check")
            b = QPushButton(tr(GSX_TEXT_KEY[st]))
            b.setObjectName("gsx")
            b.setCursor(Qt.PointingHandCursor)
            polish(b, gsx=st)
            b.setToolTip(f"{tr(GSX_INFO_KEY[st])}<br><br>{files_html(v)}{dest_tip}")
            b.clicked.connect(lambda _=False: self.gsx_requested.emit(self.scene, 0, folder))
            self._add_gsx_widget(b)
            note = short_names(v)
            if st == GSX_DIFF:
                self._note(f"{tr('gsx_diff_note')}  ·  {note}", is_warn=True, tip=files_html(v))
            else:
                self._note(note, tip=files_html(v))
            return

        # ── Plusieurs versions : une seule active, choix mémorisé
        state, act, why, why_name = gsx_variant_state(s, dest, self.choices.get(s.key))
        self.gsx_state = {VAR_CHOSEN: "installed", VAR_NONE: "todo"}.get(state, "check")
        if state == VAR_CHOSEN and why == "auto" and self.on_auto_choice:
            self.on_auto_choice(s, variant_id(s, s.gsx_variants[act]))

        def vstate(i):
            if state == VAR_CHOSEN:
                return "active" if i == act else "inactive"
            return "check" if state == VAR_CHECK else "neutral"

        if len(s.gsx_variants) <= 3:
            for i, v in enumerate(s.gsx_variants):
                name = vlabel(v)
                lbl = name if len(name) <= 14 else name[:13] + "…"
                vs = vstate(i)
                b = QPushButton(("✓  " if vs == "active" else "") + lbl)
                b.setObjectName("varChip")
                b.setCursor(Qt.PointingHandCursor)
                polish(b, vstate=vs)
                hint = tr({"active": "var_tip_active", "inactive": "var_tip_inactive",
                           "check": "var_tip_check", "neutral": "var_tip_neutral"}[vs])
                b.setToolTip(f"<b>{name}</b> — {hint}<br><br>{files_html(v)}{dest_tip}")
                b.clicked.connect(lambda _=False, k=i: self.gsx_requested.emit(self.scene, k, folder))
                self._add_gsx_widget(b)
        else:
            cb = QComboBox()
            for i, v in enumerate(s.gsx_variants):
                mark = {"active": "✓ ", "inactive": "✕ ", "check": "? ", "neutral": ""}[vstate(i)]
                cb.addItem(mark + vlabel(v))
            cb.setCurrentIndex(act if act is not None else 0)
            cb.setFixedWidth(170)
            go = QPushButton(tr("btn_activate"))
            go.setObjectName("gsx")
            go.setCursor(Qt.PointingHandCursor)
            go.clicked.connect(lambda _=False, c=cb: self.gsx_requested.emit(self.scene, c.currentIndex(), folder))
            self._add_gsx_widget(cb)
            self._add_gsx_widget(go)

        tip = f"<b>{tr('var_versions_tip')}</b><br>" + "<br>".join(
            f"{'✓ ' if i == act else '• '}<b>{vlabel(v)}</b> — {os.path.relpath(v.folder, s.root)}"
            for i, v in enumerate(s.gsx_variants))
        n = len(s.gsx_variants)
        if state == VAR_CHOSEN:
            v = s.gsx_variants[act]
            self._note(f"{tr('var_note_active', name=vlabel(v))}  ·  {short_names(v)}", ok=True, tip=tip)
        elif state == VAR_CHECK:
            reason = tr(why, name=why_name)
            self._note(f"{tr('var_note_check')}  ·  {reason}", is_warn=True, tip=f"{reason}<br><br>{tip}")
        else:
            self._note(tr("var_note_none", n=n), tip=tip)

    def manual_groups(self) -> list:
        """Fichiers statics que SGM ne bascule pas lui-même (cas ambigus)."""
        return [g for g in self.scene.groups if not g.toggleable or g.note == "note_unknown_active"]

    def open_statics_folder(self):
        groups = self.manual_groups()
        d = groups[0].directory if groups else self.scene.root
        if not d.is_dir():
            warn(self, tr("folder_missing_msg", path=d))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def open_folder(self):
        root = self.scene.root
        if not root.is_dir():
            warn(self, tr("folder_missing_msg", path=root))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def mouseDoubleClickEvent(self, _e):
        self.open_folder()

    def can_restore(self) -> bool:
        if has_origin(self.scene.root):
            return True
        folder = self.gsx_folder_fn() if self.gsx_folder_fn else ""
        return bool(folder) and gsx_has_origin(Path(folder), [f.name for f in self.scene.gsx_files])

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.addAction(tr("tip_open_folder"), self.open_folder)
        menu.addSeparator()
        a = menu.addAction(tr("ctx_restore"), lambda: self.restore_requested.emit(self.scene))
        if not self.can_restore():
            a.setEnabled(False)
            a.setText(tr("ctx_restore_none"))
        menu.exec(e.globalPos())


class ScanWorker(QThread):
    progress = Signal(int, int, str)
    done = Signal(list)

    def __init__(self, sources):
        super().__init__()
        self.sources = sources

    def run(self):
        try:
            scenes = scan_all(self.sources, lambda i, n, name: self.progress.emit(i, n, name))
        except Exception:
            scenes = []
        self.done.emit(scenes)


class UpdateCheckWorker(QThread):
    done = Signal(object, str)                 # release_info ou None, message d'erreur

    def run(self):
        try:
            self.done.emit(fetch_latest_release(), "")
        except Exception as e:
            self.done.emit(None, str(e) or e.__class__.__name__)


class UpdateDownloadWorker(QThread):
    """Télécharge, vérifie (SHA-256) et prépare la nouvelle version, sans rien remplacer."""
    progress = Signal(int, int)
    done = Signal(object, str)                 # dict (script…) ou None, clé ou message d'erreur

    def __init__(self, info: dict):
        super().__init__()
        self.info = info

    def run(self):
        try:
            self.done.emit(prepare_update(self.info, lambda a, b: self.progress.emit(a, b)), "")
        except UpdateError as e:
            self.done.emit(None, str(e))
        except Exception as e:
            self.done.emit(None, str(e) or e.__class__.__name__)


class DownloadsWorker(QThread):
    done = Signal(list)

    def __init__(self, seen: set, folders=None, installed=None):
        super().__init__()
        self.seen, self.folders, self.installed = seen, folders, installed

    def run(self):
        try:
            found = find_download_archives(self.seen, self.folders, self.installed)
        except Exception:
            found = []
        self.done.emit(found)


class FoldersDialog(QDialog):
    def __init__(self, config: Config, sources: list[Source], parent=None):
        super().__init__(parent)
        self.config = config
        self.sources = sources
        self.changed = False
        self.gsx_changed = False
        self.downloads_changed = False
        self.setWindowTitle(f"{tr('dlg_folders')} — {config.sim}")
        self.setMinimumWidth(660)
        self.setSizeGripEnabled(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        t = QLabel(f"{tr('dlg_folders')} — {config.sim}")
        t.setObjectName("h1")
        t.setStyleSheet("font-size: 17px;")
        hint = QLabel(tr("dlg_hint", sim=config.sim))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(t)
        self._hint = hint
        self.list = QVBoxLayout()
        self.list.setSpacing(6)
        v.addLayout(self.list)
        btns = QHBoxLayout()
        close = QPushButton(tr("close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(close)
        v.addSpacing(6)
        v.addLayout(btns)
        self.rebuild()

    def _row(self, label, path, exists, tail_widgets):
        fr = QFrame()
        fr.setObjectName("folderRow")
        h = QHBoxLayout(fr)
        h.setContentsMargins(12, 8, 8, 8)
        src = QLabel(label.upper())
        src.setObjectName("src")
        p = ElidedLabel(path)
        p.setObjectName("path")
        p.setToolTip(path)
        h.addWidget(src)
        h.addWidget(p, 1)
        if not exists:
            m = QLabel(tr("not_found"))
            m.setObjectName("missing")
            h.addWidget(m)
        for w in tail_widgets:
            h.addWidget(w)
        self.list.addWidget(fr)

    def _ghost(self, text, fn):
        b = QPushButton(text)
        b.setObjectName("ghost")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(fn)
        return b

    def _chip(self, text):
        a = QLabel(text)
        a.setObjectName("chip")
        return a

    @staticmethod
    def _clear(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()                      # retiré tout de suite de l'affichage, détruit ensuite
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                FoldersDialog._clear(item.layout())

    def _section(self, title: str, hint: str = "", first: bool = False):
        if not first:
            self.list.addSpacing(14)
        h = QLabel(title)
        h.setObjectName("h2")
        self.list.addWidget(h)
        if hint:
            lbl = QLabel(hint)
            lbl.setObjectName("hint")
            lbl.setWordWrap(True)
            self.list.addWidget(lbl)

    def rebuild(self):
        self._clear(self.list)
        self._section(tr("sec_scenery"), self._hint.text(), first=True)
        autos = [s for s in self.sources if s.auto]
        if not autos:
            lbl = QLabel(tr("no_auto"))
            lbl.setObjectName("missing")
            self.list.addWidget(lbl)
        for s in autos:
            self._row(s.label, str(s.path), s.path.is_dir(), [self._chip(tr("auto"))])
        for f in self.config.manual_folders:
            self._row(tr("manual"), f, Path(f).is_dir(),
                      [self._ghost(tr("remove"), lambda _=False, x=f: self.remove_folder(x))])

        row = QHBoxLayout()
        row.addWidget(self._ghost(tr("add_folder"), self.add_folder))
        row.addStretch()
        self.list.addLayout(row)

        self._section(tr("gsx_dest"))
        folder = self.config.gsx_folder()
        tail = [] if self.config.gsx_override else [self._chip(tr("auto"))]
        tail += [self._ghost(tr("modify"), self.change_gsx), self._ghost(tr("default"), self.reset_gsx)]
        self._row("GSX", folder, Path(folder).is_dir(), tail)

        parts = re.split(r"\s*[—–]+\s*", tr("dl_folders"), maxsplit=1)     # « titre — explication »
        self._section(parts[0], parts[1] if len(parts) > 1 else "")
        custom = bool(self.config.download_folders)
        for f in self.config.download_dirs():
            f = str(f)
            tail = [] if custom else [self._chip(tr("auto"))]
            tail.append(self._ghost(tr("modify"), lambda _=False, x=f: self.change_download(x)))
            if custom and len(self.config.download_folders) > 1:
                tail.append(self._ghost(tr("remove"), lambda _=False, x=f: self.remove_download(x)))
            self._row(tr("dl_label"), f, Path(f).is_dir(), tail)
        row = QHBoxLayout()
        row.addWidget(self._ghost(tr("dl_add"), self.add_download))
        if custom:
            row.addWidget(self._ghost(tr("default"), self.reset_downloads))
        row.addStretch()
        self.list.addLayout(row)

    # ── Dossiers de téléchargement (archives de profils GSX)
    def _set_downloads(self, folders: list):
        out = []
        for f in folders:
            f = os.path.normpath(f)
            if norm_key(f) not in {norm_key(x) for x in out}:
                out.append(f)
        default = [os.path.normpath(str(downloads_dir()))]
        self.config.download_folders = [] if out == default else out[:10]
        self.config.save()
        self.downloads_changed = True
        self.rebuild()

    def change_download(self, old: str):
        d = QFileDialog.getExistingDirectory(self, tr("dl_choose"), old)
        if d:
            cur = [str(x) for x in self.config.download_dirs()]
            self._set_downloads([d if norm_key(x) == norm_key(old) else x for x in cur])

    def add_download(self):
        d = QFileDialog.getExistingDirectory(self, tr("dl_choose"), str(self.config.download_dirs()[0]))
        if d:
            self._set_downloads([str(x) for x in self.config.download_dirs()] + [d])

    def remove_download(self, f: str):
        self._set_downloads([str(x) for x in self.config.download_dirs() if norm_key(x) != norm_key(f)])

    def reset_downloads(self):
        self.config.download_folders = []
        self.config.save()
        self.downloads_changed = True
        self.rebuild()

    def change_gsx(self):
        d = QFileDialog.getExistingDirectory(self, tr("choose_gsx"), self.config.gsx_folder())
        if d:
            self.config.gsx_override = os.path.normpath(d)
            self.config.save()
            self.gsx_changed = True
            self.rebuild()

    def reset_gsx(self):
        self.config.gsx_override = ""
        self.config.save()
        self.gsx_changed = True
        self.rebuild()

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, tr("choose_folder"))
        if not d:
            return
        d = os.path.normpath(d)
        known = {norm_key(s.path) for s in self.sources if s.auto} | {norm_key(f) for f in self.config.manual_folders}
        if norm_key(d) in known:
            return
        self.config.manual_folders.append(d)
        self.config.save()
        self.changed = True
        self.rebuild()

    def remove_folder(self, f):
        self.config.manual_folders = [x for x in self.config.manual_folders if x != f]
        self.config.save()
        self.changed = True
        self.rebuild()


class DocDialog(QDialog):
    """Fenêtre de lecture pour le guide et l'avertissement."""

    def __init__(self, title: str, html: str, note: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — {title}")
        self.resize(720, 640)
        self.setSizeGripEnabled(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)
        if note:
            n = QLabel(note)
            n.setObjectName("hint")
            v.addWidget(n)
        doc = QTextBrowser()
        doc.setObjectName("doc")
        doc.setOpenExternalLinks(True)
        doc.document().setDefaultStyleSheet(DOC_CSS)
        doc.setHtml(html)
        v.addWidget(doc, 1)
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton(tr("close"))
        close.setObjectName("primary")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        v.addLayout(row)


class ReportDialog(QDialog):
    """Fenêtre « Signaler un problème / Proposer une idée » : texte, pièces jointes, aperçu exact.
    Rien n'est envoyé par SGM : il prépare un .zip et ouvre la page GitHub préremplie."""

    def __init__(self, kind: str, sim: str, scene_names=(), parent=None):
        super().__init__(parent)
        self.sim = sim
        self.kind = "bug" if kind == "bug" else "idea"
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        top = QHBoxLayout()
        self.h = QLabel()
        self.h.setObjectName("h1")
        self.h.setStyleSheet("font-size: 17px;")
        top.addWidget(self.h)
        top.addStretch()
        chips = QFrame()
        chips.setObjectName("chips")
        ch = QHBoxLayout(chips)
        ch.setContentsMargins(3, 3, 3, 3)
        ch.setSpacing(2)
        self.kind_btns = {}
        group = QButtonGroup(self)
        for k, key in (("bug", "rd_kind_bug"), ("idea", "rd_kind_idea")):
            b = QPushButton(tr(key))
            b.setObjectName("chipBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, k=k: self.set_kind(k))
            group.addButton(b)
            ch.addWidget(b)
            self.kind_btns[k] = b
        top.addWidget(chips)
        v.addLayout(top)
        hint = QLabel(tr("rd_hint"))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.summary = QLineEdit()
        self.summary.setPlaceholderText(tr("rd_summary_ph"))
        self.summary.setMaxLength(120)
        self.inputs, self.rows = {}, {}
        specs = [("summary", "rd_summary", self.summary)]
        for key, label, multi in (("what", "rd_what", 3), ("expected", "rd_expected", 0), ("steps", "rd_steps", 3),
                                  ("scene", "rd_scene", 0), ("message", "rd_message", 0),
                                  ("idea", "rd_idea", 4), ("why", "rd_why", 2)):
            if multi:
                w = QPlainTextEdit()
                w.setTabChangesFocus(True)
                w.setFixedHeight(22 + 18 * multi)
                w.textChanged.connect(self.update_preview)
            else:
                w = QLineEdit()
                w.textChanged.connect(self.update_preview)
            self.inputs[key] = w
            specs.append((key, label, w))
        self.summary.textChanged.connect(self.update_preview)
        scene = self.inputs["scene"]
        scene.setPlaceholderText(tr("rd_scene_ph"))
        if scene_names:
            comp = QCompleter(sorted(set(scene_names)), scene)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            scene.setCompleter(comp)
        for r, (key, label, w) in enumerate(specs):
            lab = QLabel(tr(label))
            lab.setObjectName("fieldLabel")
            lab.setWordWrap(True)
            lab.setContentsMargins(0, 7, 0, 0)          # aligné sur le texte des champs
            grid.addWidget(lab, r, 0, Qt.AlignTop)
            grid.addWidget(w, r, 1)
            self.rows[key] = (lab, w)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid)

        self.cb_report = CheckBox(tr("rd_attach_report"))
        self.cb_log = CheckBox(tr("rd_attach_log"))
        for cb in (self.cb_report, self.cb_log):
            cb.toggled.connect(self.update_preview)
            v.addWidget(cb)
        priv = QLabel(tr("rd_privacy"))
        priv.setObjectName("hint")
        priv.setWordWrap(True)
        v.addWidget(priv)

        self.prev_btn = QPushButton(tr("rd_preview_show"))
        self.prev_btn.setObjectName("linkBtn")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self.toggle_preview)
        v.addWidget(self.prev_btn, 0, Qt.AlignLeft)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName("preview")
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(170)
        self.preview.hide()
        v.addWidget(self.preview)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(tr("rd_cancel"))
        cancel.clicked.connect(self.reject)
        self.send = QPushButton(tr("rd_send"))
        self.send.setObjectName("primary")
        self.send.setCursor(Qt.PointingHandCursor)
        self.send.clicked.connect(self.accept_if_filled)
        btns.addWidget(cancel)
        btns.addWidget(self.send)
        v.addSpacing(4)
        v.addLayout(btns)
        self.set_kind(self.kind)

    # ── état
    def set_kind(self, kind: str):
        self.kind = kind
        self.kind_btns[kind].setChecked(True)
        self.h.setText(tr("rd_title_bug" if kind == "bug" else "rd_title_idea"))
        own = {k for k, _ in ISSUE_FIELDS[kind]}
        for key, (lab, w) in self.rows.items():
            show = key == "summary" or key in own
            lab.setVisible(show)
            w.setVisible(show)
        self.cb_report.setChecked(kind == "bug")
        self.cb_log.setChecked(kind == "bug")
        self.update_preview()
        self.adjustSize()

    def fields(self) -> dict:
        out = {}
        for key, _ in ISSUE_FIELDS[self.kind]:
            w = self.inputs[key]
            out[key] = w.toPlainText() if isinstance(w, QPlainTextEdit) else w.text()
        return out

    def main_text(self) -> str:
        f = self.fields()
        return (f.get("what") or f.get("idea") or "").strip()

    def attachment_name(self) -> str:
        if not (self.cb_report.isChecked() or self.cb_log.isChecked()):
            return ""
        return f"sgm-{self.kind}-…zip"

    def update_preview(self, *_):
        if not hasattr(self, "preview") or self.preview.isHidden():
            return
        title, body = issue_text(self.kind, self.sim, get_lang(), self.fields(), self.summary.text(),
                                 [self.attachment_name()] if self.attachment_name() else ())
        parts = [title, "", body]
        if self.attachment_name():
            inside = ["message.md"] + (["statics-report.json"] if self.cb_report.isChecked() else []) + \
                     (["sgm.log"] if self.cb_log.isChecked() else [])
            parts += ["", "════════", f"{tr('rd_files')} {self.attachment_name()}  ({', '.join(inside)})"]
        self.preview.setPlainText("\n".join(parts))

    def toggle_preview(self):
        show = self.preview.isHidden()
        self.preview.setVisible(show)
        self.prev_btn.setText(tr("rd_preview_hide" if show else "rd_preview_show"))
        self.update_preview()
        self.adjustSize()

    def accept_if_filled(self):
        if not self.main_text():
            warn(self, tr("rd_empty"))
            self.inputs["what" if self.kind == "bug" else "idea"].setFocus()
            return
        self.accept()


class MainWindow(QMainWindow):
    """Fenêtre principale. `state` permet de la recréer (changement de langue) sans relancer l'analyse."""

    def __init__(self, state: dict | None = None):
        super().__init__()
        self.config = Config()
        set_lang(self.config.lang)
        self.sources: list[Source] = []
        self.scenes: dict = {}
        self.rows: dict = {}
        self.session_new: set = set()
        self.worker = None
        self.busy = False
        sim = self.config.sim

        self.setWindowTitle(f"{APP_NAME} — {APP_FULL} — {sim}")
        self.resize(1080, 720)
        self.setMinimumSize(800, 500)
        self._build_menu()

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(26, 18, 26, 14)
        root.setSpacing(14)

        # En-tête
        head = QHBoxLayout()
        tv = QVBoxLayout()
        tv.setSpacing(3)
        tline = QHBoxLayout()
        tline.setSpacing(10)
        h1 = QLabel(APP_NAME)
        h1.setObjectName("h1")
        full = QLabel(APP_FULL)
        full.setObjectName("fullname")
        pill = QLabel(sim)
        pill.setObjectName("simPill")
        pill.setToolTip(tr("sim_tip"))
        tline.addWidget(h1)
        tline.addWidget(full, 0, Qt.AlignBottom)
        tline.addSpacing(4)
        tline.addWidget(pill, 0, Qt.AlignVCenter)
        tline.addStretch()
        st = QLabel(tr("subtitle"))
        st.setObjectName("subtitle")
        tv.addLayout(tline)
        tv.addWidget(st)
        head.addLayout(tv, 1)
        self.stats = QLabel()
        self.stats.setObjectName("stats")
        self.stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(self.stats)
        root.addLayout(head)

        # Recherche + filtres
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search_ph"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        self.search.setMinimumWidth(220)
        bar.addWidget(self.search, 1)
        chips = QFrame()
        chips.setObjectName("chips")
        ch = QHBoxLayout(chips)
        ch.setContentsMargins(3, 3, 3, 3)
        ch.setSpacing(2)
        self.new_chip = QPushButton(tr("f_new"))
        self.new_chip.setObjectName("chipBtn")
        self.new_chip.setCheckable(True)
        self.new_chip.setCursor(Qt.PointingHandCursor)
        self.new_chip.setToolTip(tr("tip_new_filter"))
        self.new_chip.toggled.connect(lambda _c: self.apply_filter())
        ch.addWidget(self.new_chip)
        bar.addWidget(chips)
        self.reset_btn = QPushButton(tr("btn_reset_filters"))
        self.reset_btn.setObjectName("linkBtn")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_filters)
        self.reset_btn.hide()
        bar.addWidget(self.reset_btn)
        self.st_filter, self.gsx_filter = "all", "all"
        root.addLayout(bar)

        # Actions
        bar2 = QHBoxLayout()
        bar2.setSpacing(8)
        self.btn_folders = QPushButton(tr("btn_folders"))
        self.btn_folders.clicked.connect(self.open_folders)
        self.btn_scan = QPushButton(tr("btn_scan"))
        self.btn_scan.clicked.connect(self.manual_scan)
        self.btn_scan.setToolTip(tr("tip_scan"))
        self.btn_install = QPushButton(tr("btn_install"))
        self.btn_install.setToolTip(tr("arch_drop_tip"))
        self.btn_install.clicked.connect(self.choose_archives)
        # Annuler : séparé des boutons d'action (il défait, il ne crée rien)
        # Profils de statics : enregistrer / appliquer un jeu d'états ON/OFF
        self.btn_profiles = QPushButton(tr("btn_profiles"))          # flèche de menu dessinée par Qt
        self.btn_profiles.setToolTip(tr("tip_profiles"))
        self.profiles_menu = QMenu(self)
        self.profiles_menu.aboutToShow.connect(self.build_profiles_menu)
        self.btn_profiles.setMenu(self.profiles_menu)
        self.btn_undo = QPushButton("↶  " + tr("btn_undo"))
        self.btn_undo.setObjectName("ghost")
        self.btn_undo.clicked.connect(self.undo_last_action)
        for b in (self.btn_folders, self.btn_scan, self.btn_install, self.btn_undo, self.btn_profiles):
            b.setCursor(Qt.PointingHandCursor)
        self.scope_lbl = QLabel()
        self.scope_lbl.setObjectName("hint")
        bar2.addWidget(self.btn_folders)
        bar2.addWidget(self.btn_scan)
        bar2.addWidget(self.btn_install)
        bar2.addWidget(self.btn_profiles)
        bar2.addSpacing(6)
        bar2.addWidget(self.btn_undo)
        bar2.addStretch()
        bar2.addWidget(self.scope_lbl)
        root.addLayout(bar2)

        # Bandeau
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        bh = QHBoxLayout(self.banner)
        bh.setContentsMargins(14, 9, 8, 9)
        self.banner_lbl = QLabel()
        self.banner_lbl.setWordWrap(True)
        bx = QPushButton("✕")
        bx.setObjectName("ghost")
        bx.setCursor(Qt.PointingHandCursor)
        bx.clicked.connect(self.banner.hide)
        bh.addWidget(self.banner_lbl, 1)
        bh.addWidget(bx)
        self.banner.hide()
        root.addWidget(self.banner)

        self.dl_banner = QFrame()
        self.dl_banner.setObjectName("banner")
        dh = QHBoxLayout(self.dl_banner)
        dh.setContentsMargins(14, 7, 8, 7)
        dh.setSpacing(8)
        self.dl_lbl = ElidedLabel()
        dl_inst = QPushButton(tr("dl_install"))
        dl_inst.setObjectName("primary")
        dl_inst.setCursor(Qt.PointingHandCursor)
        dl_inst.clicked.connect(self.install_found_downloads)
        dl_ign = QPushButton(tr("dl_ignore"))
        dl_ign.setObjectName("ghost")
        dl_ign.setCursor(Qt.PointingHandCursor)
        dl_ign.clicked.connect(self.ignore_found_downloads)
        dh.addWidget(self.dl_lbl, 1)
        dh.addWidget(dl_inst)
        dh.addWidget(dl_ign)
        self.dl_banner.hide()
        root.addWidget(self.dl_banner)

        # Question de mise à jour (premier lancement) : dans un bandeau, sans fenêtre qui bloque le démarrage
        self.upd_banner = QFrame()
        self.upd_banner.setObjectName("banner")
        uh = QHBoxLayout(self.upd_banner)
        uh.setContentsMargins(14, 9, 8, 9)
        uh.setSpacing(8)
        self.upd_lbl = QLabel()
        self.upd_lbl.setWordWrap(True)
        self.upd_lbl.setTextFormat(Qt.RichText)
        up_yes = QPushButton(tr("yes"))
        up_yes.setObjectName("primary")
        up_no = QPushButton(tr("no"))
        up_no.setObjectName("ghost")
        for b_, v in ((up_yes, True), (up_no, False)):
            b_.setCursor(Qt.PointingHandCursor)
            b_.clicked.connect(lambda _=False, v=v: self.answer_update_question(v))
        uh.addWidget(self.upd_lbl, 1)
        uh.addWidget(up_yes, 0, Qt.AlignVCenter)
        uh.addWidget(up_no, 0, Qt.AlignVCenter)
        self.upd_banner.hide()
        root.addWidget(self.upd_banner)

        # Version installée, premier lancement : reprendre les données d'une version portable
        self.imp_banner = QFrame()
        self.imp_banner.setObjectName("banner")
        ih = QHBoxLayout(self.imp_banner)
        ih.setContentsMargins(14, 9, 8, 9)
        ih.setSpacing(8)
        imp_lbl = QLabel(tr("import_ask"))
        imp_lbl.setWordWrap(True)
        imp_go = QPushButton(tr("import_btn"))
        imp_go.setObjectName("primary")
        imp_go.clicked.connect(self.import_from_portable)
        imp_no = QPushButton(tr("no"))
        imp_no.setObjectName("ghost")
        imp_no.clicked.connect(self.imp_banner.hide)
        for b_ in (imp_go, imp_no):
            b_.setCursor(Qt.PointingHandCursor)
        ih.addWidget(imp_lbl, 1)
        ih.addWidget(imp_go, 0, Qt.AlignVCenter)
        ih.addWidget(imp_no, 0, Qt.AlignVCenter)
        self.imp_banner.setVisible(bool(FRESH_DATA and is_installed() and not hosted() and not state))
        root.addWidget(self.imp_banner)
        self._dl_found: list = []
        self._dl_checked = False
        self.setAcceptDrops(True)

        # Liste
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_w = QWidget()
        self.list_w.setObjectName("list")
        self.list_l = QVBoxLayout(self.list_w)
        self.list_l.setContentsMargins(0, 0, 6, 0)
        self.list_l.setSpacing(8)
        self.col_header = ColumnHeader()
        self.col_header.filter_changed.connect(self._column_filter_changed)
        self.col_header.bulk_requested.connect(self.set_all)
        # Tout OFF / Tout ON : dans l'en-tête de la colonne Statics, cas simples uniquement
        self.btn_all_off, self.btn_all_on = self.col_header.bulk_btns[OFF], self.col_header.bulk_btns[ON]
        self.col_fs, self.col_fg = self.config.col_fs, self.config.col_fg
        for i, hd in enumerate(self.col_header.handles):
            hd.dragged.connect(lambda dx, i=i: self._drag_column(i, dx))
            hd.released.connect(self._save_columns)
            hd.reset.connect(self._auto_columns)
        self._col_auto = self.config.col_auto
        self._natural = None                  # largeurs du texte (mode automatique), recalculées si besoin
        # en-tête FIXE au-dessus de la zone qui défile (il ne disparaît plus en descendant dans la liste)
        self.header_box = QWidget()
        hb = QHBoxLayout(self.header_box)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(0)
        hb.addWidget(self.col_header)
        hb.addStretch()
        root.addWidget(self.header_box)
        self.empty = QLabel(tr("empty_scanning"))
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.list_l.addWidget(self.empty)
        self.list_l.addStretch()
        self.scroll.setWidget(self.list_w)
        self.scroll.viewport().installEventFilter(self)
        root.addWidget(self.scroll, 1)

        sep = QFrame()
        sep.setObjectName("sep")
        root.addWidget(sep)
        self.status = QLabel()
        self.status.setObjectName("status")
        root.addWidget(self.status)

        if state:   # recréation après changement de langue : on reprend la liste telle quelle
            self.sources = state["sources"]
            self.session_new = state["session_new"]
            self.scenes = state["scenes"]
            self.st_filter = state.get("st_filter", "all")
            self.gsx_filter = state.get("gsx_filter", "all")
            self.col_header.set_filter("statics", self.st_filter)
            self.col_header.set_filter("gsx", self.gsx_filter)
            self.new_chip.setChecked(state.get("new_only", False))
            self.search.setText(state.get("search", ""))
            self._scan_time = state.get("scan_time", "")
            self.rebuild_rows()
            self.status.setText(state.get("status_fn", lambda: "")())
        else:
            QTimer.singleShot(50, self.start_scan)

    # ── Barre de menu
    def _build_menu(self):
        mb = self.menuBar()
        m_set = mb.addMenu(tr("m_settings"))

        m_lang = m_set.addMenu(tr("m_language"))
        grp = QActionGroup(self)
        for code, name in LANGS:
            a = QAction(f"{name}   ({code.upper()})", self, checkable=True)
            a.setChecked(code == get_lang())
            a.triggered.connect(lambda _=False, c=code: self.change_language(c))
            grp.addAction(a)
            m_lang.addAction(a)

        m_sim = m_set.addMenu(tr("m_sim"))
        sgrp = QActionGroup(self)
        for sim in SIMS:
            a = QAction(sim, self, checkable=True)
            a.setChecked(sim == self.config.sim)
            a.triggered.connect(lambda _=False, s=sim: self.change_sim(s))
            sgrp.addAction(a)
            m_sim.addAction(a)
        m_sim.addSeparator()
        note = QAction(tr("sim_note"), self)
        note.setEnabled(False)
        m_sim.addAction(note)

        m_set.addSeparator()
        a = QAction(tr("m_folders"), self)
        a.triggered.connect(self.open_folders)
        m_set.addAction(a)
        m_set.addSeparator()
        a = QAction(tr("m_check_dl"), self, checkable=True)
        a.setChecked(self.config.check_downloads)
        a.toggled.connect(self.set_check_downloads)
        m_set.addAction(a)
        m_clean = m_set.addMenu(tr("m_arch_cleanup"))
        cgrp = QActionGroup(self)
        for mode in ARCHIVE_CLEANUP:
            a = QAction(tr("m_arch_cleanup_" + mode), self, checkable=True)
            a.setChecked(self.config.archive_cleanup == mode)
            a.triggered.connect(lambda _=False, md=mode: self.set_archive_cleanup(md))
            cgrp.addAction(a)
            m_clean.addAction(a)
        if is_installed() and not hosted():
            m_set.addSeparator()
            a = QAction(tr("m_import"), self)
            a.setData("m_import")
            a.triggered.connect(self.import_from_portable)
            m_set.addAction(a)
        if not hosted():                       # S10 : embarqué, pas de mise à jour propre à SGM
            m_set.addSeparator()
            a = QAction(tr("m_update_auto"), self, checkable=True)
            a.setChecked(self.config.update_check is True)
            a.toggled.connect(self.set_update_check)
            m_set.addAction(a)
            self.update_auto_act = a

        def keep(key: str) -> bool:              # accroche S12 : menus Outils et Aide allégés dans l'hôte
            return HOST_HELP_ITEMS is None or key in HOST_HELP_ITEMS

        def act(menu, key, fn, shortcut=None, text=None):
            a = QAction(text or tr(key), self)
            a.setData(key)
            if shortcut:
                a.setShortcut(shortcut)
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        # Outils : ce que SGM FAIT (le menu Aide ne garde que l'aide)
        m_tools = mb.addMenu(tr("m_tools"))
        act(m_tools, "m_scan", self.manual_scan, "F5", tr("btn_scan"))
        act(m_tools, "m_install_arch", self.choose_archives)
        pm = m_tools.addMenu(tr("btn_profiles"))
        pm.aboutToShow.connect(lambda: self.build_profiles_menu(pm))
        self.undo_act = act(m_tools, "m_undo", self.undo_last_action, "Ctrl+Z", tr("btn_undo"))
        self.addAction(self.undo_act)                  # raccourci actif même sans barre de menus (hôte)
        self.addAction(m_tools.actions()[0])           # F5
        m_tools.addSeparator()
        for key, fn in (("m_restore_all", self.restore_all), ("m_stats_report", self.make_statics_report)):
            if keep(key):
                act(m_tools, key, fn)
        m_tools.addSeparator()
        for key, fn in (("m_backups", self.open_backups), ("m_open_log", self.open_logs)):
            if keep(key):
                act(m_tools, key, fn)
        self.tools_menu = m_tools

        m_help = mb.addMenu(tr("m_help"))
        if keep("m_guide"):
            act(m_help, "m_guide", self.show_guide, "F1")
        m_help.addSeparator()
        for key, kind in (("m_report_bug", "bug"), ("m_suggest", "idea")):
            if keep(key):
                act(m_help, key, lambda _=False, k=kind: self.open_report(k))
        m_help.addSeparator()
        if keep("m_check_updates") and not hosted():
            act(m_help, "m_check_updates", lambda: self.check_updates(manual=True))
        m_help.addSeparator()
        for key, fn in (("m_disclaimer", self.show_disclaimer), ("m_licenses", self.show_licenses),
                        ("m_donate", self.donate), ("m_about", self.about)):
            if keep(key):
                act(m_help, key, fn)
        self.help_menu = m_help

        # Raccourcis sans menu : Ctrl+F (recherche), Échap (vider la recherche / les filtres)
        a = QAction(self)
        a.setShortcut(QKeySequence.Find)
        a.triggered.connect(self.focus_search)
        self.addAction(a)
        a = QAction(self)
        a.setShortcut(Qt.Key_Escape)
        a.setShortcutContext(Qt.WindowShortcut)
        a.triggered.connect(self.escape_pressed)
        self.addAction(a)

        # Coin droit : version · auteur, don, langue
        corner = QWidget()
        hl = QHBoxLayout(corner)
        hl.setContentsMargins(0, 0, 4, 0)
        hl.setSpacing(4)
        credit = QLabel(f"v{APP_VERSION}  ·  {APP_AUTHOR}")
        credit.setObjectName("credit")
        heart = QToolButton()
        heart.setObjectName("cornerBtn")
        heart.setIcon(heart_icon())
        heart.setIconSize(QSize(14, 14))
        heart.setToolTip(tr("donate_tip"))
        heart.setCursor(Qt.PointingHandCursor)
        heart.clicked.connect(self.donate)
        lang = QToolButton()
        lang.setObjectName("cornerBtn")
        lang.setText(get_lang().upper())
        lang.setToolTip(tr("lang_tip"))
        lang.setCursor(Qt.PointingHandCursor)
        lang.setPopupMode(QToolButton.InstantPopup)
        lm = QMenu(lang)
        for code, name in LANGS:
            a = lm.addAction(f"{code.upper()}   {name}")
            a.setCheckable(True)
            a.setChecked(code == get_lang())
            a.triggered.connect(lambda _=False, c=code: self.change_language(c))
        lang.setMenu(lm)
        hl.addWidget(credit)
        hl.addWidget(heart)
        hl.addWidget(lang)
        self._corner = corner          # garder une référence : PySide ne prend pas la propriété
        mb.setCornerWidget(corner, Qt.TopRightCorner)

    def change_language(self, code: str):
        if code == get_lang():
            return
        self.config.lang = code
        self.config.save()
        set_lang(code)
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if code in RTL_LANGS else Qt.LeftToRight)
        state = None if self.busy else {
            "sources": self.sources, "session_new": self.session_new, "scenes": self.scenes,
            "st_filter": self.st_filter, "gsx_filter": self.gsx_filter, "new_only": self.new_chip.isChecked(),
            "search": self.search.text(),
            "status_fn": self._status_done_text,
            "scan_time": self._scan_time,
        }
        self._replace_window(state)

    def change_sim(self, sim: str):
        if sim == self.config.sim or self.busy:
            return
        self.config.sim = sim
        self.config.save()
        self._replace_window(None)

    def _replace_window(self, state):
        if HOST_REPLACE:                        # accroche S1 : l'hôte recrée lui-même l'onglet
            HOST_REPLACE(state)
            return
        w = MainWindow(state)
        w.setGeometry(self.geometry())
        if self.isMaximized():
            w.showMaximized()
        else:
            w.show()
        dark_title_bar(w)
        QApplication.instance().main_window = w
        self.close()

    def _doc_note(self) -> str:
        return "" if get_lang() in ("en", "fr") else tr("help_lang_note")

    def show_guide(self):
        DocDialog(tr("m_guide").rstrip("…"), tr("help_html"), self._doc_note(), self).exec()

    def show_disclaimer(self):
        DocDialog(tr("m_disclaimer").rstrip("…"), tr("disclaimer_html"), self._doc_note(), self).exec()

    def show_licenses(self):
        import html as _html
        try:
            import PySide6
            from PySide6.QtCore import qVersion
            pyside_v, qt_v = PySide6.__version__, qVersion()
        except Exception:
            pyside_v = qt_v = "?"
        rows = [(f"{APP_NAME} — {APP_FULL}", f"v{APP_VERSION}"), ("Qt for Python (PySide6)", pyside_v),
                ("Qt", qt_v), ("Python", sys.version.split()[0])]
        doc = tr("licenses_html")
        doc += f"<h3>{tr('versions_title')}</h3><ul>" + "".join(f"<li>{a} — <b>{b}</b></li>" for a, b in rows) + "</ul>"
        folder = license_dir()
        found = False
        for name in ("LICENSE-SGM.txt", "THIRD-PARTY-NOTICES.txt", "LGPL-3.0-only.txt",
                     "GPL-3.0-only.txt", "Python-PSF-LICENSE.txt"):
            f = folder / name
            if f.is_file():
                found = True
                text = f.read_text(encoding="utf-8", errors="replace")
                doc += (f"<h3>{name}</h3><pre style='white-space:pre-wrap; font-size:11px; "
                        f"color:{C['doc_text']}'>{_html.escape(text)}</pre>")
        if not found:
            doc += f"<p><i>{tr('licenses_missing')}</i></p>"
        DocDialog(tr("m_licenses").rstrip("…"), doc, "", self).exec()

    # ── Restauration de l'état d'origine
    def on_restore(self, scene: Scene):
        if not self.ensure_sim_closed():
            return
        if not ask(self, tr("restore_confirm", name=scene.title), default_yes=False):
            return
        msgs = []
        with undoable(f"↺ {scene.title}"):
            if has_origin(scene.root):
                try:
                    restore_scene_statics(scene.root)
                except RestoreError as e:
                    msgs.append(str(e))
            folder = self.config.gsx_folder()
            kept = []
            if folder and gsx_restore(Path(folder), [f.name for f in scene.gsx_files], kept):
                self.config.gsx_choices.pop(scene.key, None)
                self.config.save()
            if kept:
                msgs.append(tr("gsx_restore_kept", files="\n".join(f"• {n}" for n in kept)))
        self.update_undo_btn()
        self.refresh_gsx_index()
        self.refresh_scene(scene)
        self.update_stats()
        self.status.setText(tr("restore_done", name=scene.title))
        if msgs:
            warn(self, "\n\n".join(msgs))

    def restore_all(self):
        roots = origin_roots()
        dests = gsx_journal_dests()
        if not roots and not dests:
            warn(self, tr("restore_nothing"))
            return
        if not self.ensure_sim_closed():
            return
        if not ask(self, tr("restore_all_confirm", n=len(roots)), default_yes=False):
            return
        errors = []
        with undoable("↺ " + tr("m_restore_all").rstrip("…. ")):
            for root in roots:
                try:
                    restore_scene_statics(root)
                except RestoreError as e:
                    errors.append(f"• {root.name} : {e}")
            kept = []
            for d in dests:
                gsx_restore(d, None, kept)
            if kept:
                errors.append(tr("gsx_restore_kept", files="\n".join(f"• {n}" for n in kept[:15])))
        self.config.gsx_choices.clear()
        self.config.save()
        self.status.setText(tr("restore_all_done", n=len(roots)))
        if errors:
            warn(self, tr("all_errors") + "\n\n" + "\n".join(errors[:15]) + ("\n…" if len(errors) > 15 else ""))
        self.start_scan()

    def make_statics_report(self):
        """Rapport en lecture seule : aucun fichier de scène n'est modifié."""
        res = self._create_report()
        if res:
            path, report = res
            QMessageBox.information(self, APP_NAME, tr("report_done", n=report["summary"]["scenes_with_candidates"],
                                                       name=path.name))
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _create_report(self):
        if self.busy:
            return None
        self.set_busy(True)
        try:
            def prog(i, n, name):
                self.status.setText(tr("report_progress", i=i, n=n, name=name))
                QApplication.processEvents()
            report = build_statics_report(find_sources(self.config), self.config.sim, prog)
            path = write_statics_report(report)
        except Exception as e:
            self.set_busy(False)
            warn(self, tr("report_fail", err=e))
            return None
        self.set_busy(False)
        self.status.setText(tr("report_saved", name=path.name))
        return path, report

    def open_backups(self):
        d = data_dir() / "backups"
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def open_logs(self):
        log_dir().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir())))

    def open_report(self, kind: str):
        names = [s.title for s in self.scenes.values()] + [s.icao for s in self.scenes.values() if s.icao]
        dlg = ReportDialog(kind, self.config.sim, names, self)
        ok = dlg.exec() == QDialog.Accepted
        kind, fields, summary = dlg.kind, dlg.fields(), dlg.summary.text()
        want_report, want_log = dlg.cb_report.isChecked(), dlg.cb_log.isChecked()
        dlg.deleteLater()
        if not ok:
            return
        report = None
        if want_report:
            res = self._create_report()
            if res:
                report = res[1]
        package = None
        if report is not None or want_log:
            try:
                package = build_report_package(kind, self.config.sim, get_lang(), fields, summary,
                                               report, want_log)
            except OSError as e:
                warn(self, tr("report_fail", err=e))
        url = report_url(kind, self.config.sim, get_lang(), [package.name] if package else (), fields, summary)
        LOG.info("Signalement préparé (%s), pièce jointe : %s", kind, package.name if package else "aucune")
        if package:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(package.parent)))
            QMessageBox.information(self, APP_NAME, tr("rd_done", name=package.name))
        else:
            QMessageBox.information(self, APP_NAME, tr("rd_done_nofile"))
        QDesktopServices.openUrl(QUrl(url))

    def donate(self):
        if DONATE_URL:
            QDesktopServices.openUrl(QUrl(DONATE_URL))
        else:
            QMessageBox.information(self, APP_NAME, tr("donate_soon"))

    def about(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr("m_about"))
        box.setIconPixmap(make_icon().pixmap(56, 56))
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setText(tr("about_text", ver=APP_VERSION, author=APP_AUTHOR, path=data_dir())
                    + f"<br><br><span style='color:{C['muted']}'>{tr('about_credits')}</span>"
                    + f"<br><br>♥ <a href='{DONATE_URL}' style='color:{C['blue']}'>{DONATE_URL.replace('https://', '')}</a>")
        box.exec()

    # ── Installation de profils GSX depuis une archive
    def set_check_downloads(self, on: bool):
        self.config.check_downloads = bool(on)
        self.config.save()

    _dl_manual_result = False

    def on_downloads_found(self, found: list):
        self._dl_found = found
        LOG.info("Téléchargements : %d archive(s) avec profil GSX à installer", len(found))
        if not found:
            self.dl_banner.hide()
            if self._dl_manual_result:
                self.status.setText(self._status_done_text() + "   ·   " + tr("dl_none"))
            return
        names = ", ".join(p.name for p in found[:3]) + ("…" if len(found) > 3 else "")
        txt = tr("dl_found", n=len(found), names=names)
        self.dl_lbl.setFullText(txt.replace("<b>", "").replace("</b>", ""))
        self.dl_lbl.setToolTip("<br>".join(str(p) for p in found))
        self.dl_banner.show()

    def _mark_seen(self, paths):
        keys = set(self.config.seen_archives)
        for p in paths:
            k = archive_key(Path(p))
            if k not in keys:
                self.config.seen_archives.append(k)
        self.config.seen_archives = self.config.seen_archives[-300:]
        try:
            self.config.save()
        except OSError:
            pass

    def install_found_downloads(self):
        found = list(self._dl_found)
        self.dl_banner.hide()
        self.install_paths(found)

    def ignore_found_downloads(self):
        self._mark_seen(self._dl_found)
        self.dl_banner.hide()

    def choose_archives(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("arch_choose"), str(self.config.download_dirs()[0]),
                                                tr("arch_filter"))
        if files:
            self.install_paths([Path(f) for f in files])

    @staticmethod
    def _dropped_paths(event) -> list:
        md = event.mimeData()
        if not md.hasUrls():
            return []
        out = []
        for u in md.urls():
            if u.isLocalFile():
                p = Path(u.toLocalFile())
                if p.suffix.lower() in ARCHIVE_EXT + (".ini", ".py"):
                    out.append(p)
        return out

    def dragEnterEvent(self, e):
        if self._dropped_paths(e) and not self.busy:
            e.acceptProposedAction()
            self._status_before_drop = self.status.text()
            self.status.setText("⬇  " + tr("arch_drop"))
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._dropped_paths(e):
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.status.setText(getattr(self, "_status_before_drop", ""))

    def dropEvent(self, e):
        paths = self._dropped_paths(e)
        self.status.setText(getattr(self, "_status_before_drop", ""))
        if paths:
            e.acceptProposedAction()
            QTimer.singleShot(0, lambda: self.install_paths(paths))

    def install_paths(self, paths: list):
        if not self.ensure_sim_closed():
            return
        names = ", ".join(Path(p).name for p in paths[:2]) + ("…" if len(paths) > 2 else "")
        with undoable(f"GSX — {names}"):
            self._install_paths(paths)
        self.update_undo_btn()

    def _install_paths(self, paths: list):
        archives = [Path(p) for p in paths if Path(p).suffix.lower() in ARCHIVE_EXT]
        loose = [Path(p) for p in paths if Path(p).suffix.lower() in (".ini", ".py")]
        installed, outcomes, errors = [], {}, []
        for a in archives:
            tmp = Path(tempfile.mkdtemp(prefix="sgm_"))
            try:
                extract_profiles(a, tmp)
                status, files, why = self._install_from_folder(tmp, a.name)
                outcomes[a] = status
                installed += files
                if status == ARCH_ERROR:
                    errors.append((a.name, why))
            except ArchiveError as err:
                outcomes[a] = ARCH_ERROR
                errors.append((a.name, tr(err.key, **err.kw)))
            except Exception as err:
                outcomes[a] = ARCH_ERROR
                errors.append((a.name, str(err)))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        if loose:
            tmp = Path(tempfile.mkdtemp(prefix="sgm_"))
            try:
                for f in loose:
                    if f.is_file() and f.stat().st_size <= MAX_MEMBER_SIZE:
                        shutil.copy2(f, tmp / f.name)
                status, files, why = self._install_from_folder(tmp, loose[0].name)
                installed += files
                if status == ARCH_ERROR:
                    errors.append((loose[0].name, why))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        self._mark_seen(archives)
        if installed:
            self.refresh_gsx_index()
            for r in self.rows.values():
                r.refresh_gsx()
            self.apply_filter()
            self.status.setText(tr("arch_done", files=", ".join(installed)))
        if errors:      # jamais supprimée : on le dit clairement
            warn(self, tr("arch_errors_kept") + "\n\n" + "\n".join(f"• {n} — {w}" for n, w in errors))
        self._cleanup_archives(outcomes)

    def _cleanup_archives(self, outcomes: dict):
        """Suppression (Corbeille) des archives de Téléchargements installées sans erreur, selon le réglage."""
        mode = self.config.archive_cleanup
        cands = cleanup_candidates(outcomes, self.config.download_dirs())
        if mode == "never" or not cands:
            return
        listing = "\n".join(f"• {p.name}" for p in cands)
        if mode == "ask" and not ask(self, tr("arch_delete_q", n=len(cands)) + "\n\n" + listing):
            return
        failed = trash_archives(cands)
        done = len(cands) - len(failed)
        if done:
            self.status.setText(tr("arch_deleted", n=done))
        if failed:
            warn(self, tr("arch_delete_fail") + "\n\n" + "\n".join(f"• {n} — {w}" for n, w in failed))

    def set_archive_cleanup(self, mode: str):
        if mode in ARCHIVE_CLEANUP:
            self.config.archive_cleanup = mode
            self.config.save()

    def _install_from_folder(self, folder: Path, name: str) -> tuple:
        """Installe le profil trouvé dans `folder`. Renvoie (état, fichiers installés, raison d'erreur)."""
        variants = profiles_in_folder(folder)
        if not variants:
            return ARCH_ERROR, [], tr("arch_none_short")
        v = variants[0]
        if len(variants) > 1:
            labels = [vlabel(x) or x.folder.name for x in variants]
            item, ok = QInputDialog.getItem(self, tr("arch_pick_title"), tr("arch_pick_version", name=name),
                                            labels, 0, False)
            if not ok:
                return ARCH_CANCEL, [], ""
            v = variants[labels.index(item)]
        dest = Path(self.config.gsx_folder())
        if dest.is_dir() and all((dest / f.name).is_file() and same_content(f, dest / f.name) for f in v.files):
            self.status.setText(tr("arch_already", name=name))
            return ARCH_OK, [], ""              # déjà installé à l'identique : compte comme un succès
        if not dest.is_dir() and not ask(self, tr("gsx_dir_create", path=dest, what=tr("what_profile")),
                                         default_yes=False):
            return ARCH_CANCEL, [], ""
        codes = icaos_of(v.files)
        matches = sorted({s.title for s in self.scenes.values() if s.icao and s.icao in codes})
        replaced = [f.name for f in v.files if (dest / f.name).is_file() and not same_content(f, dest / f.name)]
        msg = (tr("arch_confirm", name=name) + "\n\n" + tr("arch_files") + "\n"
               + "\n".join(f"• {f.name}" for f in v.files) + "\n\n"
               + (tr("arch_match", names=", ".join(matches)) if matches else tr("arch_nomatch"))
               + "\n\n" + tr("arch_dest") + "\n" + str(dest))
        if replaced:
            msg += "\n\n" + tr("gsx_replaced") + "\n" + "\n".join(f"• {n}" for n in replaced) \
                   + "\n" + tr("gsx_backup_note")
        if not ask(self, msg):
            return ARCH_CANCEL, [], ""
        try:
            return ARCH_OK, install_profile_files(v.files, dest), ""
        except Exception as err:
            return ARCH_ERROR, [], tr("gsx_copy_fail", err=err)

    # ── Bandeau
    def show_banner(self, html: str, kind: str = "info"):
        polish(self.banner, kind=kind)
        self.banner_lbl.setText(html)
        self.banner.show()

    _pending_import = None

    def set_busy(self, busy: bool):
        self.busy = busy
        if not busy and self._pending_import:
            folder, self._pending_import = self._pending_import, None
            QTimer.singleShot(0, lambda: self.import_from_portable(folder))
        for b in (self.btn_folders, self.btn_scan, self.btn_install, self.btn_all_off, self.btn_all_on,
                  self.btn_profiles):
            b.setEnabled(not busy)
        self.update_undo_btn()
        for r in self.rows.values():
            r.switch.setEnabled(not busy and r.scene.toggleable)

    # ── Analyse
    def manual_scan(self):
        """Bouton Analyser : les scènes, puis les dossiers de téléchargement (même les archives déjà proposées,
        sauf celles dont les profils sont déjà dans GSX)."""
        self._dl_manual = True
        self.start_scan()

    _dl_manual = False

    def check_downloads_now(self, manual: bool):
        if getattr(self, "dl_worker", None) is not None and self.dl_worker.isRunning():
            return
        seen = set() if manual else set(self.config.seen_archives)
        self._dl_manual_result = manual
        self.dl_worker = DownloadsWorker(seen, self.config.download_dirs(), gsx_dest_index(Path(self.config.gsx_folder())))
        self.dl_worker.done.connect(self.on_downloads_found)
        self.dl_worker.start()

    def start_scan(self):
        if self.busy:
            return
        self.set_busy(True)
        self.sources = find_sources(self.config)
        n_ok = sum(1 for s in self.sources if s.exists)
        self.status.setText(tr("scanning", n=n_ok))
        self.worker = ScanWorker(self.sources)
        self.worker.progress.connect(lambda i, n, name: self.status.setText(tr("scanning_i", i=i, n=n, name=name)))
        self.worker.done.connect(self.on_scan_done)
        self.worker.start()

    def _status_done_text(self) -> str:
        srcs = [s for s in self.sources if s.exists]
        names = ", ".join(sorted({display_source(s.label) for s in srcs})) or "—"
        return tr("status_done", n=len(self.scenes), names=names, time=self._scan_time)

    def on_scan_done(self, scenes: list):
        keys = {s.key for s in scenes}
        first = self.config.first_run
        if not first:
            self.session_new |= keys - set(self.config.known_scenes)
        self.config.known_scenes = sorted(keys)
        self.config.first_run = False
        try:
            self.config.save()
        except OSError:
            pass
        for s in scenes:
            s.is_new = s.key in self.session_new
        self.scenes = {s.key: s for s in scenes}
        LOG.info("Analyse : %d scènes, %d avec statics gérables, %d à vérifier, %d avec profil GSX",
                 len(scenes), sum(1 for s in scenes if s.toggleable),
                 sum(1 for s in scenes if s.state in (UNKNOWN, CONFLICT)), sum(1 for s in scenes if s.gsx_variants))
        self.rebuild_rows()
        self.set_busy(False)
        self._scan_time = datetime.now().strftime("%H:%M")
        self.status.setText(self._status_done_text())

        srcs = [s for s in self.sources if s.exists]
        if not srcs:
            self.show_banner(tr("banner_no_community", sim=self.config.sim), "warn")
        elif first:
            self.show_banner(tr("banner_first", n=len(scenes)))
        elif self.session_new:
            n = len(self.session_new & keys)
            if n:
                self.show_banner(tr("banner_new", n=n))
        missing = [s for s in self.sources if not s.exists]
        if missing and srcs:
            self.show_banner(tr("banner_missing", paths=", ".join(str(s.path) for s in missing)), "warn")
        if self._dl_manual:
            self._dl_manual = False
            self._dl_checked = True
            self.check_downloads_now(True)
        elif self.config.check_downloads and not self._dl_checked:
            self._dl_checked = True
            self.check_downloads_now(False)
        if not self._upd_started:
            self._upd_started = True
            QTimer.singleShot(800, self.maybe_check_updates)

    _scan_time = ""
    _upd_started = False
    upd_worker = None

    # ── Mise à jour automatique
    def set_update_check(self, on: bool):
        self.config.update_check = bool(on)
        self._save_config_quiet()

    def _save_config_quiet(self):
        try:
            self.config.save()
        except OSError:
            pass

    def maybe_check_updates(self):
        """Au lancement : demande une fois l'autorisation, puis au plus une vérification par jour."""
        if UPDATE_DISABLED or hosted():        # S10 : embarqué, c'est l'hôte qui livre SGM
            return
        if self.config.update_check is None:
            head, _sep, rest = tr("update_ask").partition("\n\n")
            self.upd_lbl.setText(f"<b>{_html.escape(head)}</b><br><span style='color:{C['muted']}'>"
                                 f"{_html.escape(rest).replace(chr(10), '<br>')}</span>")
            self.upd_banner.show()
            return
        if should_check_updates(self.config.update_check, self.config.update_last):
            self.check_updates(manual=False)

    def import_from_portable(self, folder=None):
        """Copie le SGM_data d'une version portable dans les données de la version installée, puis recharge.
        Le dossier se choisit tout de suite ; si une analyse tourne (premier lancement), la copie attend sa fin."""
        if not isinstance(folder, (str, Path)) or not folder:
            folder = QFileDialog.getExistingDirectory(self, tr("import_choose"), str(Path.home()))
            if not folder:
                return
        src = find_portable_data(folder)
        if src is None:
            warn(self, tr("import_none"))
            return
        if self.busy:                          # analyse en cours : reprise lancée dès qu'elle se termine
            self._pending_import = str(folder)
            return
        dst = data_dir()
        if norm_key(src) == norm_key(dst):
            warn(self, tr("import_none"))
            return
        if has_user_data(dst) and not FRESH_DATA and not ask(self, tr("import_replace"), default_yes=False):
            return
        try:
            close_logging()
            n = import_portable(src, dst)
        except (OSError, ValueError, shutil.Error) as e:
            setup_logging()
            LOG.warning("Reprise des données portables impossible : %s", e)
            warn(self, tr("import_err", err=e))
            return
        setup_logging()
        LOG.info("Données de la version portable reprises : %d fichiers", n)
        self.imp_banner.hide()
        QMessageBox.information(self, APP_NAME, tr("import_done", n=n))
        cfg = Config()
        self.config = cfg                     # la fenêtre qui se ferme n'écrase pas les réglages repris
        set_lang(cfg.lang)
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if cfg.lang in RTL_LANGS else Qt.LeftToRight)
        self._replace_window(None)

    def answer_update_question(self, yes: bool):
        self.upd_banner.hide()
        self.config.update_check = bool(yes)
        self._save_config_quiet()
        act = getattr(self, "update_auto_act", None)
        if act is not None:
            act.blockSignals(True)
            act.setChecked(bool(yes))
            act.blockSignals(False)
        if yes and should_check_updates(True, self.config.update_last):
            self.check_updates(manual=False)

    def check_updates(self, manual: bool):
        if (UPDATE_DISABLED and not manual) or hosted():
            return
        if self.upd_worker is not None and self.upd_worker.isRunning():
            return
        self.upd_worker = UpdateCheckWorker()
        self.upd_worker.done.connect(lambda info, err, mn=manual: self.on_update_result(info, err, mn))
        self.upd_worker.start()

    def on_update_result(self, info, err: str, manual: bool):
        self.config.update_last = time.time()
        self._save_config_quiet()
        if err:
            LOG.info("Vérification des mises à jour impossible : %s", err)
            if manual:
                warn(self, tr("update_fail", err=err))
            return
        if info and is_newer(info["version"]):
            LOG.info("Nouvelle version disponible : v%s", info["version"])
            if manual or info["version"] != self.config.update_skip:
                self.show_update_dialog(info)
        elif manual:
            QMessageBox.information(self, APP_NAME, tr("update_uptodate", ver=APP_VERSION))

    def show_update_dialog(self, info: dict):
        auto = os.name == "nt" and getattr(sys, "frozen", False)
        dlg = QDialog(self)
        dlg.setWindowTitle(APP_NAME)
        dlg.resize(560, 460)
        v = QVBoxLayout(dlg)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        h = QLabel(tr("update_title", ver=info["version"]))
        h.setObjectName("h1")
        h.setStyleSheet("font-size: 17px;")
        sub_ = QLabel(tr("update_current", cur=APP_VERSION))
        sub_.setObjectName("hint")
        notes = QTextBrowser()
        notes.setObjectName("doc")
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(info.get("notes") or info.get("page", ""))
        v.addWidget(h)
        v.addWidget(sub_)
        v.addWidget(notes, 1)
        row = QHBoxLayout()
        skip = QPushButton(tr("update_skip"))
        skip.setObjectName("ghost")
        later = QPushButton(tr("update_later"))
        go = QPushButton(tr("update_now") if auto else tr("update_page"))
        go.setObjectName("primary")
        go.setDefault(True)
        row.addWidget(skip)
        row.addStretch()
        row.addWidget(later)
        row.addWidget(go)
        v.addLayout(row)
        choice = {"v": ""}
        skip.clicked.connect(lambda: (choice.update(v="skip"), dlg.accept()))
        later.clicked.connect(dlg.reject)
        go.clicked.connect(lambda: (choice.update(v="go"), dlg.accept()))
        dlg.exec()
        dlg.deleteLater()
        if choice["v"] == "skip":
            self.config.update_skip = info["version"]
            self._save_config_quiet()
        elif choice["v"] == "go":
            if auto:
                self.start_update(info)
            else:
                QDesktopServices.openUrl(QUrl(info["page"]))

    def start_update(self, info: dict):
        if not info.get("sha_url"):
            warn(self, tr("update_no_sha"))
            QDesktopServices.openUrl(QUrl(info["page"]))
            return
        prog = QProgressDialog(tr("update_dl", ver=info["version"]), tr("update_later"), 0, 100, self)
        prog.setWindowTitle(APP_NAME)
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setAutoClose(False)
        self.dl_upd = UpdateDownloadWorker(info)
        self.dl_upd.progress.connect(lambda a, b: prog.setValue(int(a * 100 / b)) if b else None)
        cancelled = {"v": False}
        prog.canceled.connect(lambda: cancelled.update(v=True))

        def finished(res, err):
            prog.close()
            prog.deleteLater()
            if cancelled["v"]:
                return
            if err:
                LOG.warning("Mise à jour non préparée : %s", err)
                if err == "sha":
                    warn(self, tr("update_bad"))
                elif err == "no_sha":
                    warn(self, tr("update_no_sha"))
                    QDesktopServices.openUrl(QUrl(info["page"]))
                else:
                    warn(self, tr("update_err", err=err))
                return
            if not ask(self, tr("update_ready", ver=res["version"])):
                return
            LOG.info("Lancement de la mise à jour vers v%s", res["version"])
            # chaîne passée telle quelle à cmd (/s : guillemets extérieurs retirés) : & et espaces sans risque
            subprocess.Popen(f'cmd /d /s /c ""{res["script"]}""', cwd=str(res["script"].parent),
                             creationflags=0x00000008 | 0x08000000)      # DETACHED_PROCESS | CREATE_NO_WINDOW
            QApplication.instance().quit()
        self.dl_upd.done.connect(finished)
        self.dl_upd.start()
        prog.show()

    _gsx_index: list = []

    def refresh_gsx_index(self):
        self._gsx_index = gsx_dest_index(Path(self.config.gsx_folder()))

    def rebuild_rows(self):
        self.refresh_gsx_index()
        for r in self.rows.values():
            r.setParent(None)
            r.deleteLater()
        self.rows = {}
        order = sorted(self.scenes.values(), key=lambda s: (not s.is_new, s.title.lower()))
        for i, s in enumerate(order):
            row = SceneRow(s, self.config.gsx_folder, self.config.gsx_choices, self.remember_gsx_choice,
                           lambda: self._gsx_index)
            row.toggle_requested.connect(self.on_toggle)
            row.gsx_requested.connect(self.on_gsx)
            row.search_requested.connect(self.search_profile)
            row.restore_requested.connect(self.on_restore)
            self.list_l.insertWidget(1 + i, row)
            self.rows[s.key] = row
        self.apply_filter()
        self.update_stats()

    # ── Filtres (un par colonne, même logique pour Statics et GSX)
    def _column_filter_changed(self, col: str, key: str):
        if col == "statics":
            self.st_filter = key
        else:
            self.gsx_filter = key
        self.apply_filter()

    def focus_search(self):
        self.search.setFocus(Qt.ShortcutFocusReason)
        self.search.selectAll()

    def escape_pressed(self):
        """Échap : vide d'abord la recherche, puis remet tous les filtres."""
        if self.search.text():
            self.search.clear()
        elif self.st_filter != "all" or self.gsx_filter != "all" or self.new_chip.isChecked():
            self.reset_filters()

    def reset_filters(self):
        self.st_filter = self.gsx_filter = "all"
        self.col_header.set_filter("statics", "all")
        self.col_header.set_filter("gsx", "all")
        self.new_chip.setChecked(False)
        self.search.clear()
        self.apply_filter()

    def row_matches(self, row: SceneRow) -> bool:
        s = row.scene
        q = self.search.text().strip().lower()
        if q and q not in f"{s.title} {s.folder} {s.creator} {s.icao}".lower():
            return False
        if self.new_chip.isChecked() and not s.is_new:
            return False
        if self.st_filter != "all" and row.statics_state() != self.st_filter:
            return False
        if self.gsx_filter != "all" and row.gsx_state != self.gsx_filter:
            return False
        return True

    def apply_filter(self):
        visible = 0
        for row in self.rows.values():
            m = self.row_matches(row)
            row.setVisible(m)
            visible += m
        self.empty.setText(tr("empty_none") if not self.scenes else tr("empty_filter"))
        self.empty.setVisible(visible == 0)
        self.col_header.setVisible(visible > 0)
        filtered = visible != len(self.rows)
        self.scope_lbl.setText(tr("shown", n=visible) if filtered else "")
        active = (self.st_filter != "all" or self.gsx_filter != "all" or self.new_chip.isChecked()
                  or bool(self.search.text().strip()))
        self.reset_btn.setVisible(active)
        if visible == 0 and self.rows:
            self.col_header.setVisible(True)      # garder les filtres de colonne accessibles
        self._natural = None
        self.layout_columns()

    # ── Largeur des colonnes : proportionnelle à la fenêtre, réglable avec les poignées de l'en-tête
    def eventFilter(self, obj, ev):
        if obj is self.scroll.viewport() and ev.type() == QEvent.Resize:
            self.layout_columns()
        return super().eventFilter(obj, ev)

    def _avail_width(self) -> int:
        return max(400, self.scroll.viewport().width() - self.list_l.contentsMargins().left()
                   - self.list_l.contentsMargins().right())

    def _floors(self) -> tuple[int, int]:
        hs, hg = self.col_header.natural_widths()
        return max(120, hs), max(120, hg)

    def _natural_widths(self) -> tuple[int, int]:
        if self._natural is None:
            ns = ng = cs = cg = 0
            for row in self.rows.values():
                if not row.isHidden():
                    s, g = row.natural_widths()
                    a, b = row.natural_widths(notes=False)
                    ns, ng, cs, cg = max(ns, s), max(ng, g), max(cs, a), max(cg, b)
            self._natural = (ns, ng)
            self._compact = (cs, cg)
        return self._natural

    _compact = (0, 0)

    def current_col_widths(self) -> tuple[int, int]:
        avail = self._avail_width()
        self.col_header.set_compact(avail < COMPACT_BELOW)
        if self._col_auto:
            nat = self._natural_widths()
            fs, fg = self._floors()
            return fit_widths(avail, nat, (max(fs, self._compact[0]), max(fg, self._compact[1])))
        return column_widths(avail, self.col_fs, self.col_fg, self._floors())

    def layout_columns(self):
        ws, wg = self.current_col_widths()
        # l'en-tête (hors de la zone qui défile) a exactement la largeur des lignes
        self.col_header.setFixedWidth(self._avail_width())
        self.col_header.set_widths(ws, wg)
        for row in self.rows.values():
            row.set_col_widths(ws, wg)

    def _drag_column(self, handle: int, dx: int):
        avail = self._avail_width()
        ws, wg = self.current_col_widths()
        ms, mg = self._floors()
        if handle == 0:                    # bord gauche de Statics : la colonne s'élargit vers la gauche
            ws = max(ms, ws - dx)
        else:                              # entre Statics et GSX
            new_ws = max(ms, min(ws + dx, ws + wg - mg))
            wg -= new_ws - ws
            ws = new_ws
        if ws + wg + COL_SCENE_MIN + COL_OVERHEAD > avail:      # la colonne scène garde son minimum
            return
        self._col_auto = False
        self.col_fs, self.col_fg = ws / avail, wg / avail
        self.layout_columns()

    def _save_columns(self):
        self.config.col_auto = self._col_auto
        self.config.col_fs, self.config.col_fg = round(self.col_fs, 4), round(self.col_fg, 4)
        self.config.save()

    def _auto_columns(self):
        self._col_auto = True
        self._natural = None
        self.layout_columns()
        self._save_columns()

    def update_stats(self):
        sc = list(self.scenes.values())
        on = sum(1 for s in sc if s.state == ON)
        off = sum(1 for s in sc if s.state == OFF)
        other = sum(1 for s in sc if s.state in (MIXED, CONFLICT))
        gsx = sum(1 for s in sc if s.gsx_files)
        txt = (f"{tr('stats_n', n=len(sc))}   ·   <span style='color:{C['accent']}'>{tr('stats_on', n=on)}</span>"
               f"   ·   {tr('stats_off', n=off)}")
        if other:
            txt += f"   ·   <span style='color:{C['warn']}'>{tr('stats_check', n=other)}</span>"
        if gsx:
            txt += f"   ·   <span style='color:{C['blue']}'>{tr('stats_gsx', n=gsx)}</span>"
        self.stats.setText(txt)

    # ── Bascule statics
    def ensure_sim_closed(self) -> bool:
        """Bloque si MSFS 2020 OU MSFS 2024 tourne ; si on ne peut pas le savoir, demande (sécurité G3).
        Embarqué : l'hôte décide (accroche S11), avant chaque écriture."""
        if HOST_CONFIRM_SIM:
            try:
                return bool(HOST_CONFIRM_SIM(self))
            except Exception as e:
                LOG.warning("Contrôle du simulateur de l'hôte en erreur : %s", e)
                return False
        running = running_sims()
        if running is None:
            return ask(self, tr("sim_unknown"), default_yes=False)
        if running:
            warn(self, tr("sim_running", sim=" / ".join(running)))
            return False
        return True

    def refresh_scene(self, scene: Scene):
        new = scan_package(scene.root, scene.source)
        row = self.rows.get(scene.key)
        if new is None:
            self.scenes.pop(scene.key, None)
            if row:
                row.setParent(None)
                self.rows.pop(scene.key, None)
            return
        new.is_new = scene.is_new
        self.scenes[scene.key] = new
        if row:
            row.refresh(new)
            self._natural = None
            self.layout_columns()

    def on_toggle(self, scene: Scene, checked: bool):
        target = ON if checked else OFF
        row = self.rows.get(scene.key)
        if not self.ensure_sim_closed():
            if row:
                row.refresh(scene)
            return
        try:
            with undoable(f"Statics {'ON' if target == ON else 'OFF'} — {scene.title}"):
                set_scene_state(scene, target)
        except Exception as e:
            warn(self, tr("toggle_fail", name=scene.title, err=e))
        self.refresh_scene(scene)
        self.update_undo_btn()
        self.update_stats()
        if scene.key in self.scenes:
            self.status.setText(tr("toggled", name=scene.title, state=state_text(self.scenes[scene.key].state)))

    def set_all(self, target: str):
        targets, skipped = bulk_targets([r for r in self.rows.values() if not r.isHidden()], target)
        label = "ON" if target == ON else "OFF"
        note = ("\n\n" + tr("all_skipped", n=skipped)) if skipped else ""
        if not targets:
            if skipped:
                QMessageBox.information(self, APP_NAME, tr("all_already", label=label) + note)
            else:
                self.status.setText(tr("all_already", label=label))
            return
        if not ask(self, tr("all_confirm", n=len(targets), label=label) + note) or not self.ensure_sim_closed():
            return
        self.set_busy(True)
        errors = []
        with undoable(f"{tr('btn_all_on' if target == ON else 'btn_all_off')} ({len(targets)})"):
            for i, s in enumerate(targets, 1):
                self.status.setText(tr("all_progress", label=label, i=i, n=len(targets), name=s.title))
                QApplication.processEvents()
                try:
                    set_scene_state(s, target)
                except Exception as e:
                    errors.append(f"• {s.title} : {e}")
                self.refresh_scene(s)
        self.set_busy(False)
        self.update_stats()
        self.apply_filter()
        self.status.setText(tr("all_done", n=len(targets) - len(errors), label=label))
        if errors:
            warn(self, tr("all_errors") + "\n\n" + "\n".join(errors[:15]) + ("\n…" if len(errors) > 15 else ""))

    # ── GSX
    def search_profile(self, scene: Scene):
        url = search_url(gsx_search_query(scene))
        QDesktopServices.openUrl(QUrl(url))

    def remember_gsx_choice(self, scene: Scene, vid: str):
        if self.config.gsx_choices.get(scene.key) != vid:
            self.config.gsx_choices[scene.key] = vid
            try:
                self.config.save()
            except OSError:
                pass

    def on_gsx(self, scene: Scene, idx: int, folder: str):
        if not (0 <= idx < len(scene.gsx_variants)):
            return
        if not self.ensure_sim_closed():
            return
        v = scene.gsx_variants[idx]
        multi = len(scene.gsx_variants) > 1
        what = tr("what_version", name=vlabel(v)) if multi else tr("what_profile")
        dest = Path(folder)
        if not dest.is_dir() and not ask(self, tr("gsx_dir_create", path=dest, what=what), default_yes=False):
            return
        st = gsx_status(v.files, dest)
        if multi:
            state, act, _w, _n = gsx_variant_state(scene, dest, self.config.gsx_choices.get(scene.key))
            if state == VAR_CHOSEN and act == idx:
                self.status.setText(tr("gsx_already_active", name=scene.title, v=vlabel(v)))
                return
        replaced = [f.name for f in v.files if (dest / f.name).is_file() and not same_content(f, dest / f.name)]
        removed = [d.name for d in gsx_other_installed(scene, v, dest)]
        if replaced or removed or (multi and st == GSX_SAME):
            msg = (tr("gsx_activate_q", what=what, name=scene.title) if multi
                   else tr("gsx_update_q", name=scene.title)) + "\n\n"
            if replaced:
                msg += tr("gsx_replaced") + "\n" + "\n".join(f"• {n}" for n in replaced) + "\n\n"
            if removed:
                msg += tr("gsx_removed") + "\n" + "\n".join(f"• {n}" for n in removed) + "\n\n"
            msg += tr("gsx_backup_note")
            if not ask(self, msg):
                return
        try:
            with undoable(f"GSX — {scene.title}" + (f" ({vlabel(v)})" if multi else "")):
                copied = copy_gsx(scene, v, dest)
            if multi:
                self.remember_gsx_choice(scene, variant_id(scene, v))
        except Exception as e:
            warn(self, tr("gsx_copy_fail", err=e))
            return
        self.refresh_gsx_index()
        row = self.rows.get(scene.key)
        if row:
            row.refresh_gsx()
        done = tr("gsx_done_version", v=vlabel(v)) if multi else tr("gsx_done_copy")
        self.status.setText(tr("gsx_status", name=scene.title, what=done, files=", ".join(copied), dest=dest))

    # ── Profils de statics
    def build_profiles_menu(self, menu=None):
        m = menu if isinstance(menu, QMenu) else self.profiles_menu
        m.clear()
        profs = self.config.statics_profiles
        if not profs:
            a = m.addAction(tr("prof_none"))
            a.setEnabled(False)
        for name in sorted(profs, key=str.lower):
            a = m.addAction(tr("prof_item", name=name, n=len(profs[name])))
            a.triggered.connect(lambda _=False, n=name: self.apply_profile(n))
        m.addSeparator()
        a = m.addAction(tr("prof_save"))
        a.triggered.connect(self.save_profile)
        a.setEnabled(bool(self.scenes))
        if profs:
            sm = m.addMenu(tr("prof_delete"))
            for name in sorted(profs, key=str.lower):
                a = sm.addAction(name)
                a.triggered.connect(lambda _=False, n=name: self.delete_profile(n))

    def _save_config(self):
        try:
            self.config.save()
        except OSError as e:
            warn(self, str(e))

    def save_profile(self):
        states = profile_from_scenes(self.scenes.values())
        if not states:
            warn(self, tr("prof_empty"))
            return
        name, ok = QInputDialog.getText(self, tr("btn_profiles"), tr("prof_name_q"))
        name = (name or "").strip()[:40]
        if not ok or not name:
            return
        profs = self.config.statics_profiles
        same = next((k for k in profs if k.lower() == name.lower()), None)
        if same is not None:
            if not ask(self, tr("prof_exists", name=same), default_yes=False):
                return
            profs.pop(same)
        profs[name] = states
        self._save_config()
        LOG.info("Profil de statics enregistré : %s (%d scènes)", name, len(states))
        self.status.setText(tr("prof_saved", name=name, n=len(states)))

    def delete_profile(self, name: str):
        if name in self.config.statics_profiles and ask(self, tr("prof_delete_q", name=name), default_yes=False):
            self.config.statics_profiles.pop(name)
            self._save_config()
            self.status.setText(tr("prof_deleted", name=name))

    def apply_profile(self, name: str):
        prof = self.config.statics_profiles.get(name)
        if prof is None or self.busy:
            return
        todo, check, missing = profile_plan(prof, self.scenes.values())
        skip = ("\n\n" + tr("prof_skip", check=check, missing=missing)) if check or missing else ""
        if not todo:
            if skip:
                QMessageBox.information(self, APP_NAME, tr("prof_already", name=name) + skip)
            else:
                self.status.setText(tr("prof_already", name=name))
            return
        n_on = sum(1 for _s, tg in todo if tg == ON)
        if not ask(self, tr("prof_apply_q", name=name, n=len(todo), on=n_on, off=len(todo) - n_on) + skip) \
                or not self.ensure_sim_closed():
            return
        LOG.info("Profil de statics appliqué : %s (%d bascules)", name, len(todo))
        self.set_busy(True)
        errors = []
        with undoable(f"{tr('btn_profiles')} — {name}"):
            for i, (s, target) in enumerate(todo, 1):
                self.status.setText(tr("all_progress", label=name, i=i, n=len(todo), name=s.title))
                QApplication.processEvents()
                try:
                    set_scene_state(s, target)
                except Exception as e:
                    errors.append(f"• {s.title} : {e}")
                self.refresh_scene(s)
        self.set_busy(False)
        self.update_stats()
        self.apply_filter()
        self.status.setText(tr("prof_done", name=name, n=len(todo) - len(errors)))
        if errors:
            warn(self, tr("all_errors") + "\n\n" + "\n".join(errors[:15]) + ("\n…" if len(errors) > 15 else ""))

    # ── Annuler la dernière action
    def update_undo_btn(self):
        if not hasattr(self, "btn_undo"):
            return
        label = undo_label()
        self.btn_undo.setEnabled(bool(label) and not self.busy)
        self.btn_undo.setToolTip(tr("undo_tip", label=label) + "  (Ctrl+Z)" if label else tr("undo_tip_none"))

    def undo_last_action(self):
        label = undo_label()
        if self.busy:
            return
        if not label:
            self.status.setText(tr("undo_nothing"))
            return
        if not self.ensure_sim_closed() or not ask(self, tr("undo_confirm", label=label)):
            return
        touched = undo_paths()
        try:
            undo_last()
        except UndoError as e:
            warn(self, str(e))
            self.update_undo_btn()
            return
        except OSError as e:
            warn(self, tr("undo_failed", err=e))
            return
        # scènes concernées relues ; choix de version GSX oubliés pour les profils remis
        keys = {norm_key(p) for p in touched}
        gsx_names = {p.name.lower() for p in touched}
        for s in list(self.scenes.values()):
            root = norm_key(s.root)
            if any(k.startswith(root) for k in keys):
                self.refresh_scene(s)
            if gsx_names & {f.name.lower() for f in s.gsx_files}:
                self.config.gsx_choices.pop(s.key, None)
        try:
            self.config.save()
        except OSError:
            pass
        self.refresh_gsx_index()
        for r in self.rows.values():
            r.refresh_gsx()
        self.update_stats()
        self.apply_filter()
        self.update_undo_btn()
        self.status.setText(tr("undo_done", label=label))

    def open_folders(self):
        dlg = FoldersDialog(self.config, self.sources, self)
        dlg.exec()
        if dlg.downloads_changed:
            self._dl_manual = True              # nouveaux dossiers : on les vérifie tout de suite
        if dlg.changed or dlg.downloads_changed:
            self.start_scan()
        elif dlg.gsx_changed:
            self.refresh_gsx_index()
            for r in self.rows.values():
                r.refresh_gsx()
            self.apply_filter()


# ════════════════════════════════════════════════════════════════════════════
#  Icônes dessinées (aucun fichier externe)
# ════════════════════════════════════════════════════════════════════════════

_FOLDER_ICON = None


def folder_icon() -> QIcon:
    global _FOLDER_ICON
    if _FOLDER_ICON is not None:
        return _FOLDER_ICON
    icon = QIcon()
    for mode, color in ((QIcon.Normal, C["muted"]), (QIcon.Active, C["text"])):
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color), 5)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(8, 50)
        path.lineTo(8, 16)
        path.quadTo(8, 12, 12, 12)
        path.lineTo(24, 12)
        path.lineTo(30, 18)
        path.lineTo(52, 18)
        path.quadTo(56, 18, 56, 22)
        path.lineTo(56, 50)
        path.quadTo(56, 54, 52, 54)
        path.lineTo(12, 54)
        path.quadTo(8, 54, 8, 50)
        p.drawPath(path)
        p.drawLine(8, 27, 56, 27)
        p.end()
        icon.addPixmap(pm, mode)
    _FOLDER_ICON = icon
    return icon


def dot_icon(color: str) -> QIcon:
    """Pastille de couleur (Tout OFF rouge, Tout ON vert), grisée quand le bouton est désactivé."""
    icon = QIcon()
    for mode, c in ((QIcon.Normal, color), (QIcon.Active, color), (QIcon.Disabled, C["border2"])):
        pm = QPixmap(24, 24)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(c))
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.end()
        icon.addPixmap(pm, mode)
    return icon


def heart_icon() -> QIcon:
    icon = QIcon()
    for mode, color in ((QIcon.Normal, C["heart"]), (QIcon.Active, C["heart_hover"])):
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        path = QPainterPath()
        path.moveTo(32, 56)
        path.cubicTo(6, 38, 2, 22, 12, 13)
        path.cubicTo(20, 6, 29, 9, 32, 17)
        path.cubicTo(35, 9, 44, 6, 52, 13)
        path.cubicTo(62, 22, 58, 38, 32, 56)
        p.drawPath(path)
        p.end()
        icon.addPixmap(pm, mode)
    return icon


ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def paint_logo(p: QPainter, size: int):
    """Icône de SGM (proposition C, choisie par Fabian) : « SGM » sur trois marques de piste,
    vert = statics, bleu = GSX. Sous 32 px, seul le « S » reste (les trois lettres deviennent illisibles)."""
    s = size / 256.0
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    pen = QPen(QColor(C["border2"]))
    pen.setWidthF(max(1.0, 6 * s))
    p.setPen(pen)
    p.setBrush(QColor(C["surface"]))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 54 * s, 54 * s)
    small = size < 32
    text = "S" if small else "SGM"
    f = QFont()
    f.setFamilies(["Segoe UI", "Inter", "DejaVu Sans", "Arial"])
    f.setWeight(QFont.ExtraBold)
    f.setPixelSize(max(6, round((150 if small else 92) * s)))
    if not small:
        f.setLetterSpacing(QFont.AbsoluteSpacing, -2 * s)
    # Le texte doit tenir dans 76 % de la largeur, quelle que soit la police disponible.
    w = QFontMetricsF(f).horizontalAdvance(text)
    if w > 0.76 * size:
        f.setPixelSize(max(6, int(f.pixelSize() * 0.76 * size / w)))
    p.setFont(f)
    p.setPen(QColor(C["text"]))
    top = (8 if small else 40) * s
    bottom = (168 if small else 170) * s
    p.drawText(QRectF(0, top, size, bottom - top), Qt.AlignHCenter | Qt.AlignBottom, text)
    p.setPen(Qt.NoPen)
    y, h = 176 * s, max(2.0, 12 * s)
    for x, col in ((44, C["accent"]), (108, C["accent"]), (172, C["blue"])):
        p.setBrush(QColor(col))
        p.drawRoundedRect(QRectF(x * s, y, 40 * s, h), h / 2, h / 2)


def logo_image(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    paint_logo(p, size)
    p.end()
    return img


def make_icon() -> QIcon:
    icon = QIcon()
    for n in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(logo_image(n)))
    return icon


def dark_title_bar(win: QWidget):
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = int(win.winId())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FabianFuchs.SGM")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    f = QFont()
    f.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial",
                   "Microsoft YaHei UI", "Yu Gothic UI", "Noto Sans CJK SC", "Noto Sans Arabic"])
    f.setPointSizeF(9.5)
    app.setFont(f)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(make_icon())
    global FRESH_DATA
    FRESH_DATA = not has_user_data(data_dir())      # version installée lancée pour la 1re fois : reprise proposée
    cfg = Config()
    lang = cfg.lang
    set_lang(lang)
    setup_logging()
    LOG.info("SGM v%s démarré · %s · %s %s · Python %s · langue %s%s", APP_VERSION, cfg.sim,
             platform.system(), platform.release(), platform.python_version(), lang,
             " · exe" if getattr(sys, "frozen", False) else "")
    app.setLayoutDirection(Qt.RightToLeft if lang in RTL_LANGS else Qt.LeftToRight)
    app.main_window = MainWindow()
    dark_title_bar(app.main_window)
    app.main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
