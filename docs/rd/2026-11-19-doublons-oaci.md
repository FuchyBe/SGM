# Doublons OACI : deux scènes ou deux profils GSX pour le même aéroport

**Origine** : revue R&D E1 à E5 (ROADMAP, « Prêt » point 2 : « doublons OACI (SGM ou 3AM ?) », à décision de Fabian).
**Statut** : **décision de Fabian** (partage des rôles entre SGM et 3AM). Aucun accès réseau, aucune bibliothèque.
**Auteur** : agent `recherche-developpement`, 2026-11-19. Aucun signalement d'utilisateur à ce jour sur ce point.

## 1. Le besoin

Deux situations distinctes se cachent derrière « doublon OACI » :

- **A. Deux scènes pour le même aéroport** dans les dossiers lus par SGM : une scène achetée et une gratuite, une
  ancienne version restée dans `Community` à côté de la nouvelle, la même scène dans `Community` et dans
  `Community2024` (MSFS 2024 lit les deux, `SIMS["MSFS 2024"]["communities"]`), ou une scène liée deux fois
  (lien dans `Community` + dossier manuel). MSFS charge alors les deux : bâtiments en double, statics qui
  « reviennent » parce que l'autre scène les affiche, GSX qui se cale sur la mauvaise. Le simmer croit que SGM
  n'a pas marché.
- **B. Deux profils GSX pour le même aéroport** dans le dossier GSX : profil fourni par la scène + profil
  installé à la main (flightsim.to), ancien et nouveau profil, FULL et LITE copiés tous les deux. Les guides
  publics recommandent de ne garder **qu'un seul profil actif par scène**, un ancien `.ini` installé à la main
  pouvant « prendre le dessus ou entrer en conflit » avec celui attendu
  ([flyawaysimulation, gestionnaire de profils GSX](https://flyawaysimulation.com/ask/answers/use-gsx-pro-profile-manager-msfs/)).
  La règle exacte de choix de GSX entre deux profils n'est pas documentée publiquement (non trouvée le 2026-11-19).

**Ce qui existe déjà dans SGM** (lecture de `statics_manager.py`) :

- B est **déjà en partie couvert** : `gsx_manual_profiles` (vers la ligne 2258) liste les profils du dossier GSX
  dont le nom commence par l'OACI de la scène sans venir de la scène ; si la scène a aussi son propre profil, la
  colonne GSX passe en orange avec `gsx_other_installed` (« Un autre profil est aussi installé : … », vers la
  ligne 3933). Les variantes FULL/LITE d'une même scène sont déjà gérées (une seule active, `gsx_other_installed`
  de moteur, `_copy_gsx`).
- A **n'est pas couvert** : `scan_all` dédoublonne seulement un même dossier réel (`os.path.realpath`), pas deux
  paquets différents pour un même OACI. Pire, quand deux scènes ont le même OACI, le profil fourni par la scène 1
  et installé dans GSX apparaît pour la scène 2 comme un « profil installé à la main », et inversement : la
  colonne GSX de chacune passe en orange sans dire **pourquoi** (la vraie cause est le doublon de scène).
- À l'installation d'une archive, `arch_match` cite déjà toutes les scènes correspondant à l'OACI (vers la ligne
  5337) : le doublon y est visible mais pas signalé comme tel.

