---
name: analyse
description: Traite les nouveaux rapports d'analyse des statics déposés dans docs/analyses/ : met à jour la base des cas réels (BASE.md), propose des règles de détection et leurs tests dans la ROADMAP, via une PR de documentation.
---

# Analyse des rapports de statics

1. **Nouveaux rapports** — Fichiers `docs/analyses/*.json` absents de la liste « Rapports traités » de
   `docs/analyses/BASE.md`. S'il n'y en a pas : arrête-toi (« Aucun nouveau rapport d'analyse »).
2. **Analyse** — Appelle l'agent **analyste-regles** avec la liste des nouveaux fichiers.
3. **Cas réels pour les tests** — Appelle l'agent **testeur** : il vérifie, sans modifier l'application, quelles
   familles de noms de `BASE.md` sont déjà couvertes par les tests et liste les tests à écrire (dans `BASE.md`,
   section « Tests à écrire »). Il n'ajoute des tests au code que pour des règles **déjà en place**.
4. **Fichiers** — `docs/analyses/BASE.md` (dont « Rapports traités »), « À trier » de `docs/ROADMAP.md`,
   éventuellement des tests pour les règles existantes. Aucun changement de `statics_manager.py`.
5. **Confidentialité** — Relis : aucun chemin complet, aucun nom d'utilisateur, aucun libellé de dossier personnel.
6. **PR** — branche `analyse/AAAA-MM-JJ`, PR vers `main`.
7. **Résumé** (5 lignes max) : nombre de scènes/éditeurs ajoutés à la base, cas où SGM se trompe (**en premier**),
   règles proposées, lien de la PR.
