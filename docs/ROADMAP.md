# Feuille de route de SGM

Règles : les agents ajoutent les idées dans **À trier**. **Seul Fabian** déplace un sujet dans **Prêt**
(en le gardant tel quel ou en le précisant). Le sprint du matin prend le premier sujet de « Prêt ».

## Prêt

Placés par Fabian le 2026-11-15 (« je suis tes propositions »).

1. **Publier la v1.0** — Fabian publie (aucun agent ne publie) : supprimer le brouillon v0.9, puis Actions ›
   « Préparer une release (brouillon) » › Run workflow, vérifier (zip portable, installeur, SHA256SUMS.txt), puis
   « Publish release ». Mise à jour flightsim.to : `docs/flightsim/maj-v1.0.md` et `docs/flightsim/visuels/`. S.
2. **Nouvelles fonctions (revue R&D, E1 à E5)**, après la 1.0 — statics remis par une mise à jour de scène (bandeau
   « Réappliquer ») ; profil GSX peut-être périmé ; détection du trafic IA ; export / import des réglages et profils ;
   tri de « À trier ». Points à **décision de Fabian** avant développement : doublons OACI (SGM ou 3AM ?),
   Marketplace en lecture seule, ligne de commande. M à L.
- **Signature de l'exécutable** — à décider par Fabian (coût d'un certificat), utile avant la 1.0 (SmartScreen).

## En cours (PR à tester)

- v1.0 — branche `sprint/2026-11-15-v1.0`.

## À trier

Chaque sujet : titre, origine, bénéfice pour l'utilisateur, estimation (S/M/L), risque.

- **Réserves de la revue finale v0.9.2** — origine : revue. Restauration proposée même sur une scène déjà
  d'origine ; « Tout OFF » relit chaque scène (à mesurer) ; mise à jour annulée si SGM.exe a été renommé ;
  retour arrière de la mise à jour qui laisse les nouveaux fichiers de `_internal` ; SGM à la racine d'un lecteur ;
  .7z avec un .ini > 4 Mo sans rapport refusé en entier ; profil GSX remplacé par l'utilisateur entre deux
  installations. S chacun. Risque faible.

- **Envoi direct des rapports sans compte GitHub** — origine : Fabian. Relais serveur. M. **Décision de Fabian**
  (réseau, serveur, confidentialité). Fiche, étape 3.
- **Mise à jour automatique** — origine : Fabian. GitHub Releases + SHA-256 + programme de mise à jour, `SGM_data`
  préservé. M. **Décision de Fabian** (réseau optionnel, releases GitHub, signature). Fiche, étape 4.

- **Tester .7z et .rar avec 7-Zip** — origine : beta v0.6. Extraction non testée faute de 7-Zip dans
  l'environnement de développement. Bénéfice : fiabilité de l'installation d'archives. S. Risque faible.
