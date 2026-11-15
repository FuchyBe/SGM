# SGM — Statics & GSX Manager · beta v0.8

<p align="center"><img src="assets/SGM-256.png" width="128" alt="SGM"></p>

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

1. Décompresse `SGM_beta_v0.8.zip` où tu veux (dossier d'outils, clé USB…).
2. Lance `SGM.exe`, dans le dossier `SGM`.

Garde tout le dossier `SGM` ensemble : `SGM.exe` a besoin du dossier `_internal` placé à côté de lui.

Au premier lancement, SGM crée un dossier `SGM_data` à côté de `SGM.exe`, qui contient ses réglages et ses sauvegardes. Si tu déplaces SGM, déplace tout le dossier. Si SGM se trouve dans un dossier protégé en écriture (comme `Program Files`), les données sont rangées dans `%APPDATA%\SGM`.

**Désinstallation :** supprime le dossier `SGM`. Les modifications déjà faites dans tes scènes restent en place : rebascule-les d'abord si besoin.

## Démarrage rapide

1. **Ferme le simulateur.**
2. Lance SGM. Tes dossiers Community sont trouvés et analysés automatiquement.
3. Utilise l'interrupteur de chaque ligne pour passer les statics en ON ou OFF, ou filtre la liste et utilise **Tout OFF** / **Tout ON** dans l'en-tête de la colonne Statics (cas simples uniquement : les scènes à vérifier ne sont jamais basculées en bloc).
4. Dans la colonne **Profil GSX**, clique sur **Copier dans GSX** ou choisis la version à activer.
5. Lance le simulateur.

Le guide complet est dans l'application : **Aide › Guide d'utilisation** (F1).

## Fonctions

### Avions statiques
- **Profils** (barre d'outils) : enregistre l'état ON/OFF de tes scènes sous un nom et applique-le plus tard d'un clic ; seules les scènes qui diffèrent sont basculées, les scènes à vérifier ne sont jamais touchées, et l'application d'un profil s'annule.
- Les fichiers sont détectés quand leur nom contient `static`, `statics` ou `parked`, à n'importe quelle profondeur dans la scène. Les bibliothèques de modèles (`modelLib…`) et les aplanissements de terrain sont ignorés.
- Les méthodes des éditeurs sont reconnues (à partir d'une vraie bibliothèque de plus de 2 000 paquets) :
  - **Renommage** : `xxx_statics.bgl` (ON) ↔ `xxx_statics.bgl.off`, `xxx_statics.off` ou `.disabled` (OFF) — iniBuilds, Drzewiecki Design, Orbx, JetStream, UK2000, Burning Blue… SGM garde la convention de l'éditeur.
  - **Variantes** : `statics_on.bgl` + `statics_off.bgl` à côté d'un `statics.bgl` actif. La variante choisie est copiée sur `statics.bgl`. Aussi `xxx-airport-statics` / `xxx-airport-nostatics` à côté du `xxx-airport.bgl` actif (Homa Sim).
  - **Version sans statics** : `xxx.bgl` + `xxx.bgl.nostatic` (Orbx, Drzewiecki, UK2000). La méthode officielle de l'éditeur, identique au panneau Orbx Central : OFF renomme `xxx.bgl` → `xxx.bgl.static` et `xxx.bgl.nostatic` → `xxx.bgl`, et échange `layout.json` avec `layout.json.nostatic` s'il existe ; ON fait l'inverse. Un `xxx.bgl.nostatic` seul (Drzewiecki `XXXX_PLC.bgl.nostatic`) est simplement renommé en `.bgl`.
  - **Version avec statics** : `xxx.bgl` (sans statics) + `xxx.bgl.staticq` (UK2000). ON sauvegarde `xxx.bgl` en `xxx.bgl.bak` et copie `xxx.bgl.staticq` sur `xxx.bgl` ; OFF remet l'original.
  - **`.bgl.disabled`** (iniBuilds) : ON le copie en `.bgl` (le `.disabled` reste), OFF supprime la copie.
  - **Paire avec / sans** : `xxx_static` + `xxx_nostatic` (iniBuilds), ou un fichier d'aéroport complet `xxx-statics` qui remplace `xxx`. Un seul des deux est actif : l'aéroport n'est jamais chargé deux fois.
- Le `layout.json` de la scène (et le `total_package_size` du `manifest.json`) est mis à jour automatiquement, comme le fait MSFSLayoutGenerator. Sans cela, le simulateur ignorerait le changement.
- Les cas ambigus ne sont jamais modifiés automatiquement. Ils apparaissent en orange, « À vérifier ».

### Profils GSX
- Les profils (`.ini` et le `.py` du même nom) sont détectés n'importe où dans la scène. Les readme et autres fichiers sont ignorés.
- **Un seul profil** : Copier dans GSX / ✓ Installé / Mettre à jour.
- **Plusieurs versions** : un bouton par version. Vert = active, rouge = non active, orange = impossible d'identifier la version installée. Activer une version retire de GSX les fichiers de l'autre. Ton choix est mémorisé.
- Un fichier n'est retiré de GSX que s'il est identique à celui de la scène. Un profil que tu as modifié à la main n'est jamais supprimé.
- **Aéroports sans profil dans la scène** : SGM cherche dans le dossier GSX un profil correspondant au code OACI.
  - **✓ Installé à la main** signifie qu'un profil que tu as installé toi-même a été trouvé.
  - Le bouton **flightsim.to ↗** ouvre une recherche web « OACI GSX » limitée à flightsim.to.
  - Si un autre profil pour le même aéroport est aussi installé, un avertissement orange s'affiche, car GSX pourrait charger le mauvais.
- Le dossier de destination GSX est détecté automatiquement et peut être changé dans **Dossiers**.

### Installer un profil GSX téléchargé
- **Dépose** l'archive (`.zip`, `.7z`, `.rar`) ou les fichiers `.ini`/`.py` sur la fenêtre de SGM, ou clique sur **Installer un profil GSX…**.
- SGM n'extrait que les fichiers du profil (`.ini` et `.py` du même nom), demande quelle version installer s'il y en a plusieurs, indique la scène correspondante et demande confirmation avant de copier.
- Au lancement, SGM vérifie tes **dossiers de téléchargement** à la recherche d'archives récentes contenant un profil GSX et propose de les installer, une seule fois par archive (désactivable dans **Paramètres**). **Analyser** les revérifie à chaque fois, sans les archives dont les profils sont déjà dans GSX.
- Les dossiers de téléchargement se règlent dans **Dossiers** : **Téléchargements** de Windows par défaut ; change-le ou ajoute-en d'autres.
- Après une installation depuis Téléchargements, SGM peut retirer l'archive (**Paramètres › Après installation depuis Téléchargements** : Demander / Supprimer automatiquement / Ne jamais supprimer). Les archives vont dans la Corbeille ; une archive dont l'installation a posé problème n'est jamais supprimée (alerte), ni une archive située hors de Téléchargements.
- Les archives sont extraites de façon sûre : rien n'est écrit hors d'un dossier temporaire, les autres fichiers sont ignorés.
- Le `.zip` fonctionne directement. Les `.7z` et `.rar` nécessitent **7-Zip** (7-zip.org).

### Dossiers et simulateurs
- Détection automatique des dossiers Community à partir de `UserCfg.opt`, Microsoft Store ou Steam. Pour MSFS 2024, `Community` et `Community2024` sont analysés.
- Les scènes d'aéroport sont listées même sans statics ni profil GSX (code OACI détecté dans le titre). Les avions et livrées sont ignorés.
- Dossiers ajoutés à la main, fouillés jusqu'à 8 niveaux de profondeur (par exemple *Scènes › Europe › Belgique › scène*).
- **Mode MSFS 2024 / MSFS 2020** (Paramètres › Simulateur). Chaque simulateur garde ses propres dossiers, réglages GSX et choix.

### Interface
- 12 langues : English, Français, Deutsch, Español, Italiano, Português, Nederlands, Polski, Русский, 中文, 日本語, العربية (de droite à gauche).
- Recherche (nom, OACI, éditeur), bouton **Nouvelles**, et un **filtre par colonne** dans les en-têtes, avec la même logique : Statics (Toutes, ON, OFF, À vérifier, Sans statics) et Profil GSX (Tous, Installé, À installer, Installé à la main, Sans profil, À vérifier).
- Les colonnes Statics et GSX s'ajustent automatiquement à leur texte (une ligne) et laissent toute la place restante aux noms de scènes. Tire les traits entre les en-têtes pour les régler toi-même (réglage mémorisé) ; double-clic sur un trait pour revenir à l'ajustement automatique.
- Infobulles détaillant chaque fichier.
- Icône de dossier sur chaque ligne pour ouvrir le dossier de la scène.
- Menu Aide : guide d'utilisation, avertissement, licences, dossier des sauvegardes.

## Sauvegardes

**Annuler** (bouton à côté de *Installer un profil GSX…*, ou **Ctrl+Z**) défait la dernière action — une bascule, Tout ON / Tout OFF en entier, un profil GSX copié ou installé, une restauration — et se réutilise pour remonter plus loin (10 actions gardées). Les fichiers reviennent exactement comme avant ; si l'un d'eux a changé depuis, rien n'est modifié.

Avant chaque modification, les fichiers concernés sont copiés dans `SGM_data\backups` :
- un dossier par scène, avec les 10 sauvegardes les plus récentes ;
- les fichiers GSX dans `backups\_GSX`.

**Aide › Ouvrir le dossier des sauvegardes** l'ouvre.

### Restaurer l'état d'origine

Avant sa toute première modification d'une scène, SGM enregistre son état dans `SGM_data\origin` (fichiers statics, `layout.json`, `manifest.json`). Cet enregistrement n'est jamais effacé par les sauvegardes suivantes. SGM note aussi chaque profil GSX qu'il remplace, retire ou ajoute.

- **Clic droit sur une scène › Restaurer l'état d'origine…** remet cette scène et ses profils GSX comme avant SGM.
- **Aide › Tout restaurer à l'origine…** le fait pour toutes les scènes et le dossier GSX, par exemple avant de supprimer SGM.
- La restauration est tout ou rien : si un fichier ne correspond plus (modifié à la main), rien n'est changé et les fichiers à vérifier sont listés.
- Si l'éditeur a mis la scène à jour entre-temps, ses fichiers sont déjà d'origine : rien n'est fait.

## Mises à jour de SGM

Au premier lancement, SGM demande s'il peut vérifier l'existence d'une nouvelle version. Si tu acceptes, une fois par jour au plus, il demande à GitHub (github.com/FuchyBe/SGM) le numéro de la dernière version : c'est la seule connexion Internet de SGM, rien d'autre n'est envoyé. Quand une nouvelle version existe, **Mettre à jour** la télécharge, vérifie son empreinte SHA-256 publiée, ferme SGM, remplace ses fichiers et le relance — `SGM_data` (réglages, sauvegardes, profils) n'est jamais touché, et l'ancienne version est remise en cas de problème. **Aide › Rechercher une mise à jour…** vérifie à tout moment ; **Paramètres › Rechercher les mises à jour au lancement** l'active ou la désactive.

## Mises à jour des scènes

Une mise à jour de scène (par le Marketplace ou un installateur) peut remettre ses fichiers d'origine. Il suffit de la rebasculer dans SGM.

## Compiler depuis les sources

Prérequis : Python 3.10 ou plus récent.

1. Place ensemble `statics_manager.py`, `i18n.py`, `build_exe.bat`, les deux README et le dossier `licenses`.
2. Lance `build_exe.bat`. Il installe PySide6 et PyInstaller, crée `dist\SGM\SGM.exe`, y copie les licences et les README, puis crée `dist\SGM_beta_v0.8.zip`.

Pour lancer sans compiler : `pip install pyside6`, puis `python statics_manager.py`.

## Signaler un problème ou proposer une idée

Utilise **Aide › Signaler un problème…** ou **Aide › Proposer une idée…** dans SGM. Une petite fenêtre demande un titre, ce qui s'est passé (ou ton idée), la scène concernée et le message affiché par SGM. Deux cases ajoutent un rapport d'analyse des statics et le journal de SGM (cochées pour un problème) ; **Voir ce qui sera partagé** montre le texte et les fichiers exacts.

**Préparer et ouvrir GitHub** crée un `.zip` dans `SGM_data\reports`, ouvre son dossier et le suivi public de GitHub (https://github.com/FuchyBe/SGM/issues, un compte GitHub gratuit est nécessaire) avec ton texte déjà rempli. Glisse le `.zip` dans la page, vérifie, puis clique sur **Submit** : rien n'est envoyé avant.

La version de SGM, le simulateur et la version de Windows sont ajoutés automatiquement. Aucune donnée personnelle n'est envoyée : ne colle ni ton adresse e-mail, ni des chemins complets contenant ton nom d'utilisateur.

### Rapport d'analyse des statics

**Aide › Créer un rapport d'analyse des statics…** parcourt toutes tes scènes sans rien modifier et enregistre un fichier `.json` dans `SGM_data\reports`. Il liste les fichiers de type statics trouvés dans chaque scène (noms à l'intérieur de la scène, tailles, empreintes, présence dans `layout.json`, interprétation de SGM). Il ne contient aucun chemin personnel ni nom d'utilisateur. Joins-le à une issue GitHub pour aider à améliorer les règles de détection de SGM.

### Journal

SGM note ce qu'il fait (lancement, analyses, chaque bascule avec les fichiers renommés ou copiés, installations GSX, erreurs) dans `SGM_data\logs\sgm.log`. Ton dossier personnel est remplacé par `~` : aucun nom d'utilisateur. Il est limité à 5 fichiers de 1 Mo. **Aide › Ouvrir le dossier du journal** l'ouvre.


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

**Prochaine version (en développement)**
- **Sécurité** : « Tout restaurer » ne supprime ni n'écrase jamais un profil GSX que tu as modifié après son installation par SGM ; les archives ne vont à la Corbeille que depuis un disque fixe (gardées sur clé USB / disque réseau au lieu d'être effacées définitivement) ; modifications bloquées si MSFS 2020 **ou** MSFS 2024 tourne, et SGM demande s'il ne peut pas le savoir.
- **Mise à jour automatique** (optionnelle, demandée au premier lancement) : vérifie GitHub une fois par jour au plus, télécharge, vérifie le SHA-256 et relance ; `SGM_data` gardé, ancienne version remise en cas d'échec.

**beta v0.8**
- **Annuler** (bouton ou Ctrl+Z, 10 actions gardées) : une bascule, Tout ON/OFF, un profil GSX, une restauration — fichiers remis exactement, refus si un fichier a changé depuis.
- **Profils de statics** : enregistre l'état ON/OFF de tes scènes sous un nom (« Trafic IA dense », « Vols photo ») et applique-le d'un clic (cas simples uniquement, annulable).
- **Colonnes ajustées à leur texte** (une ligne), les noms de scènes prennent le reste ; réglage à la main mémorisé, double-clic pour revenir à l'automatique.
- **Tout OFF / Tout ON** déplacés dans l'en-tête de la colonne Statics ; cas simples uniquement, les scènes à vérifier ne sont pas touchées.
- **Analyser vérifie aussi tes dossiers de téléchargement** (archives de profils GSX) ; dossiers modifiables et ajoutables dans **Dossiers**.
- **Fenêtre Signaler un problème / Proposer une idée** : ton texte arrive directement dans la page GitHub, rapport et journal dans un seul `.zip`, aperçu exact de ce qui est partagé.
- **Journal** (`SGM_data\logs`, sans nom d'utilisateur), joint aux signalements de bug ; Aide › Ouvrir le dossier du journal.
- **Bouton flightsim.to** : recherche web limitée à flightsim.to (la recherche du site ignorait l'OACI depuis un lien) ; le réglage de recherche est retiré.

**beta v0.7**
- **Statics : beaucoup plus de méthodes d'éditeurs reconnues**, à partir d'une vraie bibliothèque de plus de 2 000 paquets et des instructions des éditeurs : `.off`, `.disabled`, fichiers « static » au singulier et « parked », doubles identiques, versions `.nostatic` (méthode officielle Orbx / Drzewiecki, compatible avec le panneau Orbx Central, échange de `layout.json` compris), paires `_static` / `_nostatic`, fichiers d'aéroport complet avec statics, UK2000 `.staticq`. SGM garde la convention de chaque éditeur.
- **Sécurité** : un aéroport n'est jamais chargé deux fois ; les cas peu clairs ne sont jamais basculés (« À vérifier » + icône dossier pour le faire à la main) ; un `.bgl` absent de `layout.json` n'est jamais touché ; bibliothèques de modèles et aplanissements ignorés.
- **Correction** : SGM ≤ v0.6 pouvait désactiver un fichier d'aéroport complet nommé `…-airport-statics.bgl` (Homa Sim), laissant la scène sans aéroport. SGM affiche maintenant « Aucune version active » et n'en réactive qu'une.
- **Restaurer l'état d'origine** : clic droit sur une scène › Restaurer l'état d'origine…, ou Aide › Tout restaurer à l'origine. SGM enregistre chaque scène et profil GSX avant sa première modification ; restauration tout ou rien.
- **Nouvelle icône** (application, fenêtre et barre des tâches).
- **Archives GSX** : après une installation depuis Téléchargements, demander / supprimer automatiquement / ne jamais supprimer l'archive (Corbeille) ; jamais en cas d'erreur.
- **Interface** : un filtre par colonne (Statics et GSX, même logique), colonnes Statics et GSX plus larges qui suivent la taille de la fenêtre et se règlent à la main.
- **Rapport d'analyse des statics** (menu Aide) : analyse en lecture seule, sans donnée personnelle, pour améliorer les règles. Aide › Signaler un problème propose de le créer et de le joindre.

**beta v0.6**
- Les scènes d'aéroport sont listées même sans statics ni profil GSX (détection du code OACI).
- Détection des profils GSX installés à la main, et avertissement quand deux profils existent pour le même aéroport.
- Recherche sur flightsim.to en un clic pour les profils manquants (« OACI GSX »), avec choix du mode de recherche.
- Filtre par catégorie : avec statics, profil GSX dans la scène, installé à la main, sans profil GSX.
- Installation de profils GSX depuis une archive téléchargée : glisser-déposer, bouton Installer, détection dans Téléchargements au lancement (.zip ; .7z/.rar avec 7-Zip).
- Les avions et livrées sont ignorés pendant l'analyse (plus rapide).
- Aide › Signaler un problème / Proposer une idée (issue GitHub préremplie).

**beta v0.5**
- Première beta publique.
- Avions statiques : méthodes par renommage et par variantes, mise à jour automatique de `layout.json`.
- Profils GSX : détection, copie, gestion de plusieurs versions avec choix mémorisé.
- Modes MSFS 2024 (Community + Community2024) et MSFS 2020, avec mémoire séparée.
- Application portable, sauvegardes, interface en 12 langues, guide d'utilisation, licences.

---

SGM — Statics & GSX Manager © 2026 Fabian Fuchs · distribué gratuitement.
