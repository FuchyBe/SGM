# Mise à jour flightsim.to — beta v0.9.3

Tout ce qu'il faut pour mettre à jour la page https://flightsim.to/addon/119017/sgm-statics-gsx-manager-beta-v0-5
Les textes à recopier sont en anglais, entre les lignes `---`.

## Marche à suivre

1. **Fichier** : après la publication de la release v0.9.3 sur GitHub, télécharge `SGM_beta_v0.9.3.zip`
   (pièce jointe de la release). C'est le même fichier que la mise à jour automatique, avec son empreinte SHA-256.
2. Sur flightsim.to : *Edit* › *Upload new version* › dépose `SGM_beta_v0.9.3.zip`.
3. **Version** : `beta v0.9.3` — **titre de la version** : `beta v0.9.3 — Safety, reliability & a cleaner interface`
4. **Changelog** : recopie le bloc « Changelog ». Il couvre tout depuis la v0.8, puisque la v0.9 et la v0.9.1
   et la v0.9.2 n'ont jamais été publiées. Si tu as déjà mis la v0.9 en ligne sur flightsim.to, ne recopie que les
   parties « beta v0.9.3 » et « beta v0.9.2 ».
5. **Short description** et **Description** : remplace les textes actuels par ceux ci-dessous.
6. **Mots-clés** : ajoute ceux de la liste.
7. **Images** : remplace la galerie par les 5 visuels de `docs/flightsim/visuels/` (1920 × 1080, le 5e en 2560 × 1440), dans l'ordre :
   `1-hero.png` (vignette), `2-statics.png`, `3-gsx.png`, `4-securite.png`, `5-interface.png` (interface expliquée).
8. Le message de don et « About Me » ne changent pas.

---

## Titre de la version

beta v0.9.3 — Safety, reliability & a cleaner interface

---

## Short description

Switch airport static aircraft ON/OFF in one click — the developers' own methods (Orbx, iniBuilds, Drzewiecki, UK2000…), never an airport loaded twice — plus GSX Pro profiles installed by drag & drop or straight from your Downloads. Undo, statics profiles, restore original, automatic updates. Free & portable.

---

## Description

**SGM — Statics & GSX Manager** is a free, portable Windows tool for **MSFS 2024** (and MSFS 2020) that lets you switch the **static aircraft** of your airport sceneries ON or OFF in one click, and manage your **GSX Pro profiles** — without digging through folders.

**Static aircraft**
- Finds every airport with optional statics in your Community folders and your own scenery folders (any depth).
- Recognises the methods used by the developers themselves — iniBuilds, Orbx, Drzewiecki Design, UK2000, Aerosoft, LimeSim, SimPixel, Burning Blue, JetStream, Homa Sim and many more: `.off`, `.disabled`, `.nostatic` versions (official Orbx / Drzewiecki method, compatible with the Orbx Central control panel), with/without-statics pairs, complete airport files, on/off variants.
- Keeps each developer's own naming, and always updates `layout.json` so MSFS really loads (or unloads) the file.
- **Never loads an airport twice.** Unclear cases are never switched: SGM marks them "To check" and opens the right folder so you can do it yourself.
- Switch one airport, all displayed airports (simple cases only), or apply a **statics profile** — e.g. "Dense AI traffic" or "Photo flights" — in one click.

**GSX Pro profiles**
- Detects profiles shipped inside sceneries and installs them into the GSX folder in one click.
- FULL / LITE / VDGS versions: choose one, SGM remembers it.
- Shows airports without a GSX profile and searches flightsim.to for "ICAO GSX" in one click.
- **Drag & drop** a downloaded archive (.zip, .7z, .rar) onto SGM, or let SGM find GSX profile archives in your **download folders** (at launch and with Scan) and install them — it can then send the archive to the Recycle Bin.

