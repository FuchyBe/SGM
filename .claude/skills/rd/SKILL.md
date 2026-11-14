---
name: rd
description: Recherche et développement de SGM — options demandées ou exclusives (agent recherche-developpement) et profils GSX (agent chercheur-gsx). Produit des fiches de décision et des idées « À trier » ; prototypes uniquement en PR brouillon.
---

# R&D SGM

1. **GSX** — Appelle l'agent **chercheur-gsx** : vérifie l'adresse de recherche flightsim.to, les nouveautés de
   GSX Pro, met à jour `docs/gsx/SOURCES.md` et `docs/gsx/CAS.md`.
2. **Options** — Appelle l'agent **recherche-developpement** avec : les demandes récentes (`docs/RETOURS.md`),
   la veille, et les sujets « À trier » marqués « R&D ». Une à deux fiches `docs/rd/` maximum par passage,
   en priorité ce que les utilisateurs demandent le plus.
3. Évite les doublons avec `docs/rd/` et la ROADMAP. Si rien de neuf : « R&D : rien de neuf cette semaine. »
4. Sinon : branche `rd/AAAA-MM-JJ`, PR de documentation vers `main` (un prototype éventuel va dans une **autre**
   PR, en brouillon, « ne pas fusionner »).
5. **Résumé** (5 lignes max) : les idées qui demandent une décision de Fabian en premier, lien des PR.
