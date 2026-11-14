---
name: sprint
description: Développe le premier sujet de la section « Prêt » de docs/ROADMAP.md de SGM et ouvre une PR à tester par Fabian, avec le lien direct vers SGM.exe.
---

# Sprint SGM

1. **Conditions** — Arrête-toi (une ligne d'explication) si :
   - la section « Prêt » de `docs/ROADMAP.md` est vide ;
   - une PR `sprint/…` est déjà ouverte (`gh api "repos/FuchyBe/SGM/pulls?state=open" --jq '.[] | select(.head.ref|startswith("sprint/")) | .number'`) : Fabian doit d'abord la tester.
2. **Branche** — `git switch -c sprint/AAAA-MM-JJ-<sujet-court>` depuis `main` à jour.
3. **Interface d'abord** — Si le sujet change quelque chose de visible, appelle l'agent **designer-interface** :
   proposition + maquette/capture. Un nouvel écran ou une réorganisation attend l'accord de Fabian : ouvre alors
   la PR en brouillon avec la question et arrête-toi.
4. **Développement** — Appelle l'agent **developpeur** (moteur) avec le sujet complet ; le **designer-interface**
   réalise ou relit la partie visible. Lis `docs/analyses/BASE.md` si le sujet touche aux règles des statics.
5. **Tests** — Appelle l'agent **testeur** sur le diff (cas limites, cas réels de `BASE.md`).
6. **Captures** — Pour un changement visible : le **designer-interface** fait les captures (en, fr, de, ar, ja) avec
   `scripts/capture_ui.py` dans `docs/captures/<branche>/` et donne son avis « Interface OK ».
7. **Relecture** — Appelle l'agent **gardien-securite**. Si « Bloquant » ou « À corriger », fais corriger par
   **developpeur** puis redemande l'avis (2 tours maximum ; sinon PR en brouillon avec la question pour Fabian).
8. **ROADMAP** — Déplace le sujet de « Prêt » vers « En cours (PR à tester) ».
9. **Tests** — `bash tests/run_tests.sh` vert.
10. **PR** — Commit(s) clairs en français, `git push -u origin <branche>`, puis `gh api repos/FuchyBe/SGM/pulls -f title=… -f head=<branche> -f base=main -F body=@fichier.md`
   avec le modèle `.github/pull_request_template.md` : résumé, **À tester dans MSFS** (cases à cocher concrètes),
   avis du gardien, avis interface et captures, questions pour Fabian.
11. **Lien de l'exe** — Attends la fin de la compilation (`gh run list -R FuchyBe/SGM --branch <branche>` puis `gh run watch <id> -R FuchyBe/SGM`, 20 min max) ; l'id de l'artefact : `gh api repos/FuchyBe/SGM/actions/runs/<id>/artifacts`. Récupère le
   lien de l'artefact `SGM-exe` dans le commentaire « SGM.exe à tester » de la PR (lecture seule).
12. **Résumé** (5 lignes max) : sujet, lien de la PR, **lien direct SGM.exe**, ce qu'il faut tester, question éventuelle.

Interdits : pousser sur `main`, fusionner, créer une release ou un tag, commenter ou étiqueter sur GitHub.
