# StudentSphere — Student Database Management System

A Python backend project built for the **EWB Edu Tech Pvt. Ltd.** Python Backend Development internship.
**Developer:** Narendra Vishnoi

StudentSphere manages student records with full CRUD through a **FastAPI** REST API backed by **SQLite**
(via SQLAlchemy), with a responsive web dashboard and an optional **local AI assistant (Ollama)**.

## Objectives
- Create, read, update and delete student records through a documented API.
- Persist data in SQLite so records survive restarts.
- Validate input and handle missing records and duplicates properly.
- Provide a real web UI that talks to the real API (no fake data).

## Features
- Full CRUD: `POST/GET/PUT/PATCH/DELETE /students`
- Search (name, ID, email, phone), course and enrollment-date filters, sorting, pagination, record counts
- Unique student ID and unique email (case-insensitive) → `409 Conflict`; invalid data → `422`; missing → `404`
- Dashboard with statistics computed from the database (nothing hardcoded)
- Add/edit form with inline validation, profile modal, delete confirmation dialog, toasts, empty/loading/error states
- Swagger (`/docs`) and ReDoc (`/redoc`), health check (`/health`)
- Optional read-only AI assistant: allowlisted queries only, model never touches SQL
- 27 automated pytest tests using a temporary database

## Technology stack
Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite, Jinja2, vanilla HTML/CSS/JavaScript (ES modules), pytest, Ollama (optional).

## Folder structure
```
studentsphere/
├── app/
│   ├── main.py              # app entry point, middleware, routes wiring
│   ├── config.py            # environment-based settings
│   ├── database.py          # engine, session dependency, init_db()
│   ├── models.py            # SQLAlchemy Student model
│   ├── schemas.py           # Pydantic request/response + validation
│   ├── exceptions.py        # custom errors + global handlers
│   ├── routers/
│   │   ├── students.py      # CRUD endpoints
│   │   └── meta.py          # /api/stats, /api/courses, /api/ai/*
│   ├── services/
│   │   ├── student_service.py   # business logic + all queries
│   │   └── ai_service.py        # allowlisted AI operations + Ollama call
│   ├── templates/index.html
│   └── static/{css,js}/
├── scripts/{init_db.py, seed_data.py}
├── tests/{conftest.py, test_students.py, test_ai.py}
├── docs/SUBMISSION.md       # architecture, schema, viva Q&A, demo script, checklist…
├── requests.http, requirements.txt, .env.example, .gitignore, LICENSE
└── data/                    # SQLite file is created here (git-ignored)
```

## Prerequisites
Python 3.10 or newer (`python --version`) and Git (optional, for GitHub).

## Setup (Windows PowerShell)
```powershell
cd studentsphere
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
copy .env.example .env              # optional
python -m scripts.init_db           # optional: tables are also auto-created on start
python -m scripts.seed_data         # optional: 10 DUMMY demo students
uvicorn app.main:app --reload
```
macOS/Linux: use `python3 -m venv .venv && source .venv/bin/activate` and `cp .env.example .env`.

## URLs
| What | URL |
|---|---|
| Web dashboard | http://127.0.0.1:8000/ |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| Health | http://127.0.0.1:8000/health |

## API examples
```bash
# Create → 201
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"student_id":"STU-2001","full_name":"Nisha Example","date_of_birth":"2004-03-12","email":"nisha@example.com","course":"Physics"}'

# List/search/filter/paginate → 200
curl "http://127.0.0.1:8000/students?search=nisha&course=Physics&page=1&page_size=10"

# One / PATCH / PUT / DELETE
curl http://127.0.0.1:8000/students/STU-2001
curl -X PATCH http://127.0.0.1:8000/students/STU-2001 -H "Content-Type: application/json" -d '{"phone":"+91 90000 22222"}'
curl -X DELETE http://127.0.0.1:8000/students/STU-2001        # → 204
```
Example list response:
```json
{"items":[{"id":1,"student_id":"STU-2001","full_name":"Nisha Example","date_of_birth":"2004-03-12",
"email":"nisha@example.com","phone":null,"course":"Physics","address":null,"enrollment_date":null,
"created_at":"2026-10-17T10:00:00","updated_at":"2026-10-17T10:00:00"}],
"total":1,"page":1,"page_size":10,"total_pages":1}
```
Error examples: `404 {"detail":"Student 'X' was not found."}`, `409 {"detail":"Student ID 'STU-1001' is already registered."}`,
`422 {"detail":"Validation failed.","errors":[{"field":"email","message":"…"}]}`.
More requests are in `requests.http`.

**Path identifier:** `{student_id}` is the business ID (e.g. `STU-1001`), not the internal database number.

## CRUD demonstration steps
1. Open `/`, click **Add student**, fill the form, save → appears in **Students**.
2. Search by name/ID/email/phone, filter by course, sort by clicking headers, change rows per page.
3. Click the eye icon → profile. Click the pencil → edit and save.
4. Try adding the same Student ID → inline 409 message. Submit empty form → inline validation.
5. Click the trash icon → confirm → record removed. Stop and restart the server → data is still there.

## Testing
```powershell
pytest -v
```
Tests use a temporary SQLite file per test, so your real `data/students.db` is never touched.

## Optional: Local AI assistant with Ollama
The core app works fully without it.
1. Install Ollama from https://ollama.com/download
2. `ollama pull llama3.2:1b`
3. Make sure Ollama is running (`ollama serve`, default port 11434).
4. Open **AI Assistant** in the sidebar. Set `ENABLE_AI=false` in `.env` to hide it.

Supported questions: total students; "born after/before YEAR"; students per course; enrolled this month; distribution by course.
Safety: the question is mapped to an allowlisted function, the backend runs it with the ORM, and the model only rephrases the verified result.
It never writes SQL and cannot create/update/delete. If Ollama is off, you get the direct database answer with a notice.
"Born after 2005" means born in 2006 or later.

## Screenshots
Screenshots from a real run are in `docs/screenshots/`. To replace them, run the app, open each page, capture with
Win+Shift+S, and save into that folder. Reference them like `![Dashboard](docs/screenshots/dashboard.png)`.

## Known limitations
- No login/authentication (single-user local educational tool; do not expose publicly without adding auth).
- SQLite is single-writer; ideal for local/small use, not heavy concurrency.
- No schema migrations (Alembic) — changing models requires recreating the database in development.
- AI intent matching is keyword-based by design (safety over flexibility).

## Future improvements
Authentication and roles, Alembic migrations, CSV import/export, attendance/grades modules, Docker, CI with GitHub Actions.

## Attribution
Developed by **Narendra Vishnoi** for the Python Backend Development internship at **EWB Edu Tech Pvt. Ltd.** Licensed under MIT (see `LICENSE`).
