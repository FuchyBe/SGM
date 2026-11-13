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
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus, urlencode
import platform
from pathlib import Path, PurePosixPath

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF,
                            QSize, Qt, QThread, QTimer, QUrl, Signal)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont,
                           QIcon, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup, QComboBox, QInputDialog,
                               QDialog, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QSizePolicy, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

from i18n import LANGS, RTL_LANGS, get_lang, set_lang, tr

APP_NAME = "SGM"
APP_FULL = "Statics & GSX Manager"
APP_VERSION = "0.6"
APP_AUTHOR = "Fabian Fuchs"
# Lien de don public (PayPal.me)
DONATE_URL = "https://paypal.me/Fuchy"
# Recherche de profils GSX : {q} est remplacé par « OACI GSX » (encodé)
# Signalements : Issues publiques du dépôt FuchyBe/SGM
ISSUES_NEW_URL = "https://github.com/FuchyBe/SGM/issues/new"

SEARCH_ENGINES = {
    "fsto": "https://flightsim.to/search/?keyword={q}",
    "web": "https://www.google.com/search?q=site%3Aflightsim.to+{q}",
}

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


def license_dir() -> Path:
    """Dossier « licenses » livré à côté du programme (ou dans le paquet PyInstaller)."""
    for base in (app_dir(), Path(getattr(sys, "_MEIPASS", app_dir()))):
        if (base / "licenses").is_dir():
            return base / "licenses"
    return app_dir() / "licenses"


def data_dir() -> Path:
    """Dossier portable à côté de l'application ; repli sur %APPDATA% s'il n'est pas inscriptible."""
    global _DATA_DIR
    if _DATA_DIR is None:
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


