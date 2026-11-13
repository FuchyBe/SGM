# SGM — Statics & GSX Manager · beta v0.6

**Gestionnaire des avions statiques et des profils GSX pour Microsoft Flight Simulator 2024 et 2020**
par **Fabian Fuchs** · gratuit · portable · 12 langues

*English version: [README.md](README.md)*

---

## À quoi sert-il ?

Beaucoup de scènes livrent des **avions statiques** garés sur les parkings. C'est joli, mais ils occupent les places que le trafic IA pourrait utiliser. Les développeurs prévoient souvent un fichier optionnel pour les retirer, mais il faut le trouver et le renommer à la main, scène par scène.

SGM le fait pour toi :

- **Détecte** toutes les scènes qui contiennent des fichiers d'avions statiques, dans tes dossiers Community et dans les dossiers que tu ajoutes.
- **Active ou désactive** les statics scène par scène, ou pour toutes les scènes affichées d'un coup.
- **Détecte les profils GSX** livrés dans les scènes et les copie dans GSX en un clic, y compris quand la scène propose plusieurs versions (par exemple FULL / LITE).
- **Montre les aéroports qui n'ont pas encore de profil GSX**, détecte les profils que tu as installés à la main, et cherche ceux qui manquent sur flightsim.to en un clic.
- **Installe les profils GSX téléchargés** : dépose l'archive sur la fenêtre, ou laisse SGM la trouver dans tes Téléchargements.
- **Signale les nouvelles scènes** installées depuis le dernier lancement.

## Configuration requise

- Windows 10 ou 11 (64 bits)
- Microsoft Flight Simulator 2024 et/ou 2020 (Microsoft Store ou Steam)
- GSX Pro (facultatif, seulement pour les fonctions de profils GSX)

## Installation

Il n'y a rien à installer.

