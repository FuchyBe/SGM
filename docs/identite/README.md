# Identité visuelle de SGM

Propositions de l'agent `directeur-artistique`. Fabian choisit ; l'icône retenue est ensuite intégrée dans l'exe
(`SGM.ico` 16 → 256 px), la fenêtre, la barre des tâches, le README et la page flightsim.to.

Planche de choix : `planche-2026-11-14.png` (chaque icône de 16 à 256 px, sur fond sombre et clair).
Rendu : `python scripts/render_icons.py docs/identite/planche-AAAA-MM-JJ.png` (PNG individuels dans `png/`).

| | Proposition | Idée | Petites tailles (16–32 px) |
|---|---|---|---|
| **A** | Stand | Avion vu de dessus sur sa ligne de parking verte (avions statiques au stationnement) | Avion lisible, ligne verte discrète |
| **B** | Interrupteur | Bascule ON verte dont le bouton porte un avion : « statics ON/OFF en un clic » | **La plus reconnaissable** (forme de bascule) |
| **C** | Monogramme | « SGM » sur trois marques de piste (vert statics, bleu GSX) | Lettres illisibles sous 32 px |
| **D** | Service au sol | Avion dans un anneau vert (statics) et bleu (GSX) | Anneau bicolore reconnaissable, avion petit |

Toutes dessinées pour SGM, aux couleurs de l'application ; aucune marque ni logo de tiers.
Recommandation du directeur artistique : **B** pour la barre des tâches (lisible à 16 px, dit ce que fait l'outil),
ou **D** si l'on veut montrer les deux fonctions (statics + GSX).