def norm_key(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _empty_profile() -> dict:
    return {"manual_folders": [], "known_scenes": [], "gsx_folder": "", "gsx_choices": {}, "scanned": False}


class Config:
    def __init__(self):
        self.file = data_dir() / "config.json"
        self.lang = "en"
        self.search = "fsto"
        self.check_downloads = True
        self.seen_archives: list = []
        self.sim = DEFAULT_SIM
        self.profiles: dict = {}
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if isinstance(data, dict):
            if int(data.get("version", 1)) >= 3:
                self.lang = str(data.get("lang") or "en")
                self.search = data.get("search") if data.get("search") in SEARCH_ENGINES else "fsto"
                self.check_downloads = bool(data.get("check_downloads", True))
                self.seen_archives = [str(x) for x in data.get("seen_archives", [])][-300:]
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
    def first_run(self) -> bool:
        return not self.p["scanned"]

    @first_run.setter
    def first_run(self, v):
        self.p["scanned"] = not v

    def gsx_folder(self) -> str:
        return self.gsx_override or default_gsx_folder(self.sim)

    def save(self):
        data = {"version": 3, "lang": self.lang, "sim": self.sim, "search": self.search,
                "check_downloads": self.check_downloads, "seen_archives": self.seen_archives[-300:],
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


def parse_usercfg(cfg: Path) -> Path | None:
    try:
        text = cfg.read_text(encoding="utf-8", errors="ignore")
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
            val = val.strip()
            if val:
                return Path(val)
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
    return out


def display_source(label: str) -> str:
    return label.replace(MANUAL, tr("manual"))


# ════════════════════════════════════════════════════════════════════════════
#  Analyse des scènes
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class StaticsGroup:
    mode: str              # "rename" | "variant" | "conflict"
    directory: Path
    active: Path           # rename : fichier actuel / variant : statics.bgl actif
    state: str
    on_file: Path | None = None
    off_file: Path | None = None
    note: str = ""         # clé de traduction

    @property
    def toggleable(self) -> bool:
        return self.mode in ("rename", "variant")


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


def build_groups(directory: Path, files: list[str]) -> list[StaticsGroup]:
    variants: dict = {}
    plain: dict = {}
    for name in files:
        stem, ext = split_ext(name)
        if stem is None:
            continue
        m = VARIANT_RE.search(stem)
        if m:
            base = stem[:m.start()] + m.group(1) + stem[m.end():]
            v = variants.setdefault(base.lower(), {"base": base})
            v.setdefault(m.group(2).lower(), name)
        else:
            plain.setdefault(stem.lower(), {"stem": stem, "exts": {}})["exts"][ext] = name

    pairs = {}
    for key, v in variants.items():
        if "on" in v and "off" in v:
            pairs[key] = v
        else:   # variante isolée -> fichier simple
            for tok in ("on", "off"):
                if tok in v:
                    stem, ext = split_ext(v[tok])
                    plain.setdefault(stem.lower(), {"stem": stem, "exts": {}})["exts"][ext] = v[tok]

    groups, used = [], set()
    for key, v in pairs.items():
        on_f, off_f = directory / v["on"], directory / v["off"]
        target = key if (key in plain and ".bgl" in plain[key]["exts"]) else None
        if target is None and len(pairs) == 1:
            cands = [k for k, p in plain.items() if ".bgl" in p["exts"]]
            if len(cands) == 1:
                cand = directory / plain[cands[0]]["exts"][".bgl"]
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
            active = directory / plain[target]["exts"][".bgl"]
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

    for key, p in plain.items():
        if key in used:
            continue
        exts = p["exts"]
        if ".bgl" in exts and ".bgl.off" in exts:
            groups.append(StaticsGroup("conflict", directory, directory / exts[".bgl"], CONFLICT,
                                       note="note_conflict"))
        elif ".bgl" in exts:
            groups.append(StaticsGroup("rename", directory, directory / exts[".bgl"], ON))
        else:
            groups.append(StaticsGroup("rename", directory, directory / exts[".bgl.off"], OFF))
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
            if "statics" in low and (low.endswith(".bgl") or low.endswith(".bgl.off")):
                by_dir.setdefault(dirpath, []).append(fn)
            elif low.endswith(".ini"):
                inis.append(Path(dirpath) / fn)
    groups = []
    for d in sorted(by_dir):
        groups += build_groups(Path(d), sorted(by_dir[d], key=str.lower))
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
            sc = scan_package(p, source_label(s, p))
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


def backup_files(root: Path, files: list[Path]):
    base = data_dir() / "backups" / re.sub(r'[<>:"/\\|?*]', "_", root.name)
    dest = base / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.is_file():
            shutil.copy2(f, dest / f.name)
    old = sorted([d for d in base.iterdir() if d.is_dir()])
    for d in old[:-MAX_BACKUPS_PER_SCENE]:
        shutil.rmtree(d, ignore_errors=True)


def set_scene_state(scene: Scene, target: str):
    groups = [g for g in scene.groups if g.toggleable and g.state != target]
    if not groups:
        return
    meta = PackageMeta(scene.root)
    to_backup = [meta.layout_file, meta.manifest_file]
    to_backup += [g.active for g in groups if g.mode == "variant" and g.state == UNKNOWN and g.active.exists()]
    backup_files(scene.root, to_backup)
    try:
        for g in groups:
            if g.mode == "rename":
                cur = g.active
                new = cur.with_name(cur.name + ".off") if target == OFF else cur.with_name(cur.name[:-4])
                if new.exists():
                    raise ToggleError(tr("err_exists", name=new.name))
                os.rename(cur, new)
                if target == OFF:
                    meta.remove(cur)
                else:
                    meta.upsert(new)
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


def copy_gsx(scene: Scene, variant: GsxVariant, dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    replaced = [dest_dir / f.name for f in variant.files
                if (dest_dir / f.name).is_file() and not same_content(f, dest_dir / f.name)]
    removed = gsx_other_installed(scene, variant, dest_dir)
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
    return copied


# ── Archives de profils GSX ─────────────────────────────────────────────────

ARCHIVE_EXT = (".zip", ".7z", ".rar")
MAX_MEMBER_SIZE = 4 * 1024 * 1024        # un profil GSX fait quelques Ko : au-delà, on ignore
MAX_ARCHIVE_SCAN = 40                    # nombre d'archives récentes examinées dans Téléchargements
DOWNLOAD_MAX_AGE_DAYS = 60


class ArchiveError(Exception):
    def __init__(self, key: str, **kw):
        super().__init__(key)
        self.key, self.kw = key, kw


def find_7z() -> str | None:
    exe = shutil.which("7z") or shutil.which("7z.exe")
    if exe:
        return exe
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramW6432")):
        if base and (Path(base) / "7-Zip" / "7z.exe").is_file():
            return str(Path(base) / "7-Zip" / "7z.exe")
    return None


def _safe_rel(name: str) -> Path | None:
    """Chemin relatif sûr (pas de .., pas de lecteur, pas de chemin absolu)."""
    parts = [p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in ("", ".", "/")]
    if not parts or any(p == ".." or ":" in p for p in parts):
        return None
    return Path(*parts)


def extract_profiles(archive: Path, dest: Path):
    """Extrait uniquement les .ini et .py d'une archive dans `dest`."""
    ext = archive.suffix.lower()
    if ext == ".zip":
        try:
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith((".ini", ".py")):
                        continue
                    if info.file_size > MAX_MEMBER_SIZE:
                        continue
                    rel = _safe_rel(info.filename)
                    if rel is None:
                        continue
                    target = dest / rel
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


def install_profile_files(files: list[Path], dest_dir: Path) -> list[str]:
    """Copie des fichiers de profil dans GSX ; sauvegarde ce qui est remplacé."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    replaced = [dest_dir / f.name for f in files
                if (dest_dir / f.name).is_file() and not same_content(f, dest_dir / f.name)]
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


def find_download_archives(seen: set) -> list[Path]:
    """Archives récentes du dossier Téléchargements qui semblent contenir un profil GSX."""
    folder = downloads_dir()
    try:
        cands = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ARCHIVE_EXT]
    except OSError:
        return []
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
        for n in names:
            low = n.replace("\\", "/").lower()
            base = low.rsplit("/", 1)[-1]
            if base.endswith(".ini") and (GSX_NAME_RE.match(base) or "gsx" in low):
                out.append(p)
                break
    return out


def report_url(kind: str, sim: str, lang: str) -> str:
    """Lien « nouvelle issue » prérempli. Aucune donnée personnelle : ni chemin, ni nom d'utilisateur."""
    title = "Bug: " if kind == "bug" else "Idea: "
    if kind == "bug":
        body = ("### What happened?\n\n\n"
                "### What did you expect?\n\n\n"
                "### Steps to reproduce\n1. \n2. \n\n"
                "### Scenery concerned (name, developer, ICAO)\n\n\n"
                "### Message shown by SGM (if any)\n\n\n")
    else:
        body = ("### Your idea\n\n\n"
                "### Why would it help you?\n\n\n")
    body += ("---\n"
             f"SGM beta v{APP_VERSION} · {sim} · {platform.system()} {platform.release()} · UI language: {lang}\n"
             "_Please do not post personal information (e-mail, full file paths with your user name)._")
    return ISSUES_NEW_URL + "?" + urlencode({"title": title, "body": body,
                                            "labels": "bug" if kind == "bug" else "enhancement"})


def sim_running(sim: str) -> bool:
    if os.name != "nt":
        return False
    try:
        res = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                             timeout=10, creationflags=0x08000000)
        out = res.stdout.decode("utf-8", errors="ignore").lower()
    except Exception:
        return False
    return f'"{SIMS[sim]["process"]}"' in out


# ════════════════════════════════════════════════════════════════════════════
#  Interface
# ════════════════════════════════════════════════════════════════════════════

C = {
    "bg": "#0E1014", "surface": "#161920", "surface2": "#1C2029", "border": "#232833",
    "border2": "#2D3441", "text": "#E7E9ED", "muted": "#8B93A5", "faint": "#5E6678",
    "accent": "#4CC9A0", "accent_dark": "#0A1A14", "warn": "#E3B266", "blue": "#7AA7F5",
    "heart": "#E2677A",
}

QSS = f"""
* {{ font-size: 13px; }}
QMainWindow, QDialog, QWidget#central, QWidget#list {{ background: {C['bg']}; color: {C['text']}; }}
QLabel {{ background: transparent; color: {C['text']}; }}
QLabel#h1 {{ font-size: 21px; font-weight: 600; letter-spacing: 0.3px; }}
QLabel#subtitle, QLabel#sub, QLabel#status, QLabel#hint {{ color: {C['muted']}; }}
QLabel#sub {{ font-size: 12px; }}
QLabel#status {{ font-size: 12px; }}
QLabel#stats {{ color: {C['muted']}; font-size: 12px; }}
QLabel#title {{ font-size: 14px; font-weight: 600; }}
QLabel#empty {{ color: {C['faint']}; font-size: 14px; padding: 40px; }}
QLabel#fullname {{ color: {C['muted']}; font-size: 15px; font-weight: 500; padding-bottom: 2px; }}
QLabel#simPill {{ color: {C['blue']}; border: 1px solid #2E4670; background: #141C2A; border-radius: 5px;
                  padding: 2px 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.6px; }}
QLabel#credit {{ color: {C['faint']}; font-size: 11px; padding: 0 6px; }}
QMenuBar {{ background: {C['bg']}; color: {C['muted']}; border-bottom: 1px solid {C['border']}; padding: 2px 8px; }}
QMenuBar::item {{ background: transparent; padding: 5px 10px; border-radius: 5px; }}
QMenuBar::item:selected {{ background: {C['surface2']}; color: {C['text']}; }}
QMenu {{ background: {C['surface']}; color: {C['text']}; border: 1px solid {C['border2']}; padding: 5px; }}
QMenu::item {{ padding: 6px 26px 6px 22px; border-radius: 5px; }}
QMenu::item:selected {{ background: {C['surface2']}; }}
QMenu::item:disabled {{ color: {C['faint']}; }}
QMenu::separator {{ height: 1px; background: {C['border']}; margin: 5px 8px; }}
QToolButton#cornerBtn {{ background: transparent; border: 1px solid transparent; border-radius: 5px;
                         color: {C['muted']}; padding: 2px 6px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }}
QToolButton#cornerBtn:hover {{ background: {C['surface2']}; border-color: {C['border2']}; color: {C['text']}; }}
QToolButton#cornerBtn::menu-indicator {{ image: none; width: 0; }}
QPushButton#varChip {{ background: transparent; color: {C['muted']}; border: 1px solid {C['border2']};
                      border-radius: 6px; padding: 4px 10px; font-size: 12px; }}
QPushButton#varChip:hover {{ color: {C['text']}; background: {C['surface2']}; }}
QPushButton#varChip[vstate="active"] {{ color: {C['accent']}; border-color: #2B5A4B; background: #12241E; font-weight: 600; }}
QPushButton#varChip[vstate="inactive"] {{ color: #E07A72; border-color: #5A2D2A; background: #1F1413; }}
QPushButton#varChip[vstate="inactive"]:hover {{ color: #F09088; background: #2A1817; }}
QPushButton#varChip[vstate="check"] {{ color: {C['warn']}; border-color: #4A3A1E; background: #221C12; }}
QPushButton#varChip[vstate="check"]:hover {{ background: #2C2416; }}
QComboBox {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']};
             border-radius: 6px; padding: 3px 8px; font-size: 12px; }}
QComboBox QAbstractItemView {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']};
                               selection-background-color: #232835; }}
QLabel#note[ok="true"] {{ color: {C['accent']}; }}
QLabel#gsxManual {{ color: {C['accent']}; border: 1px solid #2B5A4B; background: #12241E; border-radius: 6px;
                   padding: 4px 10px; font-size: 12px; }}
QPushButton#searchBtn {{ background: transparent; color: {C['muted']}; border: 1px dashed {C['border2']};
                        border-radius: 6px; padding: 4px 9px; font-size: 12px; }}
QPushButton#searchBtn:hover {{ color: {C['blue']}; border-color: #2E4670; background: #141C2A; }}
QComboBox#catCombo {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 9px;
                      padding: 8px 34px 8px 12px; font-size: 13px; min-width: 190px; }}
QComboBox#catCombo:hover {{ border-color: {C['border2']}; }}
QComboBox#catCombo::drop-down {{ border: none; width: 30px; }}
QComboBox#catCombo::down-arrow {{ image: none; width: 0; height: 0; }}
QPushButton#folderBtn {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
                        padding: 0; min-width: 26px; max-width: 26px; min-height: 24px; max-height: 24px; }}
QPushButton#folderBtn:hover {{ background: {C['surface2']}; border-color: {C['border2']}; }}
QPushButton#folderBtn:pressed {{ background: #232835; }}
QLabel#badgeNew {{ color: {C['blue']}; border: 1px solid #2E4670; background: #172235;
                   border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }}
QLabel#chip {{ color: {C['faint']}; border: 1px solid {C['border2']}; border-radius: 4px;
               padding: 1px 6px; font-size: 11px; }}
QLabel#state {{ font-size: 12px; font-weight: 600; min-width: 92px; }}
QLabel#state[state="on"] {{ color: {C['accent']}; }}
QLabel#state[state="off"] {{ color: {C['muted']}; }}
QLabel#state[state="none"] {{ color: {C['faint']}; font-weight: 400; }}
QLabel#state[state="mixed"], QLabel#state[state="conflict"] {{ color: {C['warn']}; }}
QLabel#src {{ color: {C['muted']}; font-size: 11px; font-weight: 700; letter-spacing: 0.6px; min-width: 70px; }}
QLabel#path {{ color: {C['text']}; }}
QLabel#missing {{ color: {C['warn']}; font-size: 11px; }}
QLineEdit {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 8px;
             padding: 7px 11px; color: {C['text']}; selection-background-color: {C['accent']}; }}
QLineEdit:focus {{ border-color: {C['border2']}; background: {C['surface2']}; }}
QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']};
               border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #232835; border-color: {C['border2']}; }}
QPushButton:pressed {{ background: #1A1E27; }}
QPushButton:disabled {{ color: {C['faint']}; background: {C['surface']}; }}
QPushButton#primary {{ background: {C['accent']}; color: {C['accent_dark']}; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #5DD6AE; }}
QPushButton#primary:disabled {{ background: #2A4A40; color: #5E7A70; }}
QPushButton#danger {{ background: #B5443D; color: #FFF4F3; border: none; font-weight: 600; }}
QPushButton#danger:hover {{ background: #C85149; }}
QPushButton#danger:pressed {{ background: #9E3A34; }}
QPushButton#danger:disabled {{ background: #4A2725; color: #8A6360; }}
QPushButton#chipBtn {{ background: transparent; border: 1px solid transparent; color: {C['muted']};
                       padding: 5px 11px; border-radius: 7px; }}
QPushButton#chipBtn:hover {{ color: {C['text']}; }}
QPushButton#chipBtn:checked {{ background: {C['surface2']}; border-color: {C['border2']}; color: {C['text']}; }}
QPushButton#gsx {{ background: transparent; color: {C['blue']}; border: 1px solid #2E4670;
                  border-radius: 6px; padding: 4px 10px; font-size: 12px; }}
QPushButton#gsx:hover {{ background: #172235; }}
QPushButton#gsx[gsx="same"] {{ color: {C['muted']}; border-color: {C['border2']}; }}
QPushButton#gsx[gsx="diff"] {{ color: {C['warn']}; border-color: #4A3A1E; }}
QFrame#vsep {{ background: {C['border']}; min-width: 1px; max-width: 1px; border: none; }}
QFrame#vsepHidden {{ background: transparent; min-width: 1px; max-width: 1px; border: none; }}
QLabel#colHead {{ color: {C['faint']}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; }}
QLabel#note {{ color: {C['faint']}; font-size: 11px; }}
QLabel#note[warn="true"] {{ color: {C['warn']}; }}
QLabel#none {{ color: {C['faint']}; font-size: 12px; }}
QPushButton#ghost {{ background: transparent; border: none; color: {C['muted']}; padding: 4px 8px; }}
QPushButton#ghost:hover {{ color: {C['text']}; }}
QFrame#chips {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 9px; }}
QFrame#row {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 10px; }}
QFrame#row:hover {{ border-color: {C['border2']}; background: #181C24; }}
QFrame#banner {{ background: #141C2A; border: 1px solid #263A5C; border-radius: 9px; }}
QFrame#banner[kind="warn"] {{ background: #221C12; border-color: #4A3A1E; }}
QFrame#sep {{ background: {C['border']}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#folderRow {{ background: {C['surface']}; border: 1px solid {C['border']}; border-radius: 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['border2']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3A4352; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QToolTip {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border2']}; padding: 6px; }}
QMessageBox {{ background: {C['surface']}; }}
QTextBrowser#doc {{ background: {C['surface']}; color: {C['text']}; border: 1px solid {C['border']};
                    border-radius: 10px; padding: 14px 18px; font-size: 13px; }}
"""

DOC_CSS = f"""
h2 {{ color: {C['text']}; font-size: 18px; margin: 0 0 8px 0; }}
h3 {{ color: {C['accent']}; font-size: 14px; margin: 16px 0 4px 0; }}
p, li {{ color: #C9CED8; line-height: 140%; }}
i {{ color: {C['muted']}; }}
b {{ color: {C['text']}; }}
a {{ color: {C['blue']}; }}
"""


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
        track = blend(QColor("#2A303C"), QColor(C["accent"]), self._knob)
        knob = QColor("#F3F5F7")
        if not self.isEnabled():
            track, knob = QColor("#20242D"), QColor("#4A5161")
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = self.height() - 6
        t = self._knob if self.layoutDirection() == Qt.LeftToRight else 1 - self._knob
        x = 3 + t * (self.width() - 6 - d)
        p.setBrush(knob)
        p.drawEllipse(QRectF(x, 3, d, d))

    def sizeHint(self):
        return self.size()


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
        super().setText(self.fontMetrics().elidedText(self._full, Qt.ElideRight, max(10, self.width())))


def state_text(st: str) -> str:
    return tr({ON: "st_on", OFF: "st_off", MIXED: "st_mixed", CONFLICT: "st_conflict", NONE: "st_none"}[st])


GROUP_STATE_KEY = {ON: "grp_on", OFF: "grp_off", UNKNOWN: "grp_unknown", CONFLICT: "grp_conflict"}
MODE_KEY = {"rename": "mode_rename", "variant": "mode_variant", "conflict": "mode_conflict"}
MODE_NOTE_KEY = {"rename": "note_rename", "variant": "note_variant", "conflict": "note_conflict"}
GSX_TEXT_KEY = {GSX_MISSING: "gsx_copy", GSX_SAME: "gsx_same", GSX_DIFF: "gsx_diff"}
GSX_INFO_KEY = {GSX_MISSING: "gsx_info_missing", GSX_SAME: "gsx_info_same", GSX_DIFF: "gsx_info_diff"}

FILTER_KEYS = ("all", "on", "off", "new", "check")
CATEGORY_KEYS = ("all", "statics", "gsx_scene", "gsx_manual", "gsx_none")

COL_STATICS_W = 220
COL_GSX_W = 300
ROW_MARGINS = (16, 11, 14, 11)
ROW_SPACING = 16


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


class ColumnHeader(QWidget):
    """En-têtes alignés sur les colonnes des lignes."""

    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self)
        l, _t, r, _b = ROW_MARGINS
        h.setContentsMargins(l + 1, 0, r + 1, 0)
        h.setSpacing(ROW_SPACING)
        for key, width in (("col_scene", None), (None, 0), ("col_statics", COL_STATICS_W),
                           (None, 0), ("col_gsx", COL_GSX_W)):
            if key is None:
                h.addWidget(vsep(False))
                continue
            lbl = QLabel(tr(key))
            lbl.setObjectName("colHead")
            if width:
                lbl.setFixedWidth(width)
                h.addWidget(lbl)
            else:
                h.addWidget(lbl, 1)


class SceneRow(QFrame):
    toggle_requested = Signal(object, bool)
    gsx_requested = Signal(object, int, str)    # scène, index de variante, dossier GSX
    search_requested = Signal(object)

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
        line = QHBoxLayout()
        line.setSpacing(10)
        self.state_lbl = QLabel()
        self.state_lbl.setObjectName("state")
        self.switch = Switch()
        sp = self.switch.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.switch.setSizePolicy(sp)
        self.switch.clicked.connect(lambda c: self.toggle_requested.emit(self.scene, c))
        line.addWidget(self.state_lbl, 1)
        line.addWidget(self.switch)
        self.st_note = ElidedLabel()
        self.st_note.setObjectName("note")
        cv.addLayout(line)
        cv.addWidget(self.st_note)
        h.addWidget(col)
        h.addWidget(vsep())

        # ── Colonne GSX
        col, gv = column(COL_GSX_W)
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
                note = tr(MODE_NOTE_KEY[modes.pop()])
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

    def refresh_gsx(self):
        s = self.scene
        self._clear_gsx()
        self.manual = gsx_manual_profiles(s, self.gsx_index_fn()) if self.gsx_index_fn else []
        if self.gsx_folder_fn is None:
            self.gsx_none.show()
            self._note("")
            return
        if not s.gsx_variants:
            # ── Aucun profil fourni avec la scène : profil installé à la main ? sinon recherche
            if self.manual:
                self.gsx_none.hide()
                lbl = QLabel(tr("gsx_manual_lbl"))
                lbl.setObjectName("gsxManual")
                tip = tr("gsx_manual_tip") + "<br>" + "<br>".join(f"• {n}" for n in self.manual)
                lbl.setToolTip(tip)
                self._add_gsx_widget(lbl)
                self._note(", ".join(self.manual), tip=tip)
            else:
                self.gsx_none.show()
                self._note(tr("gsx_none_note", q=gsx_search_query(s)) if s.icao else "")
            if s.icao:
                self._search_button()
            return
        self.gsx_none.hide()
        self._refresh_scene_profile()
        if self.manual:      # un autre profil pour le même aéroport : GSX risque de choisir le mauvais
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

    def open_folder(self):
        root = self.scene.root
        if not root.is_dir():
            warn(self, tr("folder_missing_msg", path=root))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def mouseDoubleClickEvent(self, _e):
        self.open_folder()


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


class DownloadsWorker(QThread):
    done = Signal(list)

    def __init__(self, seen: set):
        super().__init__()
        self.seen = seen

    def run(self):
        try:
            found = find_download_archives(self.seen)
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
        self.setWindowTitle(f"{tr('dlg_folders')} — {config.sim}")
        self.setMinimumWidth(660)
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
        v.addWidget(hint)
        self.list = QVBoxLayout()
        self.list.setSpacing(6)
        v.addLayout(self.list)
        btns = QHBoxLayout()
        add = QPushButton(tr("add_folder"))
        add.clicked.connect(self.add_folder)
        close = QPushButton(tr("close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        btns.addWidget(add)
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

    def rebuild(self):
        while self.list.count():
            item = self.list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
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

        gl = QLabel(tr("gsx_dest"))
        gl.setObjectName("hint")
        self.list.addSpacing(8)
        self.list.addWidget(gl)
        folder = self.config.gsx_folder()
        tail = [] if self.config.gsx_override else [self._chip(tr("auto"))]
        tail += [self._ghost(tr("modify"), self.change_gsx), self._ghost(tr("default"), self.reset_gsx)]
        self._row("GSX", folder, Path(folder).is_dir(), tail)

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
        self.filter = "all"
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
        self.chip_group = QButtonGroup(self)
        for key in FILTER_KEYS:
            b = QPushButton(tr("f_" + key))
            b.setObjectName("chipBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(key == "all")
            b.clicked.connect(lambda _=False, k=key: self.set_filter(k))
            self.chip_group.addButton(b)
            ch.addWidget(b)
        bar.addWidget(chips)
        self.category = "all"
        self.cat_combo = ChevronCombo()
        self.cat_combo.setObjectName("catCombo")
        self.cat_combo.setToolTip(tr("cat_tip"))
        self.cat_combo.setCursor(Qt.PointingHandCursor)
        for key in CATEGORY_KEYS:
            self.cat_combo.addItem(tr("cat_" + key), key)
        self.cat_combo.currentIndexChanged.connect(self._category_changed)
        bar.addWidget(self.cat_combo)
        root.addLayout(bar)

        # Actions
        bar2 = QHBoxLayout()
        bar2.setSpacing(8)
        self.btn_folders = QPushButton(tr("btn_folders"))
        self.btn_folders.clicked.connect(self.open_folders)
        self.btn_scan = QPushButton(tr("btn_scan"))
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_install = QPushButton(tr("btn_install"))
        self.btn_install.setToolTip(tr("arch_drop_tip"))
        self.btn_install.clicked.connect(self.choose_archives)
        self.btn_all_off = QPushButton(tr("btn_all_off"))
        self.btn_all_off.setObjectName("danger")
        self.btn_all_off.clicked.connect(lambda: self.set_all(OFF))
        self.btn_all_on = QPushButton(tr("btn_all_on"))
        self.btn_all_on.setObjectName("primary")
        self.btn_all_on.clicked.connect(lambda: self.set_all(ON))
        for b in (self.btn_folders, self.btn_scan, self.btn_install, self.btn_all_off, self.btn_all_on):
            b.setCursor(Qt.PointingHandCursor)
        self.scope_lbl = QLabel()
        self.scope_lbl.setObjectName("hint")
        bar2.addWidget(self.btn_folders)
        bar2.addWidget(self.btn_scan)
        bar2.addWidget(self.btn_install)
        bar2.addStretch()
        bar2.addWidget(self.scope_lbl)
        bar2.addWidget(self.btn_all_off)
        bar2.addWidget(self.btn_all_on)
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
        self.list_l.addWidget(self.col_header)
        self.empty = QLabel(tr("empty_scanning"))
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.list_l.addWidget(self.empty)
        self.list_l.addStretch()
        self.scroll.setWidget(self.list_w)
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
            self.filter = state.get("filter", "all")
            for b, key in zip(self.chip_group.buttons(), FILTER_KEYS):
                b.setChecked(key == self.filter)
            cat = state.get("category", "all")
            self.cat_combo.setCurrentIndex(max(0, list(CATEGORY_KEYS).index(cat) if cat in CATEGORY_KEYS else 0))
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

        m_srch = m_set.addMenu(tr("m_search"))
        egrp = QActionGroup(self)
        for key, label in (("fsto", "search_fsto"), ("web", "search_web")):
            a = QAction(tr(label), self, checkable=True)
            a.setChecked(self.config.search == key)
            a.triggered.connect(lambda _=False, k=key: self.set_search_engine(k))
            egrp.addAction(a)
            m_srch.addAction(a)
        a = QAction(tr("m_check_dl"), self, checkable=True)
        a.setChecked(self.config.check_downloads)
        a.toggled.connect(self.set_check_downloads)
        m_set.addAction(a)
        a = QAction(tr("m_install_arch"), self)
        a.triggered.connect(self.choose_archives)
        m_set.addAction(a)

        m_set.addSeparator()
        a = QAction(tr("m_folders"), self)
        a.triggered.connect(self.open_folders)
        m_set.addAction(a)

        m_help = mb.addMenu(tr("m_help"))
        for key, fn, shortcut in (("m_guide", self.show_guide, "F1"),
                                  ("m_disclaimer", self.show_disclaimer, None),
                                  ("m_licenses", self.show_licenses, None),
                                  ("m_backups", self.open_backups, None)):
            a = QAction(tr(key), self)
            if shortcut:
                a.setShortcut(shortcut)
            a.triggered.connect(fn)
            m_help.addAction(a)
        m_help.addSeparator()
        for key, kind in (("m_report_bug", "bug"), ("m_suggest", "idea")):
            a = QAction(tr(key), self)
            a.triggered.connect(lambda _=False, k=kind: self.open_report(k))
            m_help.addAction(a)
        m_help.addSeparator()
        for key, fn in (("m_donate", self.donate), ("m_about", self.about)):
            a = QAction(tr(key), self)
            a.triggered.connect(fn)
            m_help.addAction(a)

        # Coin droit : version · auteur, don, langue
        corner = QWidget()
        hl = QHBoxLayout(corner)
        hl.setContentsMargins(0, 0, 4, 0)
        hl.setSpacing(4)
        credit = QLabel(f"beta v{APP_VERSION}  ·  {APP_AUTHOR}")
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
            "filter": self.filter, "category": self.category, "search": self.search.text(),
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
        rows = [(f"{APP_NAME} — {APP_FULL}", f"beta v{APP_VERSION}"), ("Qt for Python (PySide6)", pyside_v),
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
                        f"color:#C9CED8'>{_html.escape(text)}</pre>")
        if not found:
            doc += f"<p><i>{tr('licenses_missing')}</i></p>"
        DocDialog(tr("m_licenses").rstrip("…"), doc, "", self).exec()

    def open_backups(self):
        d = data_dir() / "backups"
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def open_report(self, kind: str):
        QDesktopServices.openUrl(QUrl(report_url(kind, self.config.sim, get_lang())))

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

    def on_downloads_found(self, found: list):
        self._dl_found = found
        if not found:
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
        files, _ = QFileDialog.getOpenFileNames(self, tr("arch_choose"), str(downloads_dir()), tr("arch_filter"))
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
        archives = [Path(p) for p in paths if Path(p).suffix.lower() in ARCHIVE_EXT]
        loose = [Path(p) for p in paths if Path(p).suffix.lower() in (".ini", ".py")]
        installed = []
        for a in archives:
            tmp = Path(tempfile.mkdtemp(prefix="sgm_"))
            try:
                extract_profiles(a, tmp)
                installed += self._install_from_folder(tmp, a.name)
            except ArchiveError as err:
                warn(self, tr(err.key, **err.kw))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        if loose:
            tmp = Path(tempfile.mkdtemp(prefix="sgm_"))
            try:
                for f in loose:
                    if f.is_file() and f.stat().st_size <= MAX_MEMBER_SIZE:
                        shutil.copy2(f, tmp / f.name)
                installed += self._install_from_folder(tmp, loose[0].name)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        self._mark_seen(archives)
        if installed:
            self.refresh_gsx_index()
            for r in self.rows.values():
                r.refresh_gsx()
            self.apply_filter()
            self.status.setText(tr("arch_done", files=", ".join(installed)))

    def _install_from_folder(self, folder: Path, name: str) -> list:
        variants = profiles_in_folder(folder)
        if not variants:
            QMessageBox.information(self, APP_NAME, tr("arch_none", name=name))
            return []
        v = variants[0]
        if len(variants) > 1:
            labels = [vlabel(x) or x.folder.name for x in variants]
            item, ok = QInputDialog.getItem(self, tr("arch_pick_title"), tr("arch_pick_version", name=name),
                                            labels, 0, False)
            if not ok:
                return []
            v = variants[labels.index(item)]
        dest = Path(self.config.gsx_folder())
        if not dest.is_dir() and not ask(self, tr("gsx_dir_create", path=dest, what=tr("what_profile")),
                                         default_yes=False):
            return []
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
            return []
        try:
            return install_profile_files(v.files, dest)
        except Exception as err:
            warn(self, tr("gsx_copy_fail", err=err))
            return []

    # ── Bandeau
    def show_banner(self, html: str, kind: str = "info"):
        polish(self.banner, kind=kind)
        self.banner_lbl.setText(html)
        self.banner.show()

    def set_busy(self, busy: bool):
        self.busy = busy
        for b in (self.btn_folders, self.btn_scan, self.btn_install, self.btn_all_off, self.btn_all_on):
            b.setEnabled(not busy)
        for r in self.rows.values():
            r.switch.setEnabled(not busy and r.scene.toggleable)

    # ── Analyse
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
        if self.config.check_downloads and not self._dl_checked:
            self._dl_checked = True
            self.dl_worker = DownloadsWorker(set(self.config.seen_archives))
            self.dl_worker.done.connect(self.on_downloads_found)
            self.dl_worker.start()

    _scan_time = ""

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
            self.list_l.insertWidget(2 + i, row)
            self.rows[s.key] = row
        self.apply_filter()
        self.update_stats()

    # ── Filtres
    def set_filter(self, key: str):
        self.filter = key
        self.apply_filter()

    def _category_changed(self, _i):
        self.category = self.cat_combo.currentData() or "all"
        self.apply_filter()

    def row_matches(self, row: SceneRow) -> bool:
        s = row.scene
        q = self.search.text().strip().lower()
        if q and q not in f"{s.title} {s.folder} {s.creator} {s.icao}".lower():
            return False
        c = self.category
        if c == "statics" and not s.groups:
            return False
        if c == "gsx_scene" and not s.gsx_variants:
            return False
        if c == "gsx_manual" and (s.gsx_variants or not row.manual):
            return False
        if c == "gsx_none" and (s.gsx_variants or row.manual):
            return False
        f = self.filter
        st = s.state
        return (f == "all" or (f == "on" and st == ON) or (f == "off" and st == OFF)
                or (f == "new" and s.is_new) or (f == "check" and st in (MIXED, CONFLICT)))

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
        if sim_running(self.config.sim):
            warn(self, tr("sim_running", sim=self.config.sim))
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

    def on_toggle(self, scene: Scene, checked: bool):
        target = ON if checked else OFF
        row = self.rows.get(scene.key)
        if not self.ensure_sim_closed():
            if row:
                row.refresh(scene)
            return
        try:
            set_scene_state(scene, target)
        except Exception as e:
            warn(self, tr("toggle_fail", name=scene.title, err=e))
        self.refresh_scene(scene)
        self.update_stats()
        if scene.key in self.scenes:
            self.status.setText(tr("toggled", name=scene.title, state=state_text(self.scenes[scene.key].state)))

    def set_all(self, target: str):
        targets = [r.scene for r in self.rows.values()
                   if r.isVisible() and r.scene.toggleable and r.scene.state != target]
        label = "ON" if target == ON else "OFF"
        if not targets:
            self.status.setText(tr("all_already", label=label))
            return
        if not ask(self, tr("all_confirm", n=len(targets), label=label)) or not self.ensure_sim_closed():
            return
        self.set_busy(True)
        errors = []
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
        url = SEARCH_ENGINES.get(self.config.search, SEARCH_ENGINES["fsto"]).format(q=quote_plus(gsx_search_query(scene)))
        QDesktopServices.openUrl(QUrl(url))

    def set_search_engine(self, key: str):
        self.config.search = key
        self.config.save()

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

    def open_folders(self):
        dlg = FoldersDialog(self.config, self.sources, self)
        dlg.exec()
        if dlg.changed:
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


def heart_icon() -> QIcon:
    icon = QIcon()
    for mode, color in ((QIcon.Normal, C["heart"]), (QIcon.Active, "#F07F90")):
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


def make_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(C["surface2"]))
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
    p.setBrush(QColor(C["accent"]))
    p.drawRoundedRect(QRectF(12, 38, 40, 14), 7, 7)
    p.setBrush(QColor("#F3F5F7"))
    p.drawEllipse(QRectF(36, 40, 10, 10))
    p.setPen(QColor(C["text"]))
    f = QFont()
    f.setPixelSize(22)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(0, 6, 64, 30), Qt.AlignCenter, "✈")
    p.end()
    return QIcon(pm)


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
    lang = Config().lang
    set_lang(lang)
    app.setLayoutDirection(Qt.RightToLeft if lang in RTL_LANGS else Qt.LeftToRight)
    app.main_window = MainWindow()
    dark_title_bar(app.main_window)
    app.main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
