# SPEC — StudyPlan

## Contexte
Les étudiants peinent à organiser leurs révisions entre plusieurs cours, examens et échéances.
StudyPlan permet à un étudiant d'importer ses supports de cours (PDF / Markdown), de déclarer ses échéances et ses disponibilités hebdomadaires, puis d'obtenir un planning de révision hebdomadaire généré automatiquement, suivi dans un tableau de bord et exportable vers un calendrier (`.ics`).
Le produit lui-même **n'appelle aucune API d'IA**. Tout le projet est réalisé en **une seule journée**.
Équipe de 3 : **Frontend** (Membre 1) · **Backend + BDD** (Membre 2) · **Planificateur + ICS** (Membre 3).

## MVP (les 5 blocs obligatoires)
1. **Import des cours** (PDF / Markdown) → chapitres proposés + heures estimées, validés par l'étudiant
2. **Échéances + disponibilités hebdomadaires**
3. **Générateur de planning hebdomadaire** (Python pur, testé)
4. **Export calendrier `.ics`**
5. **Front de suivi** : planning, dashboard, avancement

Parcours de démo : import → planning → `.ics` → dashboard.

## Notre touche perso
**Replanification automatique des séances manquées** : quand une séance est marquée `skipped`, `POST /api/planning/replan` redistribue ses heures restantes dans les prochains créneaux libres avant l'échéance, et le dashboard affiche un indicateur de retard.
*(À confirmer par l'équipe — voir Hors périmètre pour les alternatives.)*

## Hors périmètre
- Tout appel à une API d'IA / LLM dans le produit (la détection des chapitres repose uniquement sur des règles)
- Authentification et comptes multi-utilisateurs (un seul utilisateur local)
- Synchronisation Google Calendar / Outlook (export de fichier `.ics` uniquement)
- Répétition espacée, quiz, fiches de révision, notifications
- OCR pour les PDF scannés (ils sont refusés avec une erreur explicite)

## Stack
| Couche | Technologies |
|---|---|
| Frontend | Python, Streamlit (interface et graphiques natifs), Requests (appels à l'API) |
| Backend | Python 3.11+, FastAPI, SQLite, SQLAlchemy 2.x, Pydantic v2, PyMuPDF, python-multipart, Uvicorn |
| Planificateur | Module Python pur (`datetime`), `icalendar` |
| Tests | Pytest, httpx / TestClient FastAPI |

**Règles d'architecture**
- Le frontend n'accède **jamais** à SQLite : tout passe par l'API REST (préfixe `/api`).
- Le planificateur est un module Python indépendant (`planner/`), appelé uniquement par `backend/services/planning_service.py`.
- L'objet FastAPI doit être importable avec `from backend.main import app`.
- Lancement : `uvicorn backend.main:app --reload` (Swagger sur `/docs`) et `streamlit run frontend/app.py`.
- **Contrat d'API figé à 9h45** ; le frontend démarre sur des données factices jusqu'à ce que le backend soit prêt.

## Données
- **Course** : `id` (int, auto), `name` (str, 1–100 caractères après trim, unique), `description` (str, optionnel), `created_at`
- **Document** : `id`, `course_id`, `filename`, `uploaded_at`
- **Chapter** : `id`, `course_id`, `document_id` (optionnel), `parent_id` (optionnel, pour les sous-chapitres), `title` (str, non vide), `estimated_hours` (float ≥ 0), `difficulty` (int 1–5, défaut 3), `completed_hours` (float ≥ 0, défaut 0)
- **Deadline** : `id`, `course_id`, `title`, `type` (`exam` | `assignment` | `other`), `due_date` (datetime ISO), `coefficient` (float > 0, défaut 1)
- **Availability** : `id`, `weekday` (int 0 = lundi … 6 = dimanche), `start_time` (`HH:MM`), `end_time` (`HH:MM`, strictement après `start_time`)
- **StudySession** : `id`, `chapter_id`, `start_datetime`, `end_datetime`, `status` (`planned` | `done` | `skipped`, défaut `planned`)

Relations : un Course a plusieurs Documents, Chapters et Deadlines ; un Chapter a plusieurs StudySessions ; supprimer un Course supprime ses Chapters (cascade).

## Endpoints
| Méthode | Chemin | Succès | Erreurs |
|---|---|---|---|
| POST | `/api/courses` body `{name, description?}` | **201** JSON du cours | **422** body invalide · **409** nom déjà utilisé |
| GET | `/api/courses` | **200** liste des cours | — |
| GET | `/api/courses/{id}` | **200** JSON du cours | **404** id inconnu |
| POST | `/api/chapters` body `{course_id, title, estimated_hours, difficulty?, parent_id?}` | **201** JSON du chapitre | **404** cours inconnu · **422** body invalide (ex. heures négatives) |
| GET | `/api/chapters?course_id=` | **200** liste des chapitres (filtre optionnel) | — |
| POST | `/api/documents/analyze` multipart `{file (PDF ou Markdown), course_id}` | **200** structure proposée `[{title, level, page?, estimated_hours}]` (rien n'est enregistré) | **404** cours inconnu · **415** fichier ni PDF ni Markdown · **422** fichier vide, scanné ou corrompu |
| POST | `/api/deadlines` body `{course_id, title, type, due_date, coefficient?}` | **201** JSON de l'échéance | **404** cours inconnu · **422** body invalide |
| GET | `/api/deadlines` | **200** liste triée par `due_date` croissante | — |
| POST | `/api/availability` body `{weekday, start_time, end_time}` | **201** JSON de la disponibilité | **422** body invalide (`end_time` ≤ `start_time`, weekday hors plage) |
| GET | `/api/availability` | **200** liste des disponibilités | — |
| POST | `/api/planning/generate` | **201** liste des séances générées | **400** aucune disponibilité ou aucun chapitre |
| POST | `/api/planning/replan` | **200** liste des séances mise à jour | **400** rien à replanifier |
| GET | `/api/planning?week=YYYY-MM-DD` | **200** séances triées par `start_datetime` (filtre semaine optionnel) | — |
| PATCH | `/api/planning/sessions/{id}/status` body `{status}` | **200** JSON de la séance | **404** séance inconnue · **422** statut invalide |
| GET | `/api/plan.ics` | **200** fichier `text/calendar` (pièce jointe) | **400** aucune séance à exporter |
| GET | `/api/dashboard` | **200** JSON des indicateurs (voir Règles) | — |
| GET | `/health` | **200** `{"status": "ok"}` | — |

Fournis aussi pour le frontend : `PUT` et `DELETE` sur `courses`, `chapters`, `deadlines` et `availability` (**200/204**, **404** si id inconnu).

## Règles
- **Analyse à l'import** : PDF via PyMuPDF (texte page par page ; titres détectés par la taille de police, le gras et les motifs de numérotation `1.`, `1.1`, `Chapitre X`) ; Markdown via les niveaux de titres `#`. `level` 1 = chapitre, 2 = sous-chapitre. Aucune IA impliquée.
- **Heures estimées** : proposées d'après la quantité de contenu de chaque chapitre (pages pour un PDF, mots pour un Markdown, avec un ratio fixe simple). Ce n'est qu'une suggestion : l'étudiant la modifie avant d'enregistrer les chapitres via `POST /api/chapters`.
- **Génération du planning** : charge les chapitres, échéances et disponibilités, appelle le planificateur, **remplace les séances `planned` existantes** (conserve les `done` / `skipped`), enregistre et retourne les nouvelles séances. Le planning est organisé par semaine.
- **Statut d'une séance** : quand une séance passe à `done`, le `completed_hours` du chapitre augmente de la durée de la séance.
- **Garanties du planificateur** (Membre 3) : aucun chevauchement entre séances, séances uniquement dans les créneaux de disponibilité, aucune séance après son échéance, priorité calculée selon la proximité de l'échéance, le coefficient, la difficulté et les heures restantes ; un temps disponible insuffisant est signalé, pas masqué.
- **Dashboard** retourne : `total_courses`, `total_chapters`, `total_sessions`, `sessions_done`, `sessions_planned`, `sessions_skipped`, `completion_rate` (%), `total_hours_planned`, `total_hours_done`, `upcoming_deadlines` (les 5 plus proches), `progress_by_course`, `late_hours` (heures manquées non encore replanifiées).
- **Erreurs** : JSON uniforme `{"detail": "..."}`, aucune stack trace exposée. CORS autorisé pour `http://localhost:8501`.

## Contrat Backend ↔ Planificateur (à valider avec le Membre 3 avant 9h45)
Entrée : chapitres `{id, title, course_id, estimated_hours, completed_hours, difficulty}`, échéances `{course_id, due_date, coefficient}`, disponibilités `{weekday, start_time, end_time}`.
Sortie : séances `{chapter_id, start_datetime, end_datetime}`.
ICS : un événement par séance, généré avec `icalendar` par `planner/calendar.py`.

## Structure du projet
```
backend/   main.py · database.py · models.py · schemas.py · api/routes/ · services/ (pdf_reader.py, markdown_reader.py, planning_service.py)
frontend/  app.py · api_client.py · pages/ · components/
planner/   scheduler.py · priority.py · constraints.py · calendar.py
tests/ · docs/ · sample_data/
README.md · SPEC.md · AI_LOG.md · CLAUDE.md · .github/copilot-instructions.md · requirements.txt · .gitignore
```

## Definition of Done
1. `pytest tests -q` → tout est vert, **au moins 10 tests pertinents** (objectif : 20) couvrant planificateur, `.ics` et API.
2. Le parcours de démo fonctionne en direct : import → planning → `.ics` → dashboard.
3. `README.md` : un inconnu lance le back et le front en moins de 5 minutes.
4. `SPEC.md` et `.github/copilot-instructions.md` (avec le contrat d'API) écrits **avant** de coder.
5. `AI_LOG.md` : au moins 5 entrées, dont **au moins un « échec de l'IA »** détecté et corrigé.
6. Historique Git propre : petits commits (`feat:`, `fix:`, `test:`, `docs:`), **chaque membre commite**, une branche par membre fusionnée dans `develop` après les tests, `main` = versions validées uniquement.
7. `.gitignore` exclut la base locale, les documents personnels et les secrets.
8. Journée : Sprint 0 avant 9h45 (spec, copilot-instructions.md, dépôt, squelettes) · 9h45 contrat figé / Sprint 1 · 11h00 Sprint 2 + point mentor · 13h45 Sprint 3 · **15h00 gel du code**, puis répétition de la démo (8 min + 2 min de questions).
