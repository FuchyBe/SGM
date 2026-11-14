# Feuille de route de SGM

Règles : les agents ajoutent les idées dans **À trier**. **Seul Fabian** déplace un sujet dans **Prêt**
(en le gardant tel quel ou en le précisant). Le sprint du matin prend le premier sujet de « Prêt ».

## Prêt

Placés par Fabian le 2026-11-14, dans cet ordre.

1. **Nouvelle icône de l'application** — origine : Fabian. Agent : `directeur-artistique` : 3 à 4 propositions,
   Fabian choisit, puis intégration (exe, fenêtre, barre des tâches, README, flightsim.to). S.

## En cours (PR à tester)

- Filtres harmonisés + colonnes ×1,5 redimensionnables — PR #7.
- Suppression des archives GSX après installation — branche `sprint/2026-11-14-archives`.

## À trier

Chaque sujet : titre, origine, bénéfice pour l'utilisateur, estimation (S/M/L), risque.

- **Journal local (logs)** — origine : Fabian (2026-11-14). `SGM_data\logs`, rotation, chemins réduits, joint aux
  rapports de bug. S. Risque nul. Fiche : `docs/rd/2026-11-14-mise-a-jour-et-remontee.md` (étape 1).
- **Fenêtre « Signaler / Suggérer » intégrée** — origine : Fabian. Formulaire, rapport + journal joints, `.zip` prêt
  à glisser dans l'issue. M. Risque nul. Fiche, étape 2.
- **Envoi direct des rapports sans compte GitHub** — origine : Fabian. Relais serveur. M. **Décision de Fabian**
  (réseau, serveur, confidentialité). Fiche, étape 3.
- **Mise à jour automatique** — origine : Fabian. GitHub Releases + SHA-256 + programme de mise à jour, `SGM_data`
  préservé. M. **Décision de Fabian** (réseau optionnel, releases GitHub, signature). Fiche, étape 4.

- **Vérifier l'adresse de recherche flightsim.to** — origine : beta v0.6. Le format
  `flightsim.to/search/?keyword=` n'a pas pu être vérifié. Bénéfice : bouton de recherche fiable. S. Risque faible.
- **Tester .7z et .rar avec 7-Zip** — origine : beta v0.6. Extraction non testée faute de 7-Zip dans
  l'environnement de développement. Bénéfice : fiabilité de l'installation d'archives. S. Risque faible.
- **Signature de l'exécutable** — origine : publication. SmartScreen et certains antivirus signalent un exe
  non signé. Bénéfice : confiance des utilisateurs. M (coût d'un certificat : décision de Fabian). Risque nul.
- **Annuler la dernière action** — origine : idée. Revenir à l'état d'avant le dernier clic (et pas seulement à
  l'origine, déjà couvert par « Restaurer l'état d'origine », PR #2). Bénéfice : confort. M. Risque moyen (fichiers).
- **Profils de statics** — origine : idée. Enregistrer un jeu d'états ON/OFF (« Trafic IA dense », « Vols
  photo ») et l'appliquer d'un clic. Bénéfice : confort. M. Risque faible.
- **Arabe : en-tête mal aligné** — origine : captures du designer (`docs/captures/reference/ar.png`). En arabe, le
  sous-titre « avions statiques et profils GSX » passe sous les compteurs, à droite, au lieu de rester sous le titre.
  Bénéfice : interface propre en RTL. S. Risque nul. Agent : designer-interface.
- **Relecture native des traductions** (ar, zh, ja surtout) — origine : publication. S. Risque nul.

## Livré

- **beta v0.7** — méthodes de statics des éditeurs (base des cas réels), méthode officielle Orbx/Drzewiecki, restauration de l'état d'origine, rapport d'analyse, correction Homa Sim, cas peu clairs à faire à la main.
- **beta v0.6** — aéroports sans profil, profils installés à la main, recherche flightsim.to, catégories,
  installation de profils depuis une archive, menu Signaler un problème.
- **beta v0.5** — première version publique.