**Outils voisins** : MSFS Addons Linker et les gestionnaires d'add-ons activent ou désactivent des **paquets
entiers** (liens dans `Community`) ; ils ne relient pas l'OACI aux profils GSX. Les gestionnaires de profils GSX
(ex. « Dave's GSX Profile Manager », [avsim](https://www.avsim.com/forums/topic/691313-daves-gsx-profile-manager/))
gèrent les profils sans voir les statics. Personne ne fait le lien « scène en double → statics et GSX
incohérents » : c'est un créneau propre à SGM/3AM.

## 2. Faisabilité

Tout est déjà lu par SGM : `Scene.icao` (`detect_icao`, ligne 1077), `Scene.source`, `Scene.gsx_files`,
`gsx_dest_index`. Aucun nouveau fichier à lire.

- **Détection A** (lecture seule) : après `scan_all`, regrouper les scènes `is_airport` par `icao` ; un groupe
  de 2 ou plus = doublon. Ignorer les scènes sans OACI ou dont l'OACI vient seulement du nom de dossier (moins
  sûr). Cas limites :
  - Paquets **complémentaires légitimes** pour un même aéroport (scène + « mesh », scène + « jetways »,
    scène + paquet de statics séparé, librairies d'objets) : ce n'est pas un doublon. Ne signaler que si
    **les deux** paquets sont de type `SCENERY` et contiennent un `.bgl` d'aéroport — or SGM ne lit pas le
    contenu des `.bgl`. Proposition prudente : wording « **2 scènes pour EBBR** » (constat), jamais « doublon à
    supprimer » (jugement).
  - Même paquet dans `Community` et `Community2024` (MSFS 2024) : nom de dossier identique → cas le plus clair.
  - Faux OACI détecté dans un titre (mot de 4 majuscules) : le regroupement pourrait relier deux scènes sans
    rapport. `ICAO_STOP` limite déjà ce risque ; à surveiller dans `docs/analyses/BASE.md`.
- **Détection B** : déjà faite ; il suffit, quand le doublon A existe, d'attribuer chaque profil installé à la
  scène qui l'a fourni (comparaison de contenu, `same_content`) au lieu de le compter comme « manuel ».
- **Action** : pour A, la seule vraie correction est de **désactiver un paquet entier** (le sortir de
  `Community`, retirer un lien). C'est une écriture **hors du paquet de la scène** que SGM s'interdit
  (CLAUDE.md, « Jamais d'écriture hors du paquet… ») : elle relève d'un gestionnaire d'add-ons, donc de **3AM**.
  Pour B, SGM sait déjà retirer un profil qu'il a installé lui-même ; retirer un profil **installé à la main** n'est
  pas fait aujourd'hui et ne doit pas l'être sans sauvegarde et confirmation (fichier que l'utilisateur a pu
  modifier).

## 3. Risques

- **Fichiers** : la détection est en lecture seule, risque nul. Le seul risque vient d'une éventuelle action
  « retirer l'autre profil » : à limiter aux profils dont l'empreinte est connue (journal `gsx_record` /
  `written`), sauvegarde dans `backups/_GSX`, sinon « À vérifier » sans rien toucher.
- **Faux positif** : un message « 2 scènes pour … » sur deux paquets complémentaires inquiéterait à tort. D'où un
  constat neutre, en infobulle / note, sans couleur rouge.
- **Confidentialité / réseau** : rien. Le rapport d'analyse pourrait compter les doublons (sans chemin), utile à
  `analyste-regles`.
- **3AM** : si 3AM affiche aussi les doublons, éviter deux messages différents pour la même chose. Une fonction
  moteur unique `icao_duplicates(scenes)` dans SGM, appelée par 3AM, évite la divergence (nouvelle accroche à
  documenter dans `docs/rd/2026-11-15-accroches-3am.md` et `tests/test_accroches.py`).

## 4. Coût et étapes

| Étape | Contenu | Coût |
|---|---|---|
| 1 | Moteur : `icao_duplicates(scenes)` (lecture seule) + tests (même dossier dans Community/Community2024, scène + mesh, faux OACI) | S |
| 2 | Colonne GSX : profil fourni par l'autre scène reconnu comme tel ; note « 2 scènes pour {icao} : {names} » en infobulle, 12 langues, guide EN + FR | S |
| 3 | Filtre « Aéroports en double » dans la liste (comme « Nouvelles scènes ») | S |
| 4 | (option, 3AM) Désactivation d'un paquet entier depuis 3AM, en s'appuyant sur `icao_duplicates` | dans 3AM |
| 5 | (option) « Garder seulement ce profil » pour B, limité aux profils d'empreinte connue | M |

Total pour SGM (étapes 1 à 3) : **S à M**.

## 5. Décision attendue de Fabian

- **Option 1 — Tout dans 3AM** : SGM ne change rien ; 3AM détecte et désactive les paquets en double. Simple, mais
  les utilisateurs de SGM seul gardent la colonne GSX orange sans explication.
- **Option 2 — SGM signale, 3AM agit (recommandée)** : SGM détecte et **explique** (étapes 1 à 3, lecture seule,
  aucune nouvelle écriture), expose `icao_duplicates` à 3AM ; la désactivation d'un paquet entier reste dans 3AM,
  le seul qui gère les paquets. Respecte la règle « jamais d'écriture hors du paquet » de SGM.
- **Option 3 — SGM signale et agit** : SGM désactive lui-même un paquet en double. Déconseillé : sort du périmètre
  d'écriture de SGM (risque sur les fichiers, recouvrement avec 3AM).
- Question annexe : l'étape 5 (retrait d'un profil GSX concurrent d'empreinte connue) est-elle souhaitée, ou
  SGM se contente-t-il d'ouvrir le dossier GSX ?

**Recommandation** : option 2, étapes 1 à 3, sans l'étape 5 pour l'instant.

## Sources

- Code : `statics_manager.py` (`detect_icao`, `scan_all`, `gsx_manual_profiles`, `gsx_other_installed`, `arch_match`), lu le 2026-11-19.
- Conflits de profils GSX : <https://flyawaysimulation.com/ask/answers/use-gsx-pro-profile-manager-msfs/> (guide tiers, donnée non officielle).
- Gestionnaire de profils tiers : <https://www.avsim.com/forums/topic/691313-daves-gsx-profile-manager/> (titre seul, non lu).
- À vérifier par Fabian dans MSFS : quelle scène l'emporte quand deux paquets d'un même aéroport sont chargés
  (ordre de chargement non confirmé par une source officielle lors de cette recherche).
