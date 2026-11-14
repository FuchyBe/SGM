# Points d'accroche pour une application hôte (3AM) — demande du 2026-11-15

**Origine** : Fabian, conversation du projet 3AM (15 novembre 2026, 00 h 50) : « intégrer la dernière version de SGM »
dans 3AM, puis demande placée dans « Prêt » de cette feuille de route.
**Contexte** : 3AM — « Again, Another Addon Manager » (ex-Hangar, même auteur) embarque SGM dans un onglet
« Statics & GSX ». Jusqu'ici, 3AM modifiait sa propre copie de `statics_manager.py` (thème clair, contrôle de MSFS à
trois états, sources de bibliothèques…). Pour la 0.9.3 de 3AM, ces modifications sont réappliquées par un script
(`tools/appliquer_accroches_sgm.py` dans le dépôt de 3AM). Le but de cette demande : que **SGM porte lui-même ces
points d'accroche**, pour que la prochaine intégration soit une simple copie des deux fichiers.

**Règle d'or : aucun effet sur SGM seul.** Chaque accroche vaut `None` / `False` par défaut ; chaque jeton de
couleur vaut la couleur actuelle ; le rendu sombre de SGM reste identique au pixel près. Les tests de SGM doivent
passer sans changement de comportement.

Étude complète, côté 3AM : `docs/conception/sgm-0-7-integration.md` du dépôt de 3AM (§ 3, § 5, § 7).

| # | Demande | Détail |
|---|---|---|
| S1 | `HOST_REPLACE = None` | début de `_replace_window` : `if HOST_REPLACE: HOST_REPLACE(state); return` |
| S2 | `EXTRA_SOURCES = None` | fin de `find_sources` : sources supplémentaires `[(étiquette, chemin)]`, dédoublonnées, dans un `try/except` |
| S3 | `REAL_ROOTS = False` | `scan_all` : `scan_package(Path(os.path.realpath(p)) if REAL_ROOTS else p, …)` |
| S4 | `build_qss(C)`, `build_doc_css(C)` ; `QSS = build_qss(C)`, `DOC_CSS = build_doc_css(C)` | chaque couleur en dur de la feuille de style devient un jeton de `C` **dont la valeur est la couleur actuelle** ; tailles de police par `font_px` |
| S5 | `draw_check_mark(p, box, on, color)` et `Switch` aux jetons | dans SGM seul, garder l'aspect actuel : jeton `switch_off` = `#2A303C`, `SWITCH_MARKS = False` (3AM met son rouge et `True`) |
| S6 | couleurs en dur restantes | `dot_icon("#E07A72")` → `C["off_text"]` ; survol du cœur → `C["heart_hover"]` ; texte des licences → `C["doc_text"]` |
| S7 | `sim_state(sim)` à trois états (`ouvert` / `fermé` / `inconnu`) ; `sim_running` = `sim_state == "ouvert"` | même résultat pour SGM seul |
| S8 | plafond global des copies d'annulation (par exemple 500 Mo ; au-delà : pas de copie, contenu retrouvé par empreinte) | sécurité du disque |
| S9 | durcir `parse_usercfg` ; `setSizeGripEnabled(True)` sur `FoldersDialog` / `DocDialog` ; (option) texte d'aide sans le nom `SGM_data` en dur (champ `{data}`) | |
| S10 | **mode hôte : pas de mise à jour propre à SGM** | quand SGM est embarqué (`HOST_REPLACE` défini), la future mise à jour automatique de SGM (sujet n° 1 de « Prêt ») ne vérifie rien et n'installe rien : c'est l'hôte qui livre la version de SGM. Sinon elle remplacerait le mauvais exécutable |
| S11 | **confirmation quand l'état de MSFS est inconnu** | accroche `HOST_CONFIRM_SIM = None` : si `sim_state` répond `inconnu` avant une écriture, SGM appelle cette fonction (3AM demande à l'utilisateur de confirmer que MSFS est fermé) ; dans SGM seul, comportement actuel |
| S12 | **menu Aide en mode hôte** | accroche `HOST_HELP_ITEMS = None` (liste des entrées à garder) : 3AM garde Guide, Licences, Sauvegardes, Tout restaurer, Rapport d'analyse et retire Signaler, Proposer une idée, Don, À propos et le journal (ceux de 3AM s'appliquent) — choix de Fabian du 2026-11-15 |

Jetons de couleur à ajouter à `C` (valeurs sombres actuelles de SGM, + 1 nouveau) : `text2`, `hover`, `pressed`,
`accent_hover`, `accent_dis_bg`, `accent_dis_fg`, `accent_soft`, `accent_line`, `accent_pressed` (#183026, nouveau :
survol des boutons Tout ON / OFF), `sel`, `off_text`, `off_text_hover`, `off_line`, `off_soft`, `off_soft_hover`,
`warn_soft`, `warn_line`, `warn_soft_hover`, `blue_soft`, `blue_soft2`, `blue_line`, `banner_line`, `danger`,
`danger_hover`, `danger_pressed`, `danger_dis_bg`, `danger_dis_fg`, `on_danger`, `row_hover`, `scroll_hover`,
`doc_text`, `heart_hover`, `knob`, `track_dis`, `knob_dis`, `menubar`, `switch_off`.

**Effort** : S/M (environ 190 lignes). **Risque** : nul pour SGM seul si les valeurs par défaut sont respectées ;
le test de contrat de 3AM (`tests/test_sgm_contrat.py`) dira « déjà présent » pour chaque accroche reprise.
**Test** : `bash tests/run_tests.sh` ; captures avant / après de SGM seul (identiques) ; `SGM.exe` testé par Fabian.