- **Signature de l'exécutable** — origine : publication. SmartScreen et certains antivirus signalent un exe
  non signé. Bénéfice : confiance des utilisateurs. M (coût d'un certificat : décision de Fabian). Risque nul.
- **Annuler la dernière action** — origine : idée. Revenir à l'état d'avant le dernier clic (et pas seulement à
  l'origine, déjà couvert par « Restaurer l'état d'origine », PR #2). Bénéfice : confort. M. Risque moyen (fichiers).
- **Profils de statics** — origine : idée. Enregistrer un jeu d'états ON/OFF (« Trafic IA dense », « Vols
  photo ») et l'appliquer d'un clic. Bénéfice : confort. M. Risque faible.
- **Relecture native des traductions** (ar, zh, ja surtout) — origine : publication. S. Risque nul.
- **Arabe : flèche du menu « Profils de statics » invisible** — origine : revue qualité 2026-11-25 (bug Qt en
  RTL, capture `docs/captures/qualite-2026-11-25/ar-barre-x3.png`, essais `test-fleche-menu-rtl.png`). Règle QSS
  `menu-indicator` propre au RTL, à vérifier sous Windows et avec `build_qss` (3AM). Bénéfice : on voit que le
  bouton ouvre un menu. S. Risque faible.
- **Rendre « Restaurer l'état d'origine » visible** — origine : revue qualité 2026-11-25 (`AUDIT.md`, P2).
  Ajouter « Clic droit : restaurer l'état d'origine » à l'info-bulle de ligne (12 langues). Bénéfice : retour
  arrière trouvé sans le guide. S. Risque nul.
- **Filtre actif en bleu plutôt qu'en vert** — origine : revue qualité 2026-11-25 (`nl-a-verifier.png`). Le vert
  est réservé à ON ; un filtre « À vérifier » actif apparaît en vert. Décision de Fabian (sens des couleurs). S.
  Risque nul.
- **Info-bulle sur l'interrupteur désactivé d'une scène « À vérifier »** — origine : revue qualité 2026-11-25
  (`en.png`, ligne EBCI). Même texte que l'icône dossier. S. Risque nul.
- **Nettoyer les clés de traduction mortes** (`f_all`, `f_on`, `f_off`, `f_gsx`, `f_check`, `FILTER_KEYS`) —
  origine : revue qualité 2026-11-25. Vérifier d'abord que 3AM ne s'en sert pas. S. Risque faible.

## Livré

- **v1.0** (préparée) — version installable par utilisateur (PR #36), reprise du portable par copie, fin de « beta ».
- **beta v0.9.3** (PR #35) — ergonomie et visuels flightsim.to refaits.
- **Ergonomie v0.9.3** (PR #34) — menus Paramètres / Outils / Aide, raccourcis, libellés, bandeau de mise à jour,
  colonne GSX allégée, fenêtre Dossiers en sections. « Annuler » gardé (mot de Windows pour Ctrl+Z).
- **beta v0.9.2** (préparée) — sécurité archives et mise à jour (PR #29), robustesse et tout-ou-rien (PR #30),
  défauts de design (PR #31), traductions et guide (PR #32).
- **Mise à jour : 404 = aucune version publiée** (PR #27), **beta v0.9** (PR #26).
- **beta v0.9** (préparée) — mise à jour automatique, sécurité G1 à G6, .7z testé, français complet, accroches 3AM.
- **Archives .7z / .rar testées** (PR #25), **français complet** (PR #24), **sécurité G4 à G6** (PR #23).
- **Points d'accroche pour 3AM, S1 à S12** (PR #22).
- **Sécurité G1 à G3** (PR #21).
- **Mise à jour automatique** (PR #19) — GitHub Releases, SHA-256, retour arrière.
- **beta v0.8** publiée dans `main` (PR #18).
- **beta v0.8** — Annuler, profils de statics, colonnes ajustées au texte, Tout ON/OFF dans l'en-tête Statics (cas simples), Analyser vérifie les téléchargements, fenêtre Signaler / Suggérer, journal, bouton flightsim.to.
- **Profils de statics** (PR #17).
- **Annuler la dernière action** (PR #16).
- **Colonnes ajustées au texte, Tout OFF / Tout ON dans l'en-tête Statics** (PR #15).
- **Analyser vérifie les téléchargements, dossiers de téléchargement réglables** (PR #14).
- **Bouton flightsim.to** : recherche web limitée au site, réglage retiré (PR #13).
- **Fenêtre « Signaler un problème / Proposer une idée »** (PR #12).
- **Journal local** (PR #10).
- **beta v0.7** — méthodes de statics des éditeurs (base des cas réels), méthode officielle Orbx/Drzewiecki, restauration de l'état d'origine, rapport d'analyse, correction Homa Sim, cas peu clairs à faire à la main.
- **beta v0.6** — aéroports sans profil, profils installés à la main, recherche flightsim.to, catégories,
  installation de profils depuis une archive, menu Signaler un problème.
- **beta v0.5** — première version publique.
