# Mise à jour flightsim.to — beta v0.9

À recopier sur la page flightsim.to (en anglais). Fichier à publier : `SGM_beta_v0.9.zip`
(produit par `build_exe.bat`, ou dossier `SGM` de la compilation GitHub zippé).
Titre de la version : **beta v0.9 — Automatic updates & safer than ever**

---

## Short description

Switch airport static aircraft ON/OFF in one click — the developers' own methods (Orbx, iniBuilds, Drzewiecki, UK2000…), never an airport loaded twice — plus GSX Pro profiles installed by drag & drop or straight from your Downloads. Undo, statics profiles, restore original, automatic updates. Free & portable.

---

## Description (remplace la description actuelle)

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
- **Drag & drop** a downloaded archive onto SGM, or let SGM find GSX profile archives in your **download folders** (at launch and with Scan) and install them — it can then send the archive to the Recycle Bin.

**Safe by design**
- **Undo** (Ctrl+Z) for every action, backup before every change, and a record of the **original state** of each scenery: right-click › *Restore original state*, or *Help › Restore everything to original*.
- Blocked while MSFS 2020 or MSFS 2024 is running. A GSX profile you edited yourself is never removed or overwritten.
- No installation. The only internet connection is the optional update check (asked at first launch): nothing about you or your files is ever sent. 12 languages.

**Found a bug or have an idea?** *Help › Report a problem…* opens a small form: SGM prepares your text, a statics analysis report and its log (no user name, no personal path) and opens the GitHub page — nothing is sent until you click Submit.
🐞 https://github.com/FuchyBe/SGM/issues

If SGM saves you some time, you can buy me a coffee ☕ — https://paypal.me/Fuchy — thank you, and happy flying!

---

## Changelog — beta v0.9

**New**
- **Automatic updates** (optional, asked at first launch): once a day at most SGM checks for a new version on GitHub, shows what's new and — if you click *Update now* — downloads it, verifies its SHA-256 fingerprint, replaces its files and restarts. `SGM_data` (settings, backups, profiles) is never touched, and the previous version is put back if anything goes wrong. *Help › Check for updates…* at any time; *Settings* to turn it on or off.

**Safety**
- *Restore everything* never removes or overwrites a GSX profile you edited after SGM installed it (GSX editor, by hand): it is left as it is and listed.
- Downloaded archives go to the Recycle Bin only from a fixed drive; on a USB stick or network drive (where Windows would delete them for good) they are kept.
- File changes are blocked while MSFS 2020 **or** MSFS 2024 is running; if SGM cannot tell, it asks.
- Backups are stored per scenery with their folder structure; archives are checked before anything is extracted; Undo keeps far fewer copies (renamed files are found by fingerprint, 500 MB cap).

**Improved**
- `.7z` / `.rar` archives tested with a real 7-Zip.
- French interface complete; resizable Folders and Guide windows.

**Updating**: delete the old SGM folder (keep `SGM_data`), unzip v0.9, run `SGM.exe`. From v0.9 on, SGM can update itself.

---

## Mots-clés (inchangés, + ajouts)

statics, static aircraft, parked aircraft, GSX, GSX Pro, GSX profile, Virtuali, FSDreamTeam, scenery, airport,
community folder, manager, tool, utility, MSFS 2024, MSFS 2020, toggle, AI traffic, freeware, Orbx, iniBuilds,
Drzewiecki, UK2000, undo, profiles, auto update
