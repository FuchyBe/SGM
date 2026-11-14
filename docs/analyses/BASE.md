# Base des cas réels de fichiers statics

Maintenue par l'agent `analyste-regles` (procédure `analyse`) à partir des rapports déposés dans ce dossier.
Aucun chemin personnel ni nom d'utilisateur.

## Comment ajouter un rapport

1. Dans SGM : **Aide › Créer un rapport d'analyse des statics…** (lecture seule, rien n'est modifié).
2. Sur GitHub, dossier `docs/analyses/` : **Add file › Upload files**, dépose le `.json`, choisis
   « Create a new branch » et ouvre la PR (ou fusionne directement : c'est un fichier de données).
3. Un rapport reçu d'un utilisateur dans une issue : vérifie-le, puis dépose-le de la même façon.

## Rapports traités

| Fichier | Date | Paquets | Scènes avec statics | Origine |
|---|---|---|---|---|
| `2026-11-14-rapport-1.json` | 2026-11-14 | 2 218 | 89 (après retrait des textures) | bibliothèque de Fabian (MSFS 2024) |
| `2026-11-14-rapport-2.json` | 2026-11-14 | 2 218 | 89 | même bibliothèque, après tests ; liste les fichiers de base |

## Bilan

Avant les règles du 2026-11-14, SGM gérait **15 scènes** sur ce rapport. Après : **79 scènes** (39 OFF, 27 ON,
1 mixte, 4 à vérifier, 8 ignorées à raison). Vérifié par simulation : OFF → ON → OFF → ON puis restauration
d'origine redonne des fichiers identiques octet pour octet pour toutes les scènes.

## Familles de noms et méthode retenue

| # | Famille (exemple réel) | Éditeurs | Scènes | Méthode ON / OFF | Avant | Verdict |
|---|---|---|---|---|---|---|
| 1 | `eggw-scene-statics.bgl.off` | iniBuilds, Burning Blue, FSimStudios, Pilot Experience, Pilot Plus, Orbx (GSE) | 13 | Renommage `.bgl` ↔ `.bgl.off` | géré | juste |
| 2 | `kdfw-scene-statics.off`, `KDCA_Static.off`, `esgg-statics.off`, `statics.off` | iniBuilds (12), Orbx (5), Drzewiecki (5), JetStream, UK2000, NZA, Axonos, cat3dual, LimeSim | 29 | Renommage `.off` ↔ `.bgl`, retour à `.off` (convention de l'éditeur, retrouvée dans la photo d'origine) | non vu | nouveau |
| 3 | `KBFI_STATIC.BGL`, `EDDF_Placements_staticAC.bgl`, `SP_LIRN_Static.bgl`, `objects-parked-aircraft.bgl` | Drzewiecki (8), SimPixel (3), Aerosoft, ASD, LimeSim, NetDesign, SiamFlight, Permille, Orbx JW, imaginesim, Seafront… | 27 | Renommage `.bgl` ↔ `.bgl.off` (« static » au singulier, « parked ») | non vu | nouveau |
| 4 | `EPWR_Static.BGL` + `EPWR_Static.off` **identiques** | Drzewiecki | 1 | ON ; OFF = supprimer le `.BGL` (son double reste) ; ON = renommer le `.off` | « conflit » | nouveau |
| 5 | `lyni_place.bgl` + `lyni_place.bgl.nostatic` (+ `layout.json.nostatic`) | Orbx (3), UK2000 KTEX | 4 | **Méthode officielle** (notice Orbx LYNI, panneau Orbx Central) : OFF `X.bgl`→`X.bgl.static`, `X.bgl.nostatic`→`X.bgl`, `layout.json`→`layout.json.static`, `layout.json.nostatic`→`layout.json` ; ON l'inverse. Échange de layout seulement si le fichier est un layout valide | non vu | nouveau |
| 5b | `KMDW_PLC.bgl` + `KMDW_PLC.bgl.nostatic` + `KMDW_Static.off` | Drzewiecki (7) | 7 | **Méthode officielle** (notice DD EPGD : mêmes renommages que 5 pour le PLC et `layout.json`), basculée avec `KMDW_Static.off` ↔ `.bgl` (DD : « retirer la bibliothèque d'avions statiques »). Si `KMDW_PLC.bgl` absent : renommer `.nostatic` en `.bgl` (règle de Fabian) | non vu | nouveau |
| 6 | `kpvd-scene-airport_nostatic.bgl` + `kpvd-scene-airport_static.bgl.disabled` | iniBuilds | 1 | Paire : un seul des deux actif, l'autre `.disabled` | non vu | nouveau |
| 7 | `lowi-scene-airport-statics.bgl.disabled` (1 595 504 o) + `lowi-scene-airport.bgl` (1 594 496 o) | iniBuilds | 1 | **Aéroport complet confirmé par le rapport 2** (tailles quasi identiques) : échange — ON active `-statics.bgl` et désactive `lowi-scene-airport.bgl` (`.disabled`), OFF l'inverse. Si le fichier de base était petit, la règle de Fabian (copie en `.bgl`) s'appliquerait | — | nouveau |
| 8 | `oiaw-airport-statics.bgl.off` + `oiaw-airport-nostatics.off`, **pas de `oiaw-airport.bgl`** | Homa Sim | 3 | **Rapport 2** : les deux aéroports complets sont désactivés → aucun aéroport chargé, très probablement à cause de SGM ≤ v0.6 (ancienne règle « statics → .off »). SGM affiche « Aucune version active » : ON active `-statics.bgl`, OFF active `-nostatics.bgl`, jamais les deux. (Si un `oiaw-airport.bgl` existe : variantes copiées dessus) | **bug v0.6** | corrigé |
| 9 | `EBCI_NoStaticAircraft.bgl` seul | Propair Flight | 1 | À vérifier (icône dossier) | non vu | prudent |
| 10 | `Xml_Placements_With_Static_Aircraft.bgl` (absent de `layout.json`) + `Xml Placements_Without_Static_Aircraft.bgl.nostatic` + `layout.json.static` | Orbx KBUR | 1 | À vérifier : l'éditeur échange `layout.json`, et « Without » ne doit jamais être activé comme s'il apportait les statics | non vu | prudent |
| 11 | `khnd-airport.bgl` + `khnd-airport.bgl.staticq` | UK2000 | 1 | **Règle de Fabian** : statics OFF de base ; ON = `khnd-airport.bgl` → `.bak` puis copie de `.staticq` nommée `khnd-airport.bgl` ; OFF = copie supprimée, `.bak` → `khnd-airport.bgl`. Sans `khnd-airport.bgl` : à vérifier | non vu | nouveau |
| — | `statics-off.config.off` (Contrail), `modelib_People_static.BGL`, `modelLib-parked-*.BGL`, `*_flatten.bgl`, textures `*static*.dds/.ktx2`, modèles `.bin/.gltf` | Pyreegue, Atelic, IPDC, imaginesim, Orbx, … | 127 | Ignorés | — | juste |

## Points d'attention (à confirmer par Fabian sur les vraies scènes)

- **Drzewiecki (KMDW, EPBY, EPGD, EPKT, EPLB, EPSC, YSWS)** : confirmé par Fabian : `XXXX_Static.off` et
  `XXXX_PLC.bgl.nostatic` sont tous deux la forme désactivée ; activer = renommer en `.bgl`. Une fois activé,
  `XXXX_PLC.bgl` est retrouvé grâce à la photo d'origine (son nom ne contient pas « static »).
- **LOWI** et **Homa Sim** : les règles 7 et 8 supposent que le fichier de base (`lowi-scene-airport.bgl`,
  `oiaw-airport.bgl`) existe. L'ancien rapport ne le listait pas ; le nouveau rapport le liste désormais.
- Les paquets Drzewiecki/Orbx livrent aussi `layout.json.nostatic` : SGM met à jour `layout.json` lui-même,
  ce fichier n'est pas utilisé.

## Tests à écrire

Toutes les familles 1 à 10 ont leur test dans `tests/test_real_cases.py` (noms réels, contenus factices).

## Sources éditeurs (recherche du 2026-11-14)

- Orbx LYNI — notice : `layout.json`→`layout.json.static`, `layout.json.nostatic`→`layout.json`, `lyni_place.bgl`→`.static`, `lyni_place.bgl.nostatic`→`lyni_place.bgl` (addonhub.org) ; même mécanisme que le panneau « Configure » d'Orbx Central (forum Orbx 213909).
- Drzewiecki EPGD — notice : mêmes renommages pour `EPGD_PLC.bgl` et `layout.json` (sceneryaddons.org) ; DD : la version sans statics « retire la bibliothèque d'avions statiques » (forum DD, KDCA).
- iniBuilds — équipe : renommer `…-scene-statics.bgl` en `.disabled` puis mettre à jour `layout.json`, garder une sauvegarde (forum iniBuilds, OMDB).
- Homa Sim — fiches Aerosoft / simMarket : « Static and non-static aircraft versions included » (pas de procédure publiée).
- MSFS — un `.off` renommé en `.bgl` peut être ignoré si `layout.json` n'est pas mis à jour (devsupport 6982) : SGM met toujours `layout.json` à jour.
