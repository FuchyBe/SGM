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

## Bilan

Avant les règles du 2026-11-14, SGM gérait **15 scènes** sur ce rapport. Après : **78 scènes** (38 OFF, 27 ON,
1 mixte, 4 à vérifier, 8 ignorées à raison). Vérifié par simulation : OFF → ON → OFF → ON puis restauration
d'origine redonne des fichiers identiques octet pour octet pour toutes les scènes.

## Familles de noms et méthode retenue

| # | Famille (exemple réel) | Éditeurs | Scènes | Méthode ON / OFF | Avant | Verdict |
|---|---|---|---|---|---|---|
| 1 | `eggw-scene-statics.bgl.off` | iniBuilds, Burning Blue, FSimStudios, Pilot Experience, Pilot Plus, Orbx (GSE) | 13 | Renommage `.bgl` ↔ `.bgl.off` | géré | juste |
| 2 | `kdfw-scene-statics.off`, `KDCA_Static.off`, `esgg-statics.off`, `statics.off` | iniBuilds (12), Orbx (5), Drzewiecki (5), JetStream, UK2000, NZA, Axonos, cat3dual, LimeSim | 29 | Renommage `.off` ↔ `.bgl`, retour à `.off` (convention de l'éditeur, retrouvée dans la photo d'origine) | non vu | nouveau |
| 3 | `KBFI_STATIC.BGL`, `EDDF_Placements_staticAC.bgl`, `SP_LIRN_Static.bgl`, `objects-parked-aircraft.bgl` | Drzewiecki (8), SimPixel (3), Aerosoft, ASD, LimeSim, NetDesign, SiamFlight, Permille, Orbx JW, imaginesim, Seafront… | 27 | Renommage `.bgl` ↔ `.bgl.off` (« static » au singulier, « parked ») | non vu | nouveau |
| 4 | `EPWR_Static.BGL` + `EPWR_Static.off` **identiques** | Drzewiecki | 1 | ON ; OFF = supprimer le `.BGL` (son double reste) ; ON = renommer le `.off` | « conflit » | nouveau |
| 5 | `lyni_place.bgl` + `lyni_place.bgl.nostatic` | Orbx (3), UK2000 | 4 | **Règle de Fabian** : OFF `X.bgl`→`X.bgl.bak` puis copie de `X.bgl.nostatic` en `X.bgl` ; ON : copie supprimée, `X.bgl.bak`→`X.bgl` | non vu | nouveau |
| 5b | `KMDW_PLC.bgl.nostatic` seul | Drzewiecki (7) | 7 | **Règle de Fabian** : forme désactivée, ON = renommer en `KMDW_PLC.bgl` (avec `XXXX_Static.off` → `.bgl`) | non vu | nouveau |
| 6 | `kpvd-scene-airport_nostatic.bgl` + `kpvd-scene-airport_static.bgl.disabled` | iniBuilds | 1 | Paire : un seul des deux actif, l'autre `.disabled` | non vu | nouveau |
| 7 | `lowi-scene-airport-statics.bgl.disabled` | iniBuilds | 1 | **Règle de Fabian** : ON = copie en `.bgl` (le `.disabled` reste), OFF = copie supprimée. Sécurité : si le fichier de base `lowi-scene-airport.bgl` a presque la même taille (±25 %), c'est un aéroport complet → échange des deux | — | nouveau |
| 8 | `oiaw-airport.bgl` + `oiaw-airport-statics.bgl.off` + `oiaw-airport-nostatics.off` | Homa Sim | 3 | Variantes : la version choisie est copiée sur `oiaw-airport.bgl` ; sans ce fichier : à vérifier | **danger** : SGM proposait ON = aéroport en double | corrigé |
| 9 | `EBCI_NoStaticAircraft.bgl` seul | Propair Flight | 1 | À vérifier (icône dossier) | non vu | prudent |
| 10 | `Xml_Placements_With_Static_Aircraft.bgl` absent de `layout.json` + `layout.json.static` | Orbx KBUR | 1 | À vérifier : l'éditeur échange `layout.json` | non vu | prudent |
| 11 | `khnd-airport.bgl.staticq` | UK2000 | 1 | Ignoré (extension inconnue) | non vu | à confirmer |
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
