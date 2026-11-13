---
name: sprint
description: Développe le premier sujet de la section « Prêt » de docs/ROADMAP.md de SGM et ouvre une PR à tester par Fabian, avec le lien direct vers SGM.exe.
---

# Sprint SGM

1. **Conditions** — Arrête-toi (une ligne d'explication) si :
   - la section « Prêt » de `docs/ROADMAP.md` est vide ;
   - une PR `sprint/…` est déjà ouverte (`gh pr list --state open --search "head:sprint/"`) : Fabian doit d'abord la tester.
2. **Branche** — `git switch -c sprint/AAAA-MM-JJ-<sujet-court>` depuis `main` à jour.
3. **Développement** — Appelle l'agent **developpeur** avec le sujet complet.
4. **Relecture** — Appelle l'agent **gardien-securite**. Si « Bloquant » ou « À corriger », fais corriger par
   **developpeur** puis redemande l'avis (2 tours maximum ; sinon PR en brouillon avec la question pour Fabian).
5. **ROADMAP** — Déplace le sujet de « Prêt » vers « En cours (PR à tester) ».
6. **Tests** — `bash tests/run_tests.sh` vert.
7. **PR** — Commit(s) clairs en français, `git push -u origin <branche>`, puis `gh pr create --base main`
   avec le modèle `.github/pull_request_template.md` : résumé, **À tester dans MSFS** (cases à cocher concrètes),
   avis du gardien, questions pour Fabian.
8. **Lien de l'exe** — Attends la fin de la compilation (`gh pr checks <n> --watch`, 20 min max). Récupère le
   lien de l'artefact `SGM-exe` dans le commentaire « SGM.exe à tester » de la PR (lecture seule).
9. **Résumé** (5 lignes max) : sujet, lien de la PR, **lien direct SGM.exe**, ce qu'il faut tester, question éventuelle.

Interdits : pousser sur `main`, fusionner, créer une release ou un tag, commenter ou étiqueter sur GitHub.
