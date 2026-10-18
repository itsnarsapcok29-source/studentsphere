# StudentSphere — Internship Submission Pack
Developer: Narendra Vishnoi · EWB Edu Tech Pvt. Ltd. · Python Backend Development

## 1. Architecture explanation
Request flow: **Browser (fetch) → FastAPI router → service layer → SQLAlchemy ORM → SQLite**, and back as Pydantic-validated JSON.

| Layer | File | Responsibility |
|---|---|---|
| Entry | `app/main.py` | Creates the app, CORS, static files, routers, `/health`, dashboard page, creates tables on start |
| Config | `app/config.py` | Reads settings/env vars; builds an absolute DB path so the CWD never matters |
| DB | `app/database.py` | Engine, `SessionLocal`, `get_db()` dependency (opens a session per request and always closes it) |
| Model | `app/models.py` | `Student` table and constraints |
| Schemas | `app/schemas.py` | Validation rules + response shapes |
| Routers | `app/routers/*.py` | HTTP only: parse request, call service, return response |
| Services | `app/services/*.py` | Business rules, duplicate checks, queries, statistics, AI operations |
| Errors | `app/exceptions.py` | `StudentNotFoundError`→404, `DuplicateStudentError`→409, validation→422, DB/unknown→safe 500 |
| UI | `templates/`, `static/` | Single-page dashboard using hash routes and `fetch` |

How a record is **created**: the form posts JSON → Pydantic validates/cleans it → service checks duplicate ID/email → ORM `INSERT` → commit → 201 with the saved record.
**Updated**: PUT replaces all fields; PATCH changes only supplied fields (`exclude_unset`); uniqueness is re-checked excluding the record itself; `updated_at` refreshes automatically.
**Deleted**: UI asks for confirmation → `DELETE /students/{id}` → row removed → 204.

## 2. Database schema (table `students`)
| Column | Type | Rules |
|---|---|---|
| id | INTEGER | Primary key, autoincrement (internal) |
| student_id | VARCHAR(20) | NOT NULL, UNIQUE, indexed (public ID) |
| full_name | VARCHAR(100) | NOT NULL, indexed |
| date_of_birth | DATE | NOT NULL, must be in the past |
| email | VARCHAR(254) | NOT NULL, UNIQUE (also checked case-insensitively) |
| phone | VARCHAR(20) | optional |
| course | VARCHAR(100) | optional, indexed |
| address | TEXT | optional (max 500 enforced by API) |
| enrollment_date | DATE | optional |
| created_at / updated_at | DATETIME | UTC, automatic |

## 3. API endpoints
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /students | 201 | 409, 422 |
| GET | /students | 200 (search, course, enrolled_from/to, born_after/before, sort_by, order, page, page_size) | 422 |
| GET | /students/{student_id} | 200 | 404 |
| PUT | /students/{student_id} | 200 | 404, 409, 422 |
| PATCH | /students/{student_id} | 200 | 404, 409, 422 |
| DELETE | /students/{student_id} | 204 | 404 |
| GET | /health, /, /docs, /redoc | 200 | |
| GET | /api/stats, /api/courses | 200 | |
| GET/POST | /api/ai/status, /api/ai/ask | 200 | 503 if disabled |

## 4. Testing report (actual results)
- Automated: `pytest` → **27 passed, 0 failed** (run in the build environment, Python 3.12).
  Covers create, list, get, PUT, PATCH, delete, 404s, invalid input, duplicate ID/email, search (name/ID/email/phone, wildcard safety), filters, pagination/sorting, stats, persistence via a fresh DB connection, health/docs/dashboard, and AI (allowlist, offline fallback, no modification).
- Manual browser test (Chromium via Playwright, real server, real SQLite): dashboard stats, table, search, inline validation, duplicate-ID message, add, edit, profile modal, delete confirmation, empty state, AI assistant, mobile layout — all behaved correctly. The only browser console error was the expected 409 from the duplicate test.
- **Not tested:** real Ollama responses (Ollama was not installed in the build environment; the offline fallback and the model-text path were tested with a mock). Test this yourself after installing Ollama.

## 5. Install guide
See README "Setup (Windows PowerShell)".

## 6. GitHub publication guide
```powershell
git init
git add .
git status                      # confirm NO .env and NO *.db appear
git commit -m "Initial commit: StudentSphere"
# Create an empty repo on github.com (no README), then:
git branch -M main
git remote add origin https://github.com/<your-username>/studentsphere.git
git push -u origin main
```
Submit the repository URL via the channel announced by your EWB trainer. Do not commit `.env`, `data/*.db`, or real student data (already git-ignored).

## 7. Demonstration script (~6 minutes)
1. **(0:00)** Introduce: problem, stack (FastAPI, SQLite, SQLAlchemy), requirement list from the assignment.
2. **(0:45)** Show folder structure; explain router → service → ORM layering.
3. **(1:30)** Open `/docs`: run POST (create), GET list, GET one, PATCH, DELETE live; show a 404 and a 422.
4. **(3:00)** Open the dashboard: statistics, add a student via the form (show inline validation, then success toast).
5. **(4:00)** Students page: search, filter, sort, pagination; view profile; edit; delete with confirmation. Try a duplicate ID → 409 message.
6. **(5:00)** Stop the server, restart, show the record persisted (SQLite).
7. **(5:30)** Run `pytest -v` (27 pass). Mention the optional Ollama assistant and its safety design; ask it one question.
8. **(6:00)** Close: limitations (no auth) and future work.

