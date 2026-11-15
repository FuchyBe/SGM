# Mise à jour flightsim.to — beta v0.9.2

À recopier sur la page flightsim.to (en anglais). Fichier à publier : `SGM_beta_v0.9.2.zip`.
Titre de la version : **beta v0.9.2 — Safety & reliability**
La description et la short description de la v0.9 restent valables (`maj-v0.9.md`).

---

## Changelog — beta v0.9.2

**Safety**
- Archives containing absolute or network paths are refused; .7z / .rar archives with an oversized profile file are refused before anything is extracted.
- The updater only replaces SGM's own files, keeps `SGM_data`, and works whatever the folder name.

**Reliability**
- Undo and Restore are all-or-nothing: if a file is locked midway (antivirus…), everything goes back exactly as it was.
- The original state of a scenery is kept after a restore, so it can be undone and restored again.
- A scenery moved or changed since the last scan is never touched — SGM asks you to scan again.
- Installing a GSX profile is blocked while the simulator is running.

**Interface**
- Column header always visible while scrolling; better contrast; clearer check boxes; file names readable in Arabic; compact ON/OFF buttons on narrow windows.
- Translations reviewed (Portuguese, Chinese, Arabic, Dutch, Japanese, Polish…) and guide updated.

**Updating**: from v0.9 or v0.9.1, SGM offers this version itself (*Update now*). From an older version: delete the old SGM folder (keep `SGM_data`), unzip v0.9.2, run `SGM.exe`.