**Safe by design**
- **Undo** (Ctrl+Z) for every action — all-or-nothing, even if a file is locked midway — backup before every change, and a record of the **original state** of each scenery: right-click › *Restore original state*, or *Tools › Restore everything to original*.
- Blocked while MSFS 2020 or MSFS 2024 is running. A GSX profile you edited yourself is never removed or overwritten. A scenery changed since the last scan is never touched.
- Downloaded archives are checked before anything is extracted: only `.ini` / `.py` profile files, safe paths, limited size.
- No installation. The only internet connection is the optional **automatic update** check (asked at first launch): nothing about you or your files is ever sent. 12 languages.

**Found a bug or have an idea?** *Help › Report a problem…* opens a small form: SGM prepares your text, a statics analysis report and its log (no user name, no personal path) and opens the GitHub page — nothing is sent until you click Submit.
🐞 https://github.com/FuchyBe/SGM/issues

If SGM saves you some time, you can buy me a coffee ☕ — https://paypal.me/Fuchy — thank you, and happy flying!

---

## Changelog

**beta v0.9.3 — Cleaner interface**
- **Menus reorganised**: *Settings*, a new *Tools* menu (scan, install a GSX profile, statics profiles, undo, restore everything, analysis report, backups and log folders) and *Help*.
- **Keyboard shortcuts**: Ctrl+F search, Esc clears the search then the filters, F5 scan, Ctrl+Z undo, F1 guide.
- Clearer labels (*Statics profiles*, *New sceneries*); the update question is a banner instead of a blocking window; lighter GSX column; Folders window in titled sections.

**beta v0.9.2 — Safety & reliability**

*Safety*
- Archives containing absolute or network paths are refused; `.7z` / `.rar` archives with an oversized profile file are refused before anything is extracted.
- The updater only replaces SGM's own files, never touches `SGM_data`, and works whatever the folder name.

*Reliability*
- **Undo and Restore are all-or-nothing**: if a file is locked midway (antivirus, Explorer…), everything goes back exactly as it was.
- The original state of a scenery is kept after a restore, so a restore can be undone and done again.
- A scenery moved or changed since the last scan is never touched — SGM asks you to scan again.
- Installing a GSX profile is blocked while the simulator is running.

*Interface*
- The column header stays visible while scrolling; better contrast for secondary text; clearer check boxes.
- File names readable in Arabic; compact ON/OFF buttons on narrow windows.
- Translations reviewed (Portuguese, Chinese, Arabic, Dutch, Japanese, Polish…) and guide updated.

**beta v0.9 / v0.9.1 — Automatic updates**
- **Automatic updates** (optional, asked at first launch): once a day at most SGM checks for a new version on GitHub, shows what's new and — if you click *Update now* — downloads it, verifies its SHA-256 fingerprint, replaces its files and restarts. Your settings, backups and profiles are kept, and the previous version is put back if anything goes wrong. *Help › Check for updates…* at any time.
- *Restore everything* never removes or overwrites a GSX profile you edited after SGM installed it.
- Archives go to the Recycle Bin only from a fixed drive; on a USB stick or network drive (where Windows would delete them for good) they are kept.
- File changes are blocked while MSFS 2020 **or** MSFS 2024 is running; if SGM cannot tell, it asks.
- Backups stored per scenery; Undo keeps far fewer copies (renamed files are found by fingerprint, 500 MB cap).
- `.7z` / `.rar` archives tested with a real 7-Zip; French interface complete; resizable Folders and Guide windows.

**Updating**
- From v0.9 or later: SGM offers this version itself (*Update now*).
- From an older version: delete the old SGM folder (keep `SGM_data` to keep your settings, backups and profiles), unzip v0.9.3, run `SGM.exe`. From now on, SGM can update itself.

---

## Mots-clés (à ajouter aux actuels)

auto update, undo, profiles, safe, 7z, rar, shortcuts

Mots-clés actuels, pour mémoire : statics, static aircraft, parked aircraft, GSX, GSX Pro, GSX profile, Virtuali,
FSDreamTeam, scenery, airport, community folder, manager, tool, utility, MSFS 2024, MSFS 2020, toggle, AI traffic,
freeware, Orbx, iniBuilds, Drzewiecki, UK2000