## 8. Viva questions and answers
1. **What is CRUD?** Create, Read, Update, Delete — the four basic data operations, mapped to POST, GET, PUT/PATCH, DELETE.
2. **Why FastAPI?** Fast, type-hint based, automatic validation, and auto-generated Swagger docs.
3. **What is SQLite?** A serverless file-based SQL database; one file (`data/students.db`), no server to install.
4. **Why SQLAlchemy ORM?** Maps tables to Python classes, prevents SQL injection by parameterising queries, and keeps code readable.
5. **What is Pydantic?** A validation library; schemas declare field types/rules and reject bad data automatically with 422.
6. **PUT vs PATCH?** PUT replaces the whole resource (all required fields needed); PATCH changes only the fields sent.
7. **Why is student_id a string and separate from `id`?** It is the human-facing business identifier (e.g. STU-1001); `id` is an internal key.
8. **How do you prevent duplicates?** DB `UNIQUE` constraints plus a service-level check giving a friendly 409; the DB constraint also catches race conditions.
9. **Why 409 and not 400?** 409 means the request conflicts with the current state (existing record).
10. **Difference between 404 and 422?** 404: the resource doesn't exist. 422: the request data is syntactically valid JSON but fails validation.
11. **What is dependency injection here?** `Depends(get_db)` supplies a DB session to each request and guarantees it is closed.
12. **How is SQL injection prevented?** Only ORM expressions with bound parameters are used; LIKE wildcards in search are escaped.
13. **How is XSS prevented?** Every user value rendered in the UI goes through an `esc()` function; the AI chat uses `textContent`.
14. **How does pagination work?** `OFFSET (page-1)*page_size LIMIT page_size`, with a separate COUNT query for totals.
15. **How do you keep data after restart?** Data lives in the SQLite file, not in memory; tables are created only if missing.
16. **Why an absolute DB path?** So the database is found regardless of which directory you start the server from.
17. **Why a service layer?** Keeps routers thin, avoids duplicated logic and makes logic testable.
18. **How do tests avoid touching real data?** A fixture creates a temp SQLite file per test and overrides `get_db`.
19. **How does the AI feature stay safe?** Question → allowlisted operation → ORM query → model only rephrases the verified result; no SQL from the model and no write operations.
20. **What if Ollama is not running?** The deterministic database answer is returned with a notice; the rest of the app is unaffected.
21. **Why is CORS restricted?** Only the app's own origins are allowed so other websites can't call the API from a browser.
22. **What are the limitations?** No authentication, SQLite concurrency limits, no migrations.
23. **How would you add authentication?** Add a users table with hashed passwords (e.g. bcrypt/argon2), JWT or session cookies, and a dependency that protects the routes.
24. **How would you move to PostgreSQL?** Change `DATABASE_URL` and install a driver; the ORM code stays the same (add Alembic for migrations).
25. **What does `/health` do?** Runs `SELECT 1` to confirm the app and database are reachable.

## 9. Common errors and fixes
| Problem | Fix |
|---|---|
| `python` not found | Reinstall Python and tick "Add to PATH", or use `py` |
| Activate.ps1 blocked | `Set-ExecutionPolicy -Scope Process Bypass` |
| `ModuleNotFoundError` | Activate the venv and run `pip install -r requirements.txt`; run commands from the project root |
| Port 8000 busy | `uvicorn app.main:app --port 8001` |
| Page shows "Server unavailable" | The server isn't running or crashed — check the terminal |
| 409 when saving | Student ID or email already exists |
| `no such table` | Run `python -m scripts.init_db` |
| `database is locked` | Close other programs (DB browsers) using the file |
| AI says model unavailable | Start Ollama and run `ollama pull llama3.2:1b` |
| Reset everything | Stop the server, delete `data/students.db`, rerun init/seed |

## 10. Requirement checklist (assignment PDF)
| Requirement | Status | Where |
|---|---|---|
| Create student | ✅ | `POST /students`, Add form |
| Read: list + retrieve/filter | ✅ | `GET /students`, `GET /students/{id}`, table, profile |
| Update | ✅ | `PUT` and `PATCH`, Edit form |
| Delete | ✅ | `DELETE`, confirmation dialog |
| Python + FastAPI + SQLite | ✅ | whole project |
| Fields: unique ID, name, DOB, email/phone | ✅ | `models.py`, `schemas.py` |
| Optional fields: course, address, enrollment date | ✅ | optional in schema |
| Suggested endpoints | ✅ | `app/routers/students.py` |
| Data persists in SQLite | ✅ | `test_data_persists_across_connections` |
| Validation + missing-record handling | ✅ | 422 / 404 tests |
| Organized code + reproducible README | ✅ | README |
| requirements.txt, sample requests | ✅ | `requirements.txt`, `requests.http` |
| No secrets / real personal data | ✅ | `.gitignore`, dummy seed data |
| Optional: Ollama, grounded answers, no unrestricted SQL | ✅ (built; verify with real Ollama) | `ai_service.py` |

## 11. Resume description
**StudentSphere — Student Database Management System** (Python, FastAPI, SQLAlchemy, SQLite) — Built a REST API with full CRUD, validation, search/filter/pagination and conflict handling, plus a responsive admin dashboard consuming the API. Wrote 27 pytest tests with isolated databases and an optional read-only local-LLM (Ollama) assistant using allowlisted queries. Internship project, EWB Edu Tech Pvt. Ltd.
