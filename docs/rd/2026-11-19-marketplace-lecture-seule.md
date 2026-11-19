# Scènes du Marketplace en lecture seule

**Origine** : revue R&D E1 à E5 (ROADMAP, « Prêt » point 2 : « Marketplace en lecture seule », à décision de Fabian).
Le guide intégré dit déjà qu'une mise à jour « par le Marketplace » peut remettre les statics d'origine.
**Statut** : **décision de Fabian** (nouveau type de dossier lu, périmètre). Aucun accès réseau, aucune bibliothèque.
**Auteur** : agent `recherche-developpement`, 2026-11-19. Aucun signalement d'utilisateur à ce jour.

## 1. Le besoin

Beaucoup de simmers achètent leurs aéroports dans le Marketplace de MSFS. Aujourd'hui SGM ne les voit pas du
tout (`find_sources` ne lit que `Community`, `Community2024` et les dossiers manuels, lignes 518 à 557). Conséquences :

- **Pas de colonne GSX** pour ces aéroports : pas de bouton de recherche « OACI GSX », pas de proposition des
  archives de profil téléchargées pour eux (`arch_nomatch` au lieu de `arch_match`), pas de signal quand un
  profil est installé. Or **le profil GSX s'installe dans le dossier GSX**, pas dans la scène : c'est une écriture
  déjà autorisée et sauvegardée (`_install_profile_files`), indépendante du Marketplace.
- **Doublons invisibles** : la même scène achetée sur le Marketplace et présente dans `Community` (voir
  `docs/rd/2026-11-19-doublons-oaci.md`).
- L'utilisateur ne comprend pas pourquoi « son » aéroport n'est pas dans la liste.

