# SGM — Statics & GSX Manager · beta v0.6

**Static aircraft and GSX profiles manager for Microsoft Flight Simulator 2024 and 2020**
by **Fabian Fuchs** · freeware · portable · 12 languages

*Version française : [README_FR.md](README_FR.md)*

---

## What it does

Many sceneries ship **static aircraft** parked on the stands. They look nice, but they take the parking spots that AI traffic could use. Developers often provide an optional file to turn them off, but you have to find it and rename it by hand, scenery by scenery.

SGM does it for you:

- **Detects** every scenery that contains static aircraft files, in your Community folders and in any folder you add.
- **Switches** statics ON or OFF per scenery, or for all displayed sceneries at once.
- **Detects the GSX profiles** delivered inside sceneries and copies them into GSX in one click, including sceneries that ship several versions (e.g. FULL / LITE).
- **Shows which airports have no GSX profile yet**, detects profiles you installed manually, and searches flightsim.to for the missing ones in one click.
- **Installs downloaded GSX profiles**: drop the archive on the window, or let SGM find it in your Downloads folder.
- **Flags new sceneries** installed since the last launch.

## Requirements

- Windows 10 or 11 (64-bit)
- Microsoft Flight Simulator 2024 and/or 2020 (Microsoft Store or Steam)
- GSX Pro (optional, only for the GSX profile features)

## Installation

There is nothing to install.

1. Unzip `SGM_beta_v0.6.zip` anywhere (tools folder, USB stick…).
2. Run `SGM.exe` from the `SGM` folder.

Keep the whole `SGM` folder together: `SGM.exe` needs the `_internal` folder next to it.

On first launch SGM creates a `SGM_data` folder next to `SGM.exe`, containing its settings and backups. If you move SGM, move the whole folder. If SGM sits in a write-protected folder (such as `Program Files`), the data is stored in `%APPDATA%\SGM` instead.

**Uninstall:** delete the `SGM` folder. Changes already made to your sceneries stay as they are, so switch them back first if needed.

## Quick start

1. **Close the simulator.**
2. Start SGM. Your Community folders are found automatically and scanned.
3. Use the switch on each row to turn the statics ON or OFF, or filter the list and use **All ON** / **All OFF**.
4. In the **GSX profile** column, click **Copy to GSX** or choose the version to activate.
5. Start the simulator.

The full user guide is in the app: **Help › User guide** (F1).

## Features

### Static aircraft
- Files are detected when their name contains `static`, `statics` or `parked`, at any depth inside the scenery. Model libraries (`modelLib…`) and terrain flattens are ignored.
- The methods used by developers are recognised (based on a real library of more than 2,000 packages):
  - **Renaming**: `xxx_statics.bgl` (ON) ↔ `xxx_statics.bgl.off`, `xxx_statics.off` or `.disabled` (OFF) — iniBuilds, Drzewiecki Design, Orbx, JetStream, UK2000, Burning Blue… SGM keeps the developer's own naming.
  - **Variants**: `statics_on.bgl` + `statics_off.bgl` next to an active `statics.bgl`. The chosen variant is copied onto `statics.bgl`. Also `xxx-airport-statics` / `xxx-airport-nostatics` next to the active `xxx-airport.bgl` (Homa Sim).
  - **No-statics version**: `xxx.bgl` + `xxx.bgl.nostatic` (Orbx, UK2000, Drzewiecki placements). The two files are swapped; `xxx.bgl.static` keeps the version with statics.
  - **With / without pair**: `xxx_static` + `xxx_nostatic` (iniBuilds), or a complete airport file `xxx-statics` that replaces `xxx`. Only one of the two is ever active, so the airport is never loaded twice.
- The package `layout.json` (and `total_package_size` in `manifest.json`) is updated automatically, like MSFSLayoutGenerator does. Without this, the simulator would ignore the change.
- Ambiguous cases are never changed automatically. They are shown in orange as **To check**.

