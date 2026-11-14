# Mise à jour flightsim.to — beta v0.8

À recopier sur la page flightsim.to (en anglais). Fichier à publier : `SGM_beta_v0.8.zip`
(produit par `build_exe.bat`, ou dossier `SGM` de la compilation GitHub zippé).
Titre de la version : **beta v0.8 — Undo, statics profiles & smarter layout**

---

## Short description

Switch airport static aircraft ON/OFF in one click — the developers' own methods (Orbx, iniBuilds, Drzewiecki, UK2000…), never an airport loaded twice — plus GSX Pro profiles installed by drag & drop or straight from your Downloads. Undo, statics profiles, restore original. Free & portable.

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
- Blocked while the simulator is running.
- No installation, no internet connection, no data sent anywhere. 12 languages.

**Found a bug or have an idea?** *Help › Report a problem…* opens a small form: SGM prepares your text, a statics analysis report and its log (no user name, no personal path) and opens the GitHub page — nothing is sent until you click Submit.
🐞 https://github.com/FuchyBe/SGM/issues

If SGM saves you some time, you can buy me a coffee ☕ — https://paypal.me/Fuchy — thank you, and happy flying!

---

## Changelog — beta v0.8

**New**
- **Undo** — button next to *Install GSX profile…* or **Ctrl+Z**: undo a switch, All ON / All OFF, a GSX profile copied or installed, or a restore. The last 10 actions are kept. Files go back exactly as they were; if one was changed since, nothing is touched.
- **Statics profiles** — *Profiles › Save current state as a profile…*, then apply it later in one click. Only the sceneries that differ are switched, sceneries to check are never touched, and applying a profile can be undone.
- **Scan also checks your download folders** for GSX profile archives, even ones already proposed (except those already in GSX). Download folders are set in *Folders*: Windows Downloads by default, change it or add others.
- **Report a problem / Suggest an idea window** — your text goes straight into the GitHub page, with the analysis report and the log in one `.zip`, and an exact preview of what is shared.
- **Log** — `SGM_data\logs`, no user name; *Help › Open log folder*.

**Improved**
- **Columns fit their text** on one line, scenery names get all the remaining space. Drag the header lines to set them yourself (remembered); double-click a line to go back to automatic.
- **All OFF / All ON** now sit in the Statics column header and only switch simple cases: sceneries "To check" are left untouched (the confirmation tells you how many).

**Fixes**
- The **flightsim.to** button now opens a web search limited to flightsim.to: the site's own search ignored the ICAO code when opened from a link. The search-mode setting is removed.
- Folders window: no more leftover rows after a change.

**Updating**: delete the old SGM folder (keep `SGM_data` if you want to keep your settings, backups and profiles), unzip v0.8, run `SGM.exe`.

---

## Mots-clés (inchangés, + ajouts)

statics, static aircraft, parked aircraft, GSX, GSX Pro, GSX profile, Virtuali, FSDreamTeam, scenery, airport,
community folder, manager, tool, utility, MSFS 2024, MSFS 2020, toggle, AI traffic, freeware, Orbx, iniBuilds,
Drzewiecki, UK2000, undo, profiles
