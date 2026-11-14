# Mise à jour automatique, journal et remontée intégrée — fiche de décision

Demande de Fabian (2026-11-14) : « une version avec mise à jour automatique dans le logiciel avec une remontée
des bugs, des logs et des suggestions intégrée ». **Faisable**, en 4 étapes livrables. Les étapes 3 et 4 ajoutent
un accès réseau : **décision de Fabian** requise (aujourd'hui SGM ne se connecte jamais à Internet).

## 1. Journal local (S, sans réseau)

- `SGM_data\logs\sgm.log` : démarrage, analyses, chaque bascule (scène, méthode, fichiers), erreurs avec trace.
- Rotation : 5 fichiers de 1 Mo. Chemins réduits au paquet de la scène (jamais `C:\Users\…`).
- Menu Aide › Ouvrir le journal. Le journal est joint au rapport de bug (étape 2).

## 2. Fenêtre « Signaler / Suggérer » intégrée (M, sans réseau)

- Formulaire dans SGM : type (bug / idée), description, étapes, cases « joindre le rapport d'analyse » et
  « joindre le journal » (cochées par défaut pour un bug), aperçu exact de ce qui sera envoyé.
- Envoi sans serveur : SGM prépare un `.zip` (description + rapport + journal), ouvre l'issue GitHub
  pré-remplie et le dossier du `.zip` à glisser dans la page. Fonctionne dès aujourd'hui, compte GitHub requis.

## 3. Envoi direct, sans compte GitHub (M + petit serveur) — décision de Fabian

- Un relais gratuit (ex. Cloudflare Worker) reçoit le formulaire et crée l'issue dans FuchyBe/SGM avec le jeton
  GitHub stocké côté serveur (jamais dans SGM). Limite de débit, taille maximale, filtre anti-spam.
- À prévoir : texte de confidentialité (ce qui est envoyé, où, combien de temps), consentement explicite à
  chaque envoi, aucune donnée envoyée sans clic.

## 4. Mise à jour automatique (M) — décision de Fabian

- Au lancement (option, une fois par jour maximum) : lecture des **GitHub Releases** de FuchyBe/SGM (dépôt public,
  aucun serveur à payer). Si une version plus récente existe : fenêtre avec le changelog, boutons « Mettre à jour »,
  « Plus tard », « Ignorer cette version ».
- Téléchargement de `SGM_beta_vX.Y.zip`, vérification de l'empreinte SHA-256 publiée dans la release, extraction
  dans un dossier temporaire, petit programme de mise à jour qui remplace les fichiers après la fermeture de SGM
  et relance. **`SGM_data` n'est jamais touché.** En cas d'échec : l'ancienne version reste en place.
- Prérequis : publier chaque version comme **GitHub Release** (la compilation peut le préparer, Fabian publie),
  idéalement signer `SGM.exe` (SmartScreen et antivirus se méfient d'un exe qui se met à jour seul).
- flightsim.to reste le canal principal ; la mise à jour automatique est une commodité.

## Décisions demandées à Fabian

1. Accepter un accès réseau **optionnel** (vérification des mises à jour) : oui / non.
2. Envoi direct des rapports via un relais (étape 3) ou seulement via GitHub (étape 2).
3. Publier les versions en **GitHub Releases** en plus de flightsim.to.