1. Décompresse `SGM_beta_v0.6.zip` où tu veux (dossier d'outils, clé USB…).
2. Lance `SGM.exe`, dans le dossier `SGM`.

Garde tout le dossier `SGM` ensemble : `SGM.exe` a besoin du dossier `_internal` placé à côté de lui.

Au premier lancement, SGM crée un dossier `SGM_data` à côté de `SGM.exe`, qui contient ses réglages et ses sauvegardes. Si tu déplaces SGM, déplace tout le dossier. Si SGM se trouve dans un dossier protégé en écriture (comme `Program Files`), les données sont rangées dans `%APPDATA%\SGM`.

**Désinstallation :** supprime le dossier `SGM`. Les modifications déjà faites dans tes scènes restent en place : rebascule-les d'abord si besoin.

## Démarrage rapide

1. **Ferme le simulateur.**
2. Lance SGM. Tes dossiers Community sont trouvés et analysés automatiquement.
3. Utilise l'interrupteur de chaque ligne pour passer les statics en ON ou OFF, ou filtre la liste et utilise **Tout ON** / **Tout OFF**.
4. Dans la colonne **Profil GSX**, clique sur **Copier dans GSX** ou choisis la version à activer.
5. Lance le simulateur.

Le guide complet est dans l'application : **Aide › Guide d'utilisation** (F1).

## Fonctions

### Avions statiques
- Les fichiers sont détectés quand leur nom contient `statics` et se termine par `.bgl` ou `.bgl.off`, à n'importe quelle profondeur dans la scène.
- Deux méthodes sont gérées :
  - **Renommage** : `xxx_statics.bgl` (ON) ↔ `xxx_statics.bgl.off` (OFF).
  - **Variantes** : `statics_on.bgl` + `statics_off.bgl` à côté d'un `statics.bgl` actif. La variante choisie est copiée sur `statics.bgl`.
- Le `layout.json` de la scène (et le `total_package_size` du `manifest.json`) est mis à jour automatiquement, comme le fait MSFSLayoutGenerator. Sans cela, le simulateur ignorerait le changement.
- Les cas ambigus ne sont jamais modifiés automatiquement. Ils apparaissent en orange, « À vérifier ».

### Profils GSX
- Les profils (`.ini` et le `.py` du même nom) sont détectés n'importe où dans la scène. Les readme et autres fichiers sont ignorés.
- **Un seul profil** : Copier dans GSX / ✓ Installé / Mettre à jour.
- **Plusieurs versions** : un bouton par version. Vert = active, rouge = non active, orange = impossible d'identifier la version installée. Activer une version retire de GSX les fichiers de l'autre. Ton choix est mémorisé.
- Un fichier n'est retiré de GSX que s'il est identique à celui de la scène. Un profil que tu as modifié à la main n'est jamais supprimé.
- **Aéroports sans profil dans la scène** : SGM cherche dans le dossier GSX un profil correspondant au code OACI.
  - **✓ Installé à la main** signifie qu'un profil que tu as installé toi-même a été trouvé.
  - Le bouton **flightsim.to ↗** lance la recherche « OACI GSX » sur flightsim.to. Dans **Paramètres › Recherche de profils GSX**, choisis une recherche directe sur flightsim.to ou une recherche web limitée à flightsim.to.
  - Si un autre profil pour le même aéroport est aussi installé, un avertissement orange s'affiche, car GSX pourrait charger le mauvais.
- Le dossier de destination GSX est détecté automatiquement et peut être changé dans **Dossiers**.

### Installer un profil GSX téléchargé
- **Dépose** l'archive (`.zip`, `.7z`, `.rar`) ou les fichiers `.ini`/`.py` sur la fenêtre de SGM, ou clique sur **Installer un profil GSX…**.
- SGM n'extrait que les fichiers du profil (`.ini` et `.py` du même nom), demande quelle version installer s'il y en a plusieurs, indique la scène correspondante et demande confirmation avant de copier.
- Au lancement, SGM vérifie ton dossier **Téléchargements** à la recherche d'archives récentes contenant un profil GSX et propose de les installer, une seule fois par archive. Désactivable dans **Paramètres**.
- Les archives sont extraites de façon sûre : rien n'est écrit hors d'un dossier temporaire, les autres fichiers sont ignorés.
- Le `.zip` fonctionne directement. Les `.7z` et `.rar` nécessitent **7-Zip** (7-zip.org).

### Dossiers et simulateurs
- Détection automatique des dossiers Community à partir de `UserCfg.opt`, Microsoft Store ou Steam. Pour MSFS 2024, `Community` et `Community2024` sont analysés.
- Les scènes d'aéroport sont listées même sans statics ni profil GSX (code OACI détecté dans le titre). Les avions et livrées sont ignorés.
- Dossiers ajoutés à la main, fouillés jusqu'à 8 niveaux de profondeur (par exemple *Scènes › Europe › Belgique › scène*).
- **Mode MSFS 2024 / MSFS 2020** (Paramètres › Simulateur). Chaque simulateur garde ses propres dossiers, réglages GSX et choix.

### Interface
- 12 langues : English, Français, Deutsch, Español, Italiano, Português, Nederlands, Polski, Русский, 中文, 日本語, العربية (de droite à gauche).
- Recherche (nom, OACI, éditeur), filtres (ON, OFF, Nouvelles, À vérifier) et liste des **catégories** : avec statics, profil GSX dans la scène, GSX installé à la main, sans profil GSX.
- Infobulles détaillant chaque fichier.
- Icône de dossier sur chaque ligne pour ouvrir le dossier de la scène.
- Menu Aide : guide d'utilisation, avertissement, licences, dossier des sauvegardes.

## Sauvegardes

Avant chaque modification, les fichiers concernés sont copiés dans `SGM_data\backups` :
- un dossier par scène, avec les 10 sauvegardes les plus récentes ;
- les fichiers GSX dans `backups\_GSX`.

**Aide › Ouvrir le dossier des sauvegardes** l'ouvre.

## Mises à jour des scènes

Une mise à jour de scène (par le Marketplace ou un installateur) peut remettre ses fichiers d'origine. Il suffit de la rebasculer dans SGM.

## Compiler depuis les sources

Prérequis : Python 3.10 ou plus récent.

1. Place ensemble `statics_manager.py`, `i18n.py`, `build_exe.bat`, les deux README et le dossier `licenses`.
2. Lance `build_exe.bat`. Il installe PySide6 et PyInstaller, crée `dist\SGM\SGM.exe`, y copie les licences et les README, puis crée `dist\SGM_beta_v0.6.zip`.

Pour lancer sans compiler : `pip install pyside6`, puis `python statics_manager.py`.

## Signaler un problème ou proposer une idée

Utilise **Aide › Signaler un problème…** ou **Aide › Proposer une idée…** dans SGM. Une page préremplie s'ouvre sur le suivi public de GitHub (https://github.com/FuchyBe/SGM/issues, un compte GitHub gratuit est nécessaire).

La version de SGM, le simulateur et la version de Windows sont ajoutés automatiquement. Aucune donnée personnelle n'est envoyée : ne colle ni ton adresse e-mail, ni des chemins complets contenant ton nom d'utilisateur.

## Soutenir le projet

SGM est gratuit. S'il te fait gagner du temps, tu peux soutenir son développement :
**[paypal.me/Fuchy](https://paypal.me/Fuchy)** (aussi accessible dans l'application : Aide › Soutenir le projet, ou l'icône ♥).

## Licences et crédits

- **SGM** © 2026 Fabian Fuchs. Logiciel gratuit : utilisation et redistribution libres et gratuites, sans modification. La vente est interdite. Voir `licenses/LICENSE-SGM.txt`.
- **Qt for Python (PySide6, Shiboken6) et Qt** © The Qt Company Ltd. et contributeurs. Utilisés sans modification sous la **GNU Lesser General Public License v3** (`licenses/LGPL-3.0-only.txt`, qui renvoie à `licenses/GPL-3.0-only.txt`).
  - Ces bibliothèques sont des fichiers séparés, dans le dossier `_internal`, et peuvent être remplacées par une version compatible.
  - Code source : https://code.qt.io/cgit/pyside/pyside-setup.git/ et https://download.qt.io/official_releases/
- **Python** © Python Software Foundation, licence PSF (`licenses/Python-PSF-LICENSE.txt`).
- Compilé avec **PyInstaller**. Son chargeur est sous GPL-2.0 avec une exception qui autorise la distribution sous n'importe quelle licence.

Détails et versions exactes : `licenses/THIRD-PARTY-NOTICES.txt` et **Aide › Licences** dans l'application. Les textes de licence officiels sont en anglais, seule version qui fait foi.

## Avertissement

**SGM est un logiciel gratuit fourni « tel quel », sans aucune garantie**, expresse ou implicite, y compris d'adéquation à un usage particulier. Tu l'utilises à tes propres risques.

- L'application **renomme, copie et supprime des fichiers** dans tes add-ons et dans le dossier des profils GSX, et réécrit leurs `layout.json` / `manifest.json`. Une sauvegarde est faite avant chaque modification, mais garde aussi ta propre sauvegarde de tes add-ons importants.
- L'auteur ne peut être tenu responsable d'aucun dommage, perte de données ou dysfonctionnement du simulateur, des add-ons ou de GSX résultant de l'utilisation de cette application.
- Les fichiers des scènes et des profils restent la propriété de leurs développeurs. Respecte leur licence (EULA) : cet outil ne fait que basculer des options déjà prévues par le développeur.
- Une mise à jour d'une scène ou de GSX peut écraser les modifications faites par cette application.
- Ce projet est **indépendant**. Il n'est ni affilié, ni approuvé, ni soutenu par Microsoft, Asobo Studio, FSDreamTeam / Virtuali ou un développeur de scènes.
- Microsoft Flight Simulator est une marque de Microsoft Corporation. GSX est un produit de FSDreamTeam / Virtuali. Les autres noms et marques appartiennent à leurs propriétaires.

## Historique des versions

**beta v0.6**
- Les scènes d'aéroport sont listées même sans statics ni profil GSX (détection du code OACI).
- Détection des profils GSX installés à la main, et avertissement quand deux profils existent pour le même aéroport.
- Recherche sur flightsim.to en un clic pour les profils manquants (« OACI GSX »), avec choix du mode de recherche.
- Filtre par catégorie : avec statics, profil GSX dans la scène, installé à la main, sans profil GSX.
- Installation de profils GSX depuis une archive téléchargée : glisser-déposer, bouton Installer, détection dans Téléchargements au lancement (.zip ; .7z/.rar avec 7-Zip).
- Les avions et livrées sont ignorés pendant l'analyse (plus rapide).
- Sécurité des statics : un fichier statics au nom différent qui ne correspond à aucune variante on/off n'est jamais écrasé (affiché « à vérifier »).
- Aide › Signaler un problème / Proposer une idée (issue GitHub préremplie).

**beta v0.5**
- Première beta publique.
- Avions statiques : méthodes par renommage et par variantes, mise à jour automatique de `layout.json`.
- Profils GSX : détection, copie, gestion de plusieurs versions avec choix mémorisé.
- Modes MSFS 2024 (Community + Community2024) et MSFS 2020, avec mémoire séparée.
- Application portable, sauvegardes, interface en 12 langues, guide d'utilisation, licences.

---

SGM — Statics & GSX Manager © 2026 Fabian Fuchs · distribué gratuitement.
