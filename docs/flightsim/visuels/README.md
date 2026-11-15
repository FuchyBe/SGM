# Visuels flightsim.to (beta v0.9.2)

Images 1920 × 1080, à téléverser dans cet ordre (la première sert de vignette) :

1. `1-hero.png` : logo, nom, poste de stationnement vu du ciel (statics ON / OFF)
2. `2-statics.png` : bascule des statics, capture de l'interface
3. `3-gsx.png` : profils GSX Pro
4. `4-securite.png` : sécurité (simulateur ouvert, Annuler, mise à jour vérifiée)

Les captures viennent de scènes de démonstration (`scripts/capture_flightsim.py`, éditeurs inventés).

Pour les refaire :
```
python scripts/capture_flightsim.py docs/flightsim/visuels/src/shots en
cd docs/flightsim/visuels/src && mkdir -p out && node shoot.js   # Playwright, Chromium
```
Police des panneaux : Barlow Condensed (licence SIL Open Font License), fichiers `.woff2` dans `src/`.
