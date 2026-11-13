# Décisions de Fabian

Ces décisions s'imposent à tous les agents. Seul Fabian les modifie.

## Produit

- **Nom** : SGM — Statics & GSX Manager (anciennement Statics Manager).
- **Auteur** : Fabian Fuchs. Version actuelle : beta v0.6.
- **Simulateurs** : MSFS 2024 par défaut, mode MSFS 2020 en option, mémoire séparée par simulateur.
- **Portable** : aucune installation, données dans `SGM_data` à côté de `SGM.exe`.
- **Interface** : sombre, sobre et élégante. 12 langues, anglais par défaut, codes langue à deux lettres.
- **Statics** : deux méthodes (renommage `.bgl`↔`.bgl.off`, variantes on/off copiées sur `statics.bgl`).
- **GSX** : plusieurs versions (FULL/LITE…) → une seule active, choix mémorisé ; vert = active, rouge = non
  active, orange = à vérifier.
- **Profils installés à la main** reconnus par le code OACI ; bouton de recherche flightsim.to (« OACI GSX »).
- **Archives** : installation de profils par glisser-déposer, bouton, et proposition au lancement pour les
  archives du dossier Téléchargements. Rien sans confirmation.

## Licence et publication

- Freeware : utilisation et redistribution gratuites sans modification, vente interdite (`licenses/LICENSE-SGM.txt`).
- Qt for Python (PySide6) sous LGPL v3 : distribution **en dossier** (`--onedir`), textes de licence fournis,
  engagement de fournir les sources de Qt pendant 3 ans.
- Dons : https://paypal.me/Fuchy
- Publication : flightsim.to, un seul fichier `SGM_beta_vX.Y.zip`.

## Retours des utilisateurs

- Les commentaires flightsim.to ne sont pas lisibles par les agents (page en JavaScript, site inaccessible
  depuis le cloud). Les utilisateurs sont redirigés vers les Issues publiques de **FuchyBe/SGM**
  (menu Aide › Signaler un problème / Proposer une idée).
- Fabian recopie lui-même dans une issue un commentaire flightsim.to important, ou le colle dans
  `docs/RETOURS.md` (section « Reçus hors GitHub »).
- L'agent prépare les réponses ; Fabian les valide et les publie.

## Fonctionnement de l'équipe d'agents

- Fabian valide d'abord un **plan des ajouts** (section « Prêt » de la ROADMAP), puis **chaque changement**
  (PR) avant intégration.
- Code et signalements : dépôt **public** **FuchyBe/SGM**, séparé de Hangar.
