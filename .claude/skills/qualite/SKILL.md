---
name: qualite
description: Revue qualité hebdomadaire de SGM — relecture des traductions (agent traducteur) et audit de l'interface (agent designer-interface) : clarté, intuitivité, textes coupés, rendu dans les 12 langues. Corrections sûres dans une PR, le reste en idées.
---

# Revue qualité SGM

1. **Traductions** — Appelle l'agent **traducteur** : `python scripts/check_i18n.py`, puis relecture des textes
   récents et d'une langue complète (rotation notée dans `docs/i18n/RELECTURE.md`).
2. **Interface** — Appelle l'agent **designer-interface** pour un audit :
   - captures `python scripts/capture_ui.py <langue> docs/captures/qualite-AAAA-MM-JJ/<langue>.png 1280 900`
     pour en, fr, de, ar, ja, et en 1024 × 700 pour de et fr ;
   - parcours d'un nouvel utilisateur : premier lancement, comprendre l'état d'une scène, basculer, installer un
     profil GSX, restaurer, signaler un problème. Note chaque hésitation possible ;
   - textes coupés, alignements, contrastes, cohérence des couleurs (vert / rouge / orange / bleu), arabe RTL ;
   - liste priorisée dans `docs/captures/qualite-AAAA-MM-JJ/AUDIT.md`.
3. **Corrections sûres** (textes, petits ajustements de style) : faites dans la même branche, avec tests verts.
   Tout changement de disposition ou nouvel écran : seulement en idée « À trier » avec capture, pour Fabian.
4. Si rien à corriger : arrête-toi avec « Qualité : rien à signaler cette semaine ».
5. Sinon : branche `qualite/AAAA-MM-JJ`, PR vers `main` avec captures, avis du gardien si du code a changé.
6. **Résumé** (5 lignes max) : nombre de corrections de traduction, problèmes d'interface majeurs en premier,
   lien de la PR, lien SGM.exe si le code a changé.
