# Audit de l'interface — revue qualité du 2026-11-18

Agent : designer-interface. Branche `qualite/2026-11-18`. Scènes de démonstration de `scripts/capture_ui.py`.

## Captures

| Langue | 1280 × 900 (avant) | Après correction | 1024 × 700 (avant) | Après correction |
|---|---|---|---|---|
| en | `en.png` | `en-apres.png` | — | — |
| fr | `fr.png` | `fr-apres.png` | `fr-1024.png` | `fr-1024-apres.png` |
| de | `de.png` | `de-apres.png` | `de-1024.png` | `de-1024-apres.png` |
| ar | `ar.png` | `ar-apres.png` | — | — |
| ja | `ja.png` | `ja-apres.png` | — | — |

Vérification en plus (non rangée) : ru et pt en 1024 × 700, pour contrôler la flèche du bouton « Profils de statics »
avec des libellés longs.

**Avis : Interface OK après correction** : un défaut corrigé (flèche de menu invisible en arabe), aucun texte coupé sans
info-bulle, aucun chevauchement, l'arabe est bien aligné à droite. Les autres points touchent à la disposition ou au
choix des couleurs : ce sont des idées pour Fabian, non codées.

## Problèmes, par priorité

### 1. Majeur, corrigé : flèche du bouton « Profils de statics » invisible en arabe
- Capture : `ar.png` (barre d'outils, bouton `ملفات إعداد statics`) → `ar-apres.png`.
- En arabe (RTL), Qt dessinait la flèche de menu hors du bouton : rien n'indiquait que le bouton ouvre un menu.
- Correction : une ligne de QSS (`QPushButton::menu-indicator`, origine `border`, `right: 6px`), sans nouvelle
  couleur. Vérifiée en en, de, ja, ru, pt et ar : la flèche est à droite (à gauche en arabe) et ne touche pas le texte.

### 2. Moyen, corrigé (texte) : la restauration de l'état d'origine est introuvable pour un nouvel utilisateur
- Parcours « restaurer » : la seule entrée par scène est le **clic droit** sur la ligne ; rien à l'écran ne le dit.
  L'info-bulle de la ligne disait seulement « Double-clic : ouvrir le dossier ».
- Correction : l'info-bulle de la ligne (`tip_dblclick`) ajoute « Clic droit : restaurer l'état d'origine », dans
  les 12 langues, avec les mêmes mots que le menu (`ctx_restore`) et le guide intégré.
- Reste une idée (« À trier ») : rendre la restauration visible sans clic droit.

### 3. Moyen, idée : « Statics OFF » en gris, alors que la règle dit rouge = inactif
- Captures : `fr.png`, `en.png` (lignes KDFW, EGLL, LFPG ; compteur « 3 OFF » en haut à droite).
- « Statics ON » est vert, « À vérifier » orange, « GSX » bleu, mais « Statics OFF » et le compteur « OFF » sont
  gris. Seul le point de « Tout OFF » est rouge. C'est sans doute voulu (OFF n'est pas une erreur), mais ce n'est
  pas écrit dans `docs/DECISIONS.md`. **Question pour Fabian** : garder le gris (sobre, OFF n'est pas un danger) ou
  passer au rouge atténué ? Pas de changement sans décision.

### 4. Moyen, idée : « Nouvelles scènes » ressemble à un bouton d'action
- Captures : toutes (à droite de la recherche).
- C'est un filtre (afficher seulement les scènes nouvelles), mais il a l'aspect des boutons d'action « Dossiers »,
  « Analyser ». Hésitation possible : « est-ce que ça installe des scènes ? ». Piste : aspect de puce de filtre
  (comme les filtres de colonnes) ou placement dans la ligne des filtres. Changement de disposition → idée.

### 5. Moyen, idée : écran 1024 × 700 : seulement 4 lignes visibles
- Captures : `fr-1024.png`, `de-1024.png`.
- L'en-tête, deux barres d'outils et le bandeau « Première analyse » prennent environ 300 px. Le bandeau se ferme
  (×), donc c'est surtout vrai au premier lancement. Piste : réunir recherche et boutons sur une seule ligne sous
  1100 px, ou un mode compact des lignes. Changement de disposition → idée.

### 6. Mineur : choix entre plusieurs versions GSX (ligne LFPG)
- Captures : `en.png`, `fr.png` (« FULL », « LITE », « 2 versions disponibles · aucune installée »).
- Rien ne dit qu'il faut cliquer sur une version pour l'installer (l'info-bulle le dit : `var_tip_neutral`). Les
  puces sont neutres (ni bleu, ni orange). Piste : note « Cliquer une version pour l'installer » ; à voir avec le
  traducteur pour la longueur (≈ 45 caractères en anglais). Non fait : la note actuelle est déjà à la limite en de.

### 7. Mineur, traducteur : pluriels « scène(s) », « scenery(ies) », « Szenerie(n) »
- Captures : bandeau et barre d'état de toutes les langues.
- « 7 scenery(ies) detected » est lourd en anglais. Piste : « Sceneries detected: 7 » (le nombre après les deux
  points évite le pluriel). Touche ≈ 20 clés dans 12 langues : à confier à l'agent traducteur, pas fait ici.

### 8. Mineur, traducteur : japonais, termes mêlés pour « statics »
- Capture : `ja.png`. En-tête « 静的機 », état « Statics ON », bouton « statics プロファイル » (minuscule), note
  « statics ファイル ». Conforme au glossaire (`docs/i18n/GLOSSAIRE.md`) mais peu homogène. À vérifier par
  une relecture native (idée déjà « À trier »).

## Points vérifiés sans problème
- Aucun texte coupé dans les colonnes fixes (en, fr, de, ar, ja ; 1280 et 1024). À 1024, « Tout OFF / Tout ON »
  devient « OFF / ON » (forme courte prévue).
- Arabe : tout est aligné à droite, colonnes et menus en miroir, interrupteurs en miroir, noms de fichiers
  (`.bgl ↔ .bgl.off`) isolés en gauche-à-droite par `ltr_fragments`.
- Couleurs : vert = ON, orange = À vérifier (texte et note), bleu = GSX (« Copier dans GSX », compteur), sans
  couleur codée en dur repérée dans les captures.
- Les boutons de la barre d'outils gardent une taille cohérente d'une langue à l'autre ; aucun ne déborde à 1024 px
  (de, fr, ru, pt).

## Parcours d'un nouvel utilisateur : hésitations notées

| Étape | Ce qu'il voit | Hésitation possible | Suite |
|---|---|---|---|
| Premier lancement | Bandeau « Première analyse : 7 scènes… », liste remplie | Aucune ; le bandeau est clair | — |
| Comprendre l'état | « Statics ON » vert, « Statics OFF » gris, « À vérifier » orange | OFF gris : actif ou désactivé ? Le texte suffit | Point 3 |
| Cas « À vérifier » | Interrupteur grisé + icône dossier | Pourquoi grisé ? L'info-bulle explique (`tip_manual`) | — |
| Basculer | Interrupteur sur la ligne, retour dans la barre d'état, « Annuler » | Aucune | — |
| Installer un profil GSX | « Installer un profil GSX… », « Copier dans GSX », puces FULL/LITE, lien flightsim.to | Trois façons différentes ; FULL/LITE sans verbe | Point 6 |
| Restaurer | Clic droit sur la ligne ou menu Outils › « Tout restaurer à l'origine… » | Clic droit non signalé | Point 2 (corrigé en partie) |
| Signaler un problème | Aide › Signaler un problème | Aucune ; le formulaire explique qu'un compte GitHub est nécessaire | — |