### GSX profiles
- Profiles (`.ini` plus the matching `.py`) are detected anywhere inside the scenery. Readme and other files are ignored.
- **One profile**: Copy to GSX / ✓ Installed / Update.
- **Several versions**: one button per version. Green means active, red means not active, orange means the installed version cannot be identified. Activating a version removes the files of the other version from GSX. Your choice is remembered.
- A file is only removed from GSX if it is identical to the scenery's copy. A profile you edited by hand is never deleted.
- **Airports without a profile in the scenery**: SGM looks for a profile matching the ICAO code in the GSX folder.
  - **✓ Installed manually** means a profile you installed yourself was found.
  - The **flightsim.to ↗** button searches "ICAO GSX" on flightsim.to. In **Settings › GSX profile search**, choose a direct flightsim.to search or a web search limited to flightsim.to.
  - If another profile for the same airport is also installed, an orange warning is shown, because GSX could load the wrong one.
- The GSX destination folder is detected automatically and can be changed in **Folders**.

### Installing a downloaded GSX profile
- **Drop** the archive (`.zip`, `.7z`, `.rar`) or the `.ini`/`.py` files onto the SGM window, or click **Install GSX profile…**.
- SGM extracts only the profile files (`.ini` and matching `.py`), asks which version to install if there are several, shows the matching scenery and asks for confirmation before copying.
- At launch, SGM checks your **Downloads** folder for recent archives containing a GSX profile and offers to install them, once per archive. This can be turned off in **Settings**.
- Archives are extracted safely: nothing is written outside a temporary folder, other files are ignored.
- `.zip` works out of the box. `.7z` and `.rar` need **7-Zip** (7-zip.org).

### Folders and simulators
- Automatic detection of the Community folders from `UserCfg.opt`, Microsoft Store or Steam. For MSFS 2024, both `Community` and `Community2024` are scanned.
- Airport sceneries are listed even without statics or GSX profile (ICAO code detected from the title). Aircraft and liveries are ignored.
- Manual folders, searched up to 8 levels deep (for example *Sceneries › Europe › Belgium › scenery*).
- **MSFS 2024 / MSFS 2020 mode** (Settings › Simulator). Each simulator keeps its own folders, GSX settings and choices.

### Interface
- 12 languages: English, Français, Deutsch, Español, Italiano, Português, Nederlands, Polski, Русский, 中文, 日本語, العربية (right-to-left).
- Search (name, ICAO, developer), filters (ON, OFF, New, To check) and a **category** list: with statics, GSX profile in scenery, GSX installed manually, no GSX profile.
- Tooltips with the details of each file.
- Folder icon on each row to open the scenery folder.
- Help menu: user guide, disclaimer, licences, backups folder.

## Backups

Before every change, the modified files are copied to `SGM_data\backups`:
- one folder per scenery, keeping the 10 most recent backups;
- GSX files in `backups\_GSX`.

**Help › Open backups folder** opens it.

### Restore the original state

Before its very first change to a scenery, SGM records how it was in `SGM_data\origin` (statics files, `layout.json`, `manifest.json`). This record is never deleted by later backups. SGM also records every GSX profile it replaced, removed or added.

- **Right-click a scenery › Restore original state…** puts that scenery and its GSX profiles back as they were before SGM.
- **Help › Restore everything to original…** does it for every scenery and the GSX folder, for example before removing SGM.
- Restoring is all or nothing: if a file no longer matches (edited by hand), nothing is changed and the files to check are listed.
- If the developer has updated the scenery since, its files are already original: nothing is done.

## Updates of sceneries

A scenery update (for example through the Marketplace or an installer) may restore its original files. Just switch it again in SGM.

## Building from source

Requirements: Python 3.10 or newer.

1. Put `statics_manager.py`, `i18n.py`, `build_exe.bat`, both README files and the `licenses` folder together.
2. Run `build_exe.bat`. It installs PySide6 and PyInstaller, builds `dist\SGM\SGM.exe`, copies the licences and README files, and creates `dist\SGM_beta_v0.6.zip`.

To run without building: `pip install pyside6`, then `python statics_manager.py`.

## Report a problem or suggest an idea

