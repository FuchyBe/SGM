# Cas réels de profils GSX

Noms de profils et d'archives observés, et comportement de SGM. Tenu à jour par l'agent `chercheur-gsx`.
Dernier passage : 2026-11-19. Les noms viennent de titres publics de flightsim.to (observés le 2026-11-19) ;
les contenus de test restent factices. Le comportement est déduit de la lecture du code (`statics_manager.py`), pas d'un essai dans MSFS.

## Règles de SGM (lecture du code, 2026-11-19)

- Reconnaissance d'un profil : `is_gsx_profile` : chemin contenant « gsx », ou `.ini` de moins de 512 Ko contenant `[section.`
  et un mot-clé (`pushback`, `maxwingspan`, `jetway`, `parking`, `deice`, `stairs`), ou nom `xxx-….ini` (3-4 caractères,
  tiret, aucun point dans le reste du nom) avec `[section.` ou `[general]`. Le `.py` du même nom est joint automatiquement.
- Code OACI d'une scène : `detect_icao` : mot de 4 majuscules du titre (première lettre dans `ICAO_FIRST`, hors `ICAO_STOP`),
  sinon un mot de 4 lettres du nom de dossier si le titre contient un mot d'aéroport.
- Archives (`.zip`, `.7z`, `.rar`) : seuls `.ini`/`.py` extraits, chemins relatifs sûrs, 4 Mo par fichier, 20 000 entrées,
  2 000 profils, 64 Mo au total, vérifiés avant extraction. `.7z`/`.rar` demandent 7-Zip.
- Archives des Téléchargements proposées si un `.ini` correspond à `GSX_NAME_RE` ou si son chemin contient « gsx »
  et que tous ses profils ne sont pas déjà installés.
- Installation : sauvegarde de ce qui est remplacé (si le contenu diffère), journal pour restauration.
- Recherche : requête `« {OACI} GSX »` sur Google limité à flightsim.to.

## Titres flightsim.to observés (2026-11-19, catégorie « GSX Pro »)

| Titre (extrait) | Nom de fichier probable | Attendu de SGM |
|---|---|---|
| « RKPU Ulsan Airport (YSG 3DMESH) - GSX Profile » | `rkpu-….ini` | OACI RKPU trouvé dans le titre de la scène |
| « Asobo Santarem SBSN GSX Profile » | `sbsn-….ini` | OACI SBSN |
| « GSX Profile \| Jackson Hole v2 (KJAC) \| Dreamflight » | `kjac-….ini` | OACI KJAC |
| « Official GSX Profile - LGTS - Thessaloniki Airport "Makedonia" (Lisium Design) » | `lgts-….ini` | OACI LGTS |
| « GSX PRO Profile- Bristol (EGGD) UK2000 Scenery » | `eggd-….ini` | OACI EGGD |
| « gsx.cfg for Nattani A330-200 MRTT » | `gsx.cfg` (avion) | hors champ : ni `.ini` ni `.py`, ignoré |

Convention de titre : préfixe variable (« GSX Profile », « GSX Pro », « GSX PRO », « Official GSX Profile », « GSX Pro Config »)
et code OACI en général entre parenthèses. Aucune variante FULL/LITE vue dans ces onze titres.

## Cas limites repérés pour le `testeur` (noms réels, contenu factice)

1. `KOAK-BMWAmSim-rwprofiles.ini` (exemple msfsaddons) : nom avec tiret multiples, sans point : doit correspondre à `GSX_NAME_RE`.
2. Profil dont le nom contient un point (ex. `lfpg-v1.2.ini`, hypothétique) : `GSX_NAME_RE` le rejette ; il n'est reconnu que par
   son contenu (`[section.` + mot-clé) ou un chemin contenant « gsx ». Risque de profil non détecté dans une archive sans dossier « GSX ».
3. Archive contenant un `.ini` et son `.py` : les deux doivent être installés ensemble ; un `.py` seul n'est jamais proposé.
4. Titre sans OACI de 4 majuscules (ex. « Asobo Santarem SBSN GSX Profile » côté scène nommée « Santarem Airport ») : repose sur le nom de dossier.
5. Variantes FULL / LITE / VDGS : `variant_labels` retire préfixe et suffixe communs ; si deux étiquettes sont identiques, retombe sur les noms de fichiers.
6. Profil réservé à MSFS 2020 ou 2024 : SGM ne lit pas cette information (elle est dans la description de l'add-on) ; il l'installe quand même.
7. Profil livré à côté des `.bgl` (GSX le charge seul) : SGM le voit comme profil de la scène ; l'installer dans le dossier GSX
   crée un doublon sans danger mais à signaler.

## À compléter

Cas observés réellement par Fabian (profils non détectés, archives d'auteurs connus) : à ajouter ici avec le numéro d'issue.
