# Audit de l'interface — revue qualité du 2026-11-25

Agent : designer-interface. Branche `qualite/2026-11-25`, i18n.py avec les 49 corrections du traducteur.
Captures faites avec `scripts/capture_ui.py` (scènes de démonstration).

## Captures

| Fichier | Langue | Taille | Contenu |
|---|---|---|---|
| `en.png`, `fr.png`, `de.png`, `ar.png`, `ja.png` | 5 langues | 1280 × 900 | fenêtre principale |
| `fr-1024.png`, `de-1024.png` | fr, de | 1024 × 700 | fenêtre étroite (en-tête compact) |
| `nl.png`, `es.png`, `it.png` | nl, es, it | 1280 × 900 | textes revus par le traducteur |
| `nl-a-verifier.png`, `nl-a-verifier-1024.png`, `es-a-verifier.png`, `ar-a-verifier.png` | nl, es, ar | 1280 / 1024 × 500 | filtre Statics « À vérifier » actif, scène en conflit `.bgl` + `.bgl.off` (scène ajoutée seulement pour la capture) |
| `ar-barre-x3.png` | ar | agrandie × 3 | barre d'outils : flèche du menu absente |
| `test-fleche-menu-rtl.png` | — | agrandie × 4 | essais QSS de la flèche de menu (gauche : LTR, droite : RTL) |

## Textes signalés par le traducteur

| Texte | Résultat |
|---|---|
| `st_conflict` / `fst_check` : nl « Te controleren », de « Zu prüfen », es « Por revisar » | OK : pastille et liste de filtre sans coupure, même à 1024 (`nl-a-verifier-1024.png`). |
| `f_check` | **Clé inutilisée** dans le code (le filtre affiche `fst_check` / `fgx_check`). Rien à voir à l'écran. |
| `f_new` : nl « Nieuwe scenery's », de « Neue Szenerien », ar « مشاهد جديدة » | OK, bouton à la bonne largeur. |
| `btn_profiles` : it « Profili degli statics », ar « ملفات إعداد statics » | Texte OK. **En arabe, la flèche du menu manque** (voir P1). |
| `btn_undo` nl « ↶ Ongedaan maken » | OK. |
| `note_conflict` nl « .bgl en .bgl.off beide aanwezig — te controleren » | OK à 1280 et 1024 ; ordre des noms de fichiers correct en arabe. |
| README : bouton « Profils » | Déjà corrigé : les deux README et le guide disent « Statics profiles » / « Profils de statics ». Rien à changer. |

## Problèmes, par priorité

### P1 — Arabe : la flèche du bouton « Profils de statics » n'est pas dessinée (bug Qt)
- Où : barre d'outils, `btn_profiles` (QPushButton avec menu). `ar.png`, `ar-barre-x3.png`.
- En RTL, Qt place l'indicateur de menu hors du bouton : la place est réservée, la flèche est invisible. Rien
  n'indique que le bouton ouvre un menu.
- Essais (`test-fleche-menu-rtl.png`) : aucune règle QSS unique ne marche dans les deux sens. La règle
  `QPushButton::menu-indicator { subcontrol-origin: content; subcontrol-position: right center; }` ajoutée
  **seulement en RTL** donne le bon rendu en arabe (ligne 1, droite) ; en LTR elle colle la flèche au texte
  (ligne 1, gauche), donc à ne pas appliquer en LTR. À vérifier sous Windows. Non corrigé (logique dépendant de
  la langue dans la construction de la feuille de style, accroche `build_qss` de 3AM) → idée « À trier ».

### P2 — Parcours : « Restaurer l'état d'origine » n'est accessible que par clic droit ou le menu Outils
- Un nouvel utilisateur qui a basculé une scène cherche à revenir en arrière : il trouve **Annuler** (bien),
  mais rien à l'écran n'indique le clic droit sur une ligne. L'info-bulle de ligne dit seulement
  « Double-clic : ouvrir le dossier ».
- Proposition (texte seulement) : compléter `tip_dblclick`, par ex. « Double-click: open folder · Right-click:
  restore original state » (12 langues, via le traducteur) → idée « À trier ».