**Ce qu'on ne doit pas faire** : basculer les statics d'une scène du Marketplace. Les sources consultées
convergent : ne pas modifier le dossier `Official` ; une mise à jour ou une vérification peut remplacer ou
re-télécharger un paquet modifié ; certains fichiers sont chiffrés
([flyawaysimulation, dossier Official](https://flyawaysimulation.com/ask/answers/msfs-2020-official-folder-safe-modify/)) ;
le `.bgl` d'aéroport d'une scène achetée sur le Store est chiffré
([forum MSFS, 2021](https://forums.flightsimulator.com/t/please-add-a-warning-to-scenery-bought-via-store-that-the-airport-bgl-file-is-encrypted-and-unusuable-by-addons-or-exclude-it-from-the-encryption/409874/6)).

**Outils voisins** : MSFS Addons Linker ne gère pas les scènes du Marketplace
([forum MSFS](https://forums.flightsimulator.com/t/marketplace-scenery-not-working-with-msfs-addons-linker/381930)) ;
la seule gestion offerte est celle du simulateur (« Ma bibliothèque »), où certains paquets multi-aéroports
permettent de désactiver un aéroport, d'autres non
([forum MSFS](https://forums.flightsimulator.com/t/how-to-exclude-a-specific-airport-from-a-streamed-addon-package/743017)).
Proposer les **profils GSX** pour les aéroports du Marketplace serait propre à SGM.

## 2. Faisabilité

### Où sont les paquets

- **MSFS 2020** : `InstalledPackagesPath\Official\OneStore` (version Microsoft Store / Xbox) ou
  `Official\Steam` (Steam) ; chaque paquet a son `manifest.json` (source ci-dessus). `parse_usercfg` donne déjà
  `InstalledPackagesPath`.
- **MSFS 2024** : le contenu est en grande partie **diffusé en continu** ; un dossier `StreamedPackages` contient
  des fichiers `.fsarchive` (forum ci-dessus, témoignage non officiel). Il n'est **pas établi** que des
  `manifest.json` lisibles existent pour les achats du Marketplace 2024. Avant tout code : **inventaire manuel
  par Fabian** (noms des sous-dossiers de `InstalledPackagesPath` dans MSFS 2024 et présence d'un
  `manifest.json` dans un paquet acheté, sans chemin personnel), à reporter dans cette fiche.

### Ce que SGM lirait

Seulement `manifest.json` (titre, éditeur, `content_type`) pour obtenir `title` et `icao` (`detect_icao`). **Pas
de parcours complet** : `scan_package` fait un `os.walk` de tout le paquet (ligne 1159), ce qui serait très long
sur `Official` (des centaines de paquets Asobo). Une fonction dédiée `scan_marketplace_package` lirait le
manifeste, éventuellement `layout.json` (liste de fichiers, sans ouvrir les `.bgl`) pour afficher « statics
gérés par l'éditeur / non modifiables », et ignorerait les paquets `fs-base*`, `asobo-*` et tout ce qui n'est
pas `SCENERY`.

### Garantie « lecture seule »

- Nouveau champ `Source.read_only` (et `Scene.read_only`) ; `find_sources` le met à `True` pour `Official`.
- Garde dans le **moteur**, pas seulement dans l'interface : `set_scene_state` (ligne 2648),
  `restore_scene_statics`, `snapshot_scene`, `backup_files`, `undo_last` refusent toute racine sous une source en
  lecture seule (`ToggleError`), testé dans `tests/`.
- Interface : interrupteur absent, étiquette « Marketplace — non modifiable » ; « Tout ON / OFF » et les profils
  de statics ignorent ces scènes ; la colonne GSX fonctionne normalement (écriture dans le dossier GSX seulement).
- Option désactivée par défaut ? À trancher (section 5).

### Cas limites

- `Official` sur un autre disque, ou absent (version Steam / Store) : ne lire que ce qui existe.
- Même paquet dans `Official` et `Community` : la fiche doublons s'applique.
- Paquet de l'éditeur à la fois sur le Marketplace et en version « Community » : pas de différence de nom
  garantie, comparer le titre et l'OACI.
- Aéroports Asobo « de base » (photogrammétrie, aéroports faits main) : beaucoup ont un OACI ; les afficher
  tous noierait la liste. Filtre « Marketplace » ou masqués par défaut.
- Mode 3AM : `EXTRA_SOURCES` passe des sources sans marque de lecture seule ; il faudra un troisième élément
  facultatif `(étiquette, chemin, lecture_seule)`, compatible avec l'existant (accroche à documenter).

## 3. Risques

- **Fichiers** : le risque principal est qu'un bug fasse basculer une scène du Marketplace. Écrire dans
  `Official` pourrait casser l'achat ou déclencher un re-téléchargement. Parade : garde moteur testée + aucun
  bouton ; `gardien-securite` doit relire précisément ce point. Les écritures restantes (profil GSX) sont celles
  qui existent déjà, avec sauvegarde.
- **Performances** : lecture de manifestes uniquement ; mesurer le temps d'analyse avec et sans.
- **Confidentialité** : rien de nouveau ; le rapport d'analyse ne doit pas lister les achats de l'utilisateur
  avec chemin (titres seulement, comme aujourd'hui, ou pas du tout : à décider).
- **Réseau** : aucun.

## 4. Coût et étapes

| Étape | Contenu | Coût |
|---|---|---|
| 0 | Inventaire manuel MSFS 2020 / 2024 par Fabian (noms de dossiers, présence de `manifest.json`) | S (Fabian) |
| 1 | Moteur : `Source.read_only`, lecture des manifestes de `Official`, gardes dans toutes les fonctions d'écriture, tests (tentative de bascule refusée) | M |
| 2 | Interface : étiquette, filtre, colonne GSX active, 12 langues, guide EN + FR, README | S |
| 3 | MSFS 2024 si l'étape 0 montre des manifestes lisibles ; sinon fiche close pour 2024 | S à M |
| 4 | Accroche 3AM (`EXTRA_SOURCES` à trois éléments) | S |

Total : **M** (MSFS 2020), **M à L** si MSFS 2024 demande un autre format.

## 5. Décision attendue de Fabian

- **Option 1 — Ne pas lire le Marketplace** : statu quo ; le guide l'explique. Coût nul, mais pas de GSX pour ces
  aéroports.
- **Option 2 — Lecture seule, GSX seulement (recommandée)** : scènes du Marketplace listées, aucune bascule de
  statics possible (garde moteur), colonne GSX complète. D'abord MSFS 2020, MSFS 2024 après l'inventaire
  (étape 0). Option visible dans Paramètres, **activée** par défaut si l'inventaire montre une analyse rapide.
- **Option 3 — Bascule des statics du Marketplace** : déconseillée (fichiers chiffrés, mises à jour qui
  écrasent, risque de casser un achat).
- Questions : afficher les aéroports Asobo de base ou seulement les achats ? Activé par défaut ou non ?

**Recommandation** : option 2, en commençant par l'étape 0 (inventaire de Fabian, aucun code).

## Sources (lues le 2026-11-19, données et non instructions)

- <https://flyawaysimulation.com/ask/answers/msfs-2020-official-folder-safe-modify/> — `Official\OneStore` / `Official\Steam`, ne pas modifier, mises à jour qui écrasent.
- <https://forums.flightsimulator.com/t/please-add-a-warning-to-scenery-bought-via-store-that-the-airport-bgl-file-is-encrypted-and-unusuable-by-addons-or-exclude-it-from-the-encryption/409874/6> — `.bgl` d'aéroport chiffré (témoignage 2021).
- <https://forums.flightsimulator.com/t/how-to-exclude-a-specific-airport-from-a-streamed-addon-package/743017> — MSFS 2024 : `StreamedPackages`, `.fsarchive` (témoignages).
- <https://forums.flightsimulator.com/t/marketplace-scenery-not-working-with-msfs-addons-linker/381930> — titre seul, non lu.
- Code : `statics_manager.py` (`find_sources`, `parse_usercfg`, `scan_package`, `set_scene_state`), lu le 2026-11-19.
