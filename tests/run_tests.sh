#!/usr/bin/env bash
# Lance toute la suite de tests de SGM (sans écran : Qt en mode « offscreen »).
# Prérequis : Python 3.10+ et PySide6 (pip install pyside6).
set -euo pipefail
cd "$(dirname "$0")"
export QT_QPA_PLATFORM=offscreen
python -m unittest discover -s . -p "test_*.py" -v
