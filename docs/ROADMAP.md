# Feuille de route de SGM

Règles : les agents ajoutent les idées dans **À trier**. **Seul Fabian** déplace un sujet dans **Prêt**
(en le gardant tel quel ou en le précisant). Le sprint du matin prend le premier sujet de « Prêt ».

## Prêt

_(vide — Fabian déplace ici les sujets à développer, dans l'ordre souhaité)_

## En cours (PR à tester)

_(vide)_

## À trier

Chaque sujet : titre, origine, bénéfice pour l'utilisateur, estimation (S/M/L), risque.

- **Vérifier l'adresse de recherche flightsim.to** — origine : beta v0.6. Le format
  `flightsim.to/search/?keyword=` n'a pas pu être vérifié. Bénéfice : bouton de recherche fiable. S. Risque faible.
- **Tester .7z et .rar avec 7-Zip** — origine : beta v0.6. Extraction non testée faute de 7-Zip dans
  l'environnement de développement. Bénéfice : fiabilité de l'installation d'archives. S. Risque faible.
- **Signature de l'exécutable** — origine : publication. SmartScreen et certains antivirus signalent un exe
  non signé. Bénéfice : confiance des utilisateurs. M (coût d'un certificat : décision de Fabian). Risque nul.
- **Annuler la dernière action** — origine : idée. Restaurer la dernière sauvegarde d'une scène ou d'un profil
  GSX depuis l'interface. Bénéfice : sécurité perçue. M. Risque moyen (fichiers).
- **Profils de statics** — origine : idée. Enregistrer un jeu d'états ON/OFF (« Trafic IA dense », « Vols
  photo ») et l'appliquer d'un clic. Bénéfice : confort. M. Risque faible.
- **Relecture native des traductions** (ar, zh, ja surtout) — origine : publication. S. Risque nul.

## Livré

- **beta v0.6** — aéroports sans profil, profils installés à la main, recherche flightsim.to, catégories,
  installation de profils depuis une archive, menu Signaler un problème.
- **beta v0.5** — première version publique.
