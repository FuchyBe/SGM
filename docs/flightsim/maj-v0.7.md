# Mise à jour flightsim.to — beta v0.7

À recopier sur la page flightsim.to (en anglais). Fichier à publier : `SGM_beta_v0.7.zip`.
Titre de la version : **beta v0.7 — Statics for every developer + Restore original**

---

## Description (remplace la description actuelle)

**SGM — Statics & GSX Manager** is a free, portable Windows tool for **MSFS 2024** (and MSFS 2020) that lets you switch the **static aircraft** of your airport sceneries ON or OFF in one click, and manage your **GSX Pro profiles** — without digging through folders.

**Static aircraft**
- Finds every airport with optional statics in your Community folders and your own scenery folders (any depth).
- Recognises the methods used by the developers themselves — iniBuilds, Orbx, Drzewiecki Design, UK2000, Aerosoft, LimeSim, SimPixel, Burning Blue, JetStream, Homa Sim and many more: `.off`, `.disabled`, `.nostatic` versions (official Orbx / Drzewiecki method, compatible with the Orbx Central control panel), with/without-statics pairs, complete airport files, on/off variants.
- Keeps each developer's own naming, and always updates `layout.json` so MSFS really loads (or unloads) the file.
- **Never loads an airport twice.** Unclear cases are never switched: SGM marks them "To check" and opens the right folder so you can do it yourself.
- Switch one airport, or everything at once.

**GSX Pro profiles**
- Detects profiles shipped inside sceneries and installs them into the GSX folder in one click.
- FULL / LITE / VDGS versions: choose one, SGM remembers it.
- Shows airports without a GSX profile and searches flightsim.to for "ICAO GSX" in one click.
- Installs profiles straight from a downloaded archive (drag & drop, or detected in your Downloads folder).

**Safe by design**
- Backup before every change, and a record of the **original state** of each scenery: right-click › *Restore original state*, or *Help › Restore everything to original*.
- Blocked while the simulator is running.
- No installation, no internet connection, no data sent anywhere. 12 languages.

**Found a bug or have an idea?** Use *Help › Report a problem…* inside SGM: it can create a statics analysis report (file names only, no personal data) to attach to your GitHub issue.
🐞 https://github.com/FuchyBe/SGM/issues

---

## Changelog — beta v0.7

**Static aircraft**
- Many more developer methods recognised (from a real library of 2,000+ packages and the developers' own instructions): `.off` / `.disabled` files, "static" (singular) and "parked" files, identical twin files, `.nostatic` versions, `_static` / `_nostatic` pairs, complete airport files with statics, UK2000 `.staticq`.
- Orbx / Drzewiecki `.nostatic`: the official method is used (`.static` / `.nostatic` renaming + `layout.json` swap), the same as the Orbx Central control panel.
- An airport is never loaded twice; files not loaded by MSFS (absent from `layout.json`), model libraries and terrain flattens are left alone.
- Unclear cases are shown "To check" with a folder icon to do it manually.

**New**
- **GSX archives** — after installing a profile from your Downloads folder, SGM can delete the archive (ask / automatically / never). Recycle Bin, and never when something went wrong.
- **Interface** — one filter per column (Statics and GSX), wider columns that follow the window and can be resized.
- **Restore original state** — per scenery (right-click) or everything (Help menu), all or nothing.
- **Statics analysis report** (Help menu) — read-only, no personal data; offered when you report a problem.

**Fixes**
- SGM ≤ v0.6 could disable a complete airport file named `…-airport-statics.bgl` (e.g. Homa Sim), leaving the scenery without an airport. v0.7 shows "No version active" and re-enables only one version. **If you used an older version on such a scenery, open SGM v0.7 and switch it ON or OFF once.**

**Updating**: delete the old SGM folder (keep `SGM_data` if you want to keep your settings and backups), unzip v0.7, run `SGM.exe`.

---

## Mots-clés (inchangés, + ajouts)

statics, static aircraft, parked aircraft, GSX, GSX Pro, GSX profile, Virtuali, FSDreamTeam, scenery, airport,
community folder, manager, tool, utility, MSFS 2024, MSFS 2020, toggle, AI traffic, freeware, Orbx, iniBuilds,
Drzewiecki, UK2000