Use **Help › Report a problem…** or **Help › Suggest an idea…** in SGM. It opens a pre-filled page in the public GitHub issue tracker (https://github.com/FuchyBe/SGM/issues, a free GitHub account is required).

The SGM version, the simulator and the Windows version are added automatically. No personal information is sent: please do not paste your e-mail address or full file paths containing your user name.

### Statics analysis report

**Help › Create a statics analysis report…** scans all your sceneries without changing anything and saves a `.json` file in `SGM_data\reports`. It lists the statics-like files found in each scenery (names inside the scenery, sizes, fingerprints, whether they are in `layout.json`, and how SGM understood them). It contains no personal path or user name. Attach it to a GitHub issue to help improve SGM's detection rules.

When you report a problem, SGM offers to create this report at the same time: drag the file into the GitHub page before submitting.

## Support the project

SGM is free. If it saves you time, you can support its development:
**[paypal.me/Fuchy](https://paypal.me/Fuchy)** (also available in the app: Help › Support the project, or the ♥ icon).

## Licences and credits

- **SGM** © 2026 Fabian Fuchs. Freeware: free to use and to redistribute unmodified, free of charge. Selling it is not allowed. See `licenses/LICENSE-SGM.txt`.
- **Qt for Python (PySide6, Shiboken6) and Qt** © The Qt Company Ltd. and contributors. Used unmodified under the **GNU Lesser General Public License v3** (`licenses/LGPL-3.0-only.txt`, which refers to `licenses/GPL-3.0-only.txt`).
  - These libraries are separate files in the `_internal` folder and can be replaced by a compatible version.
  - Source code: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://download.qt.io/official_releases/
- **Python** © Python Software Foundation, PSF License (`licenses/Python-PSF-LICENSE.txt`).
- Built with **PyInstaller**. Its bootloader is GPL-2.0 with an exception allowing distribution under any licence.

Details and exact versions: `licenses/THIRD-PARTY-NOTICES.txt` and **Help › Licences** in the app.

## Disclaimer

**SGM is free software provided "as is", without warranty of any kind**, express or implied, including fitness for a particular purpose. You use it at your own risk.

- The application **renames, copies and deletes files** inside your add-on packages and in the GSX profiles folder, and rewrites their `layout.json` / `manifest.json`. Backups are made before every change, but you should keep your own backup of important add-ons.
- The author cannot be held liable for any damage, data loss, or malfunction of the simulator, add-ons or GSX resulting from the use of this application.
- Scenery and profile files remain the property of their respective developers. Respect their licence (EULA): this tool only switches options the developer already provides.
- A scenery or GSX update may overwrite the changes made by this application.
- This project is **independent**. It is not affiliated with, endorsed or supported by Microsoft, Asobo Studio, FSDreamTeam / Virtuali, or any scenery developer.
- Microsoft Flight Simulator is a trademark of Microsoft Corporation. GSX is a product of FSDreamTeam / Virtuali. All other names and trademarks are the property of their respective owners.

## Version history

**beta v0.6**
- Airport sceneries are listed even without statics or GSX profile (ICAO code detection).
- Detection of GSX profiles installed manually, and warning when two profiles exist for the same airport.
- One-click flightsim.to search for missing profiles ("ICAO GSX"), with a choice of search mode.
- Category filter: with statics, GSX profile in scenery, installed manually, no GSX profile.
- Install GSX profiles from downloaded archives: drag & drop, Install button, Downloads folder detection at launch (.zip; .7z/.rar with 7-Zip).
- Aircraft and liveries are skipped during the scan (faster).
- Statics analysis report (Help menu): read-only scan to help improve detection rules.
- Many more statics methods recognised (`.off`, `.disabled`, `.nostatic`, static/nostatic pairs, complete airport files), from a real library of 2,000+ packages. Problem report can include the statics analysis report.
- Restore original state: right-click a scenery, or Help › Restore everything to original. SGM records each scenery and GSX profile as it was before its first change.
- Statics safety: a statics file with a different name that matches neither on/off variant is never overwritten: it is shown as "To check", with a folder icon to open the folder of the statics file and do it manually.
- Help › Report a problem / Suggest an idea (pre-filled GitHub issue).

**beta v0.5**
- First public beta.
- Static aircraft: renaming and variant methods, automatic `layout.json` update.
- GSX profiles: detection, copy, multi-version management with remembered choice.
- MSFS 2024 (Community + Community2024) and MSFS 2020 modes with separate memory.
- Portable app, backups, 12 interface languages, user guide, licences.

---

SGM — Statics & GSX Manager © 2026 Fabian Fuchs · distributed free of charge.
