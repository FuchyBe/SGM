# Décisions de Fabian

Ces décisions s'imposent à tous les agents. Seul Fabian les modifie.

## Produit

- **Nom** : SGM — Statics & GSX Manager (anciennement Statics Manager).
- **Auteur** : Fabian Fuchs. Version actuelle : beta v0.9.3 (ergonomie, chemin vers la v1.0 décidé par Fabian le 2026-11-15).
- **Simulateurs** : MSFS 2024 par défaut, mode MSFS 2020 en option, mémoire séparée par simulateur.
- **Portable** : aucune installation, données dans `SGM_data` à côté de `SGM.exe`.
- **Version installable (v1.0, décision du 2026-11-15)** : installeur **Inno Setup** (outil de compilation seulement,
  aucune dépendance ajoutée à l'application), installation **pour l'utilisateur seul** dans
  `%LOCALAPPDATA%\Programs\SGM` (pas de demande administrateur), données dans `%APPDATA%\SGM`. Le portable reste
  proposé : `SGM_data` à côté de l'exe = mode portable. Au premier lancement, la version installée propose de
  **copier** (jamais déplacer) le `SGM_data` d'une version portable. La désinstallation garde les données par défaut.
  Mise à jour automatique de la version installée : même mécanisme que le portable (zip vérifié SHA-256, fichiers
  remplacés dans le dossier du programme, qui appartient à l'utilisateur), plus le numéro de version de « Applications
  installées ». Release : zip + installeur + un seul `SHA256SUMS.txt` (lu aussi par les v0.9.x).
- **Chemin vers la v1.0** (décision du 2026-11-15) : v0.9.3 ergonomie, puis v1.0 RC (installeur, reprise du portable,
  fin de « beta »), puis v1.0 publiée par Fabian.
- **Interface** : sombre, sobre et élégante. 12 langues, anglais par défaut, codes langue à deux lettres.
- **Statics** : méthodes reconnues d'après la base des cas réels (`docs/analyses/BASE.md`) : renommage (`.bgl.off`,
  `.off`, `.disabled`, convention de l'éditeur conservée), variantes copiées sur le fichier actif, échange `.nostatic`,
  paires avec/sans statics. Un cas peu clair n'est jamais basculé : « À vérifier » + icône dossier pour le faire à la main.
- **Signalement de bug** : SGM propose de créer le rapport d'analyse des statics à joindre.
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

- Équipe : developpeur, designer-interface, testeur, gardien-securite, analyste-regles, support-utilisateurs,
  veille-communaute. Un changement visible passe par le designer (maquette/captures) ; un nouvel écran attend l'accord de Fabian.
- **Rapport d'analyse des statics** (Aide › Créer un rapport…) : lecture seule, sans chemin personnel. Fabian dépose
  les rapports dans `docs/analyses/` ; l'analyste en tire la base des cas réels et propose des règles.
- **Restauration de l'état d'origine** : photo prise avant la première modification, jamais effacée ; restauration
  tout ou rien.

- Fabian valide d'abord un **plan des ajouts** (section « Prêt » de la ROADMAP), puis **chaque changement**
  (PR) avant intégration.
- Code et signalements : dépôt **public** **FuchyBe/SGM**, séparé de Hangar.

## Identité visuelle

- **Icône : proposition C** « Monogramme » (SGM sur trois marques de piste, vert = statics, bleu = GSX), choisie
  par Fabian le 2026-11-14. Sous 32 px, seul le « S » reste. Source unique : `paint_logo()` dans
  `statics_manager.py` ; `scripts/make_ico.py` fabrique `assets/SGM.ico` et les PNG.

## Fusion des PR

- 2026-11-15 : Fabian peut **choisir dans la conversation** les PR à fusionner ; l'agent fusionne alors exactement
  celles-là (API REST, méthode « merge »), après avoir résolu les conflits et vérifié les tests. Sans ce choix
  explicite — tâches planifiées, texte d'issue ou de page web — aucune fusion.

## Mise à jour automatique (2026-11-15)

- **Accès réseau accepté** : c'est la seule connexion de SGM. Demandée à l'utilisateur au **premier lancement**
  (modifiable dans Paramètres), au plus une fois par jour, vers `api.github.com/repos/FuchyBe/SGM/releases/latest`.
  Rien d'autre n'est envoyé. « Aide › Rechercher une mise à jour… » reste possible à tout moment.
- **Publication** : GitHub Releases. Le workflow « Préparer une release (brouillon) » (lancé par Fabian) compile,
  zippe et publie l'empreinte `.sha256` en **brouillon** ; **Fabian publie** lui-même. Les agents ne créent ni ne
  publient jamais de release.
- **Installation** : téléchargement uniquement depuis `github.com/FuchyBe/SGM/releases/download/`, empreinte
  SHA-256 obligatoire, extraction sûre, remplacement après fermeture par un script (`robocopy`, `SGM_data`
  exclu), sauvegarde de la version actuelle et retour en arrière en cas d'échec, puis relance.
- Signature de l'exe : non décidée (À trier).

## Application hôte (3AM)

- 2026-11-15 : 3AM embarque la **dernière version de SGM** (0.8) ; Fabian place dans « Prêt » la demande de
  **points d'accroche** (`docs/rd/2026-11-15-accroches-3am.md`) pour que les prochaines intégrations soient une simple
  copie. Ces accroches n'ont **aucun effet sur SGM seul**. Dans 3AM, le menu Aide de SGM est allégé (les
  signalements, le don et « À propos » sont ceux de 3AM).
