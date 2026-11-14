# -*- coding: utf-8 -*-
"""Contrôle automatique des traductions de SGM (outil de l'agent `traducteur`).

Usage : python scripts/check_i18n.py [--strict]
Signale, pour chaque langue :
  - clé manquante (repli sur l'anglais) ;
  - champs {…} différents de l'anglais (bloquant) ;
  - texte identique à l'anglais (probablement non traduit) ;
  - texte d'interface court nettement plus long que l'anglais (risque de texte coupé) ;
  - balises HTML différentes de l'anglais dans les longs textes d'aide.
Code de sortie 1 en cas d'erreur bloquante (ou de tout avertissement avec --strict).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402

FIELD_RE = re.compile(r"\{[a-z_]+\}")
TAG_RE = re.compile(r"</?([a-z0-9]+)")
LONG_KEYS = {"help_html", "disclaimer_html", "licenses_html"}
# textes courts affichés dans des zones de largeur fixe (boutons, colonnes, menus)
SHORT_PREFIXES = ("btn_", "st_", "cat_", "filter_", "col_", "mode_", "lbl_", "grp_", "note_")  # menus et barre d'état : largeur libre
SAME_OK = {"ok", "gsx", "sgm", "paypal", "github", "msfs", "statics", "on", "off", "lite", "full", "vdgs", "icao", "flightsim", "to", "bgl", "json", "layout"}
# clés volontairement identiques à l'anglais dans toutes les langues (repli normal)
SAME_KEYS = {"f_on", "f_off", "f_gsx", "col_statics", "st_on", "st_off", "grp_on", "grp_off", "statics_tip",
             "standard", "stats_on", "stats_off", "stats_gsx", "all_progress", "auto", "help_lang_note"}
# langues où l'on mesure la longueur en caractères (les idéogrammes sont plus larges : on double)
WIDE = {"zh", "ja"}


def visual_len(text: str, lang: str) -> float:
    return len(text) * (1.7 if lang in WIDE else 1)


def check() -> tuple[list, list]:
    errors, warnings = [], []
    en = i18n.EN
    for code, _name in i18n.LANGS:
        if code == "en":
            continue
        tr = i18n.TR.get(code, {})
        for key, src in en.items():
            if key not in tr:
                if key in SAME_KEYS:
                    continue
                if key not in LONG_KEYS or code == "fr":
                    warnings.append(f"[{code}] clé manquante : {key}")
                continue
            dst = tr[key]
            if sorted(FIELD_RE.findall(src)) != sorted(FIELD_RE.findall(dst)):
                errors.append(f"[{code}] champs différents dans {key} : {FIELD_RE.findall(src)} ≠ {FIELD_RE.findall(dst)}")
            if key in LONG_KEYS:
                if sorted(TAG_RE.findall(src)) != sorted(TAG_RE.findall(dst)):
                    warnings.append(f"[{code}] balises HTML différentes dans {key}")
                continue
            plain = re.sub(r"[\W\d_]+", " ", src).strip().lower()
            if dst == src and plain and not set(plain.split()) <= SAME_OK:
                warnings.append(f"[{code}] identique à l'anglais : {key} = {src!r}")
            if key.startswith(SHORT_PREFIXES) and len(src) >= 4:
                ratio = visual_len(dst, code) / max(1, len(src))
                if ratio > 1.6 and visual_len(dst, code) > 18:
                    warnings.append(f"[{code}] texte court bien plus long que l'anglais ({ratio:.1f}×) : {key} = {dst!r}")
        for key in tr:
            if key not in en:
                warnings.append(f"[{code}] clé inconnue (absente de l'anglais) : {key}")
    return errors, warnings


if __name__ == "__main__":
    errs, warns = check()
    for line in errs:
        print("ERREUR  ", line)
    for line in warns:
        print("attention", line)
    print(f"\n{len(errs)} erreur(s), {len(warns)} avertissement(s)")
    sys.exit(1 if errs or ("--strict" in sys.argv and warns) else 0)
