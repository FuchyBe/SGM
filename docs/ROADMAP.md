# Feuille de route de SGM

Règles : les agents ajoutent les idées dans **À trier**. **Seul Fabian** déplace un sujet dans **Prêt**
(en le gardant tel quel ou en le précisant). Le sprint du matin prend le premier sujet de « Prêt ».

## Prêt

Placés par Fabian le 2026-11-14, dans cet ordre.

1. **Points d'accroche pour une application hôte (3AM)** — placé par Fabian le 2026-11-15 (conversation 3AM).
   SGM porte lui-même les accroches dont 3AM a besoin (thème, contrôle de MSFS à trois états, sources, menu Aide,
   mise à jour inactive en mode hôte), **sans aucun effet sur SGM seul**. Fiche `docs/rd/2026-11-15-accroches-3am.md`
   (S1 à S12). S/M.

## En cours (PR à tester)

- Sécurité G1 à G3 — branche `sprint/2026-11-15-securite`.

## À trier

Chaque sujet : titre, origine, bénéfice pour l'utilisateur, estimation (S/M/L), risque.

- **Sécurité — relecture de SGM 0.8 par le gardien de 3AM (15 novembre), à placer dans « Prêt » par Fabian, en
  priorité.** Ces points touchent aussi SGM seul. 3AM 0.9.3 pose des correctifs provisoires (script d'accroches de 3AM),
  à remplacer par les vrais correctifs dans SGM. Détail : `docs/rd/2026-11-15-accroches-3am.md`, § « Sécurité ».
  - G1 `_gsx_restore` (« Tout restaurer ») supprime ou écrase un profil GSX **sans comparer son contenu** : un profil
    retouché dans l'éditeur GSX après l'installation disparaît (essai reproduit). S. Risque : perte d'un fichier
    modifié par l'utilisateur.
  - G2 Corbeille : `FOF_NOCONFIRMATION` sans `FOF_WANTNUKEWARNING` : sur une clé USB, un disque réseau ou un fichier
    trop gros, Windows **efface définitivement sans rien dire**, alors que le texte annonce la Corbeille. S.
  - G3 `origin/`, `undo/` et `_GSX` sont communs à MSFS 2020 et 2024, mais le contrôle « simulateur fermé » ne regarde
    que le simulateur choisi : « Tout restaurer » ou « Annuler » peut réécrire une scène de l'autre simulateur pendant
    qu'il tourne. S.
  - G4 Sauvegardes : avant une annulation, `undo_last` sauvegarde sous le nom du dossier parent (souvent « scenery ») ;
    la limite de 10 sauvegardes efface celles d'autres scènes ; `backup_files` range tout à plat (deux fichiers de
    même nom dans deux sous-dossiers s'écrasent). S.
  - G5 Archives : aucun plafond sur le nombre de fichiers ni sur le total pour les .zip ; .7z contrôlé seulement après
    l'extraction (hérité de 0.6). S.
  - G6 `undo/` copie tout le .bgl renommé alors qu'il se retrouve par empreinte, sans plafond global (voir S8) :
    plusieurs Go possibles avec des « Tout OFF » sur une grosse collection. S.

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

## Livré

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