### P3 — Couleur verte pour le filtre actif et « Réinitialiser les filtres »
- `nl-a-verifier.png` : le filtre « Te controleren » actif est encadré en **vert**, comme « Statics AAN », alors
  que l'état filtré est orange. Le lien « Filters wissen » est aussi vert. La règle de style réserve le vert à
  actif/ON ; le bleu (info) conviendrait mieux à un filtre actif. Changement de sens de couleur → décision de
  Fabian, idée « À trier ».

### P4 — Ligne « À vérifier » : interrupteur grisé sans explication directe
- `en.png`, ligne EBCI : interrupteur désactivé, petite icône dossier. L'explication est dans l'info-bulle de
  l'icône dossier, pas sur l'interrupteur. Un utilisateur clique d'abord l'interrupteur, sans réponse.
  Piste : même info-bulle (`tip_manual`) sur l'interrupteur désactivé. Petit changement de code → noté ici,
  à voir avec le développeur.

### P5 — Mineurs
- **Libellé d'annulation non traduit** : le libellé d'une bascule (info-bulle de « Annuler ») était écrit en dur
  « Statics ON/OFF — scène ». **Corrigé** (utilise `state_text`, identique en anglais).
- **Clés mortes** : `f_all`, `f_on`, `f_off`, `f_gsx`, `f_check` et la constante `FILTER_KEYS` ne sont plus
  utilisées. Le traducteur corrige des textes jamais affichés. Nettoyage possible (vérifier 3AM d'abord).
- **Japonais** : en-tête « 静的機 » mais états « Statics ON / OFF » et bouton « statics プロファイル » — mélange de
  termes, à trancher par le traducteur (glossaire).
- **Arabe** : la flèche « ↶ » d'Annuler n'est pas inversée (↷ attendu en RTL) — détail.
- **OFF** : état « Statics OFF » en gris neutre, mais pastille rouge devant « Tout OFF ». Cohérent avec l'idée
  « OFF n'est pas un danger », à confirmer par Fabian.
- **Japonais 1280 × 900** : lignes plus hautes, la dernière ligne passe sous le défilement — normal.

## Contrôles sans problème
- Aucun texte coupé dans les 8 langues à 1280, ni en fr / de / nl à 1024 (« Tout OFF / Tout ON » passe en
  « OFF / ON » avec info-bulle).
- Arabe : mise en page miroir correcte (menus, colonnes, défilement à gauche), noms de fichiers `.bgl ↔ .bgl.off`
  dans le bon ordre (isolement LRE/PDF de `ltr_fragments`), pastille orange lisible.
- Couleurs : vert = ON, orange = À vérifier, bleu = GSX (« Copier dans GSX », compteur GSX) respectés.
- Boutons de la barre d'outils : largeur adaptée à chaque langue sans casser la ligne.

## Parcours d'un nouvel utilisateur (hésitations)
1. **Premier lancement** : bandeau « Première analyse : 7 scènes… » clair. Le badge « MSFS 2024 » ne dit pas
   où changer de simulateur (Paramètres › Simulateur) — léger.
2. **Comprendre l'état** : ON vert / OFF gris / À vérifier orange lisibles ; la 2e ligne (méthode
   `.bgl ↔ .bgl.off`) est technique mais discrète. « Pas de statics » + « Aucun fichier statics dans la scène »
   répète la même information.
3. **Basculer** : interrupteur évident, retour dans la barre d'état. Ligne « À vérifier » : voir P4.
4. **Installer un profil GSX** : deux chemins (« Installer un profil GSX… » pour une archive, « Copier dans GSX »
   dans la ligne) ; les info-bulles les distinguent. Le bouton pointillé « flightsim.to ↗ » ouvre une recherche
   web — clair grâce à la flèche.
5. **Restaurer** : voir P2.
6. **Signaler un problème** : Aide › Signaler un problème, trouvé sans hésitation.

Avis : **Interface OK pour les textes du traducteur** ; un défaut visible en arabe (P1) et une piste
d'ergonomie (P2) proposés à Fabian.
