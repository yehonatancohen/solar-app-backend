# Solar Sizing, Quotation, and Installation Planning — Backend (FastAPI)

This is a production-ready skeleton to start development. It includes:
- FastAPI app with auth, projects, and calculation endpoints
- JWT auth with Argon2id password hashing
- SQLAlchemy ORM
- Env-based config (SQLite by default, Postgres-ready)
- CORS
- Placeholders for solar algorithms and PDF/email integrations

## Quick start (local, SQLite)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs

## Postgres (optional)
Set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname` in `.env` before running.

## Structure
- `app/main.py` — app factory and router includes
- `app/config.py` — environment configuration
- `app/db.py` — SQLAlchemy engine and session
- `app/models.py` — ORM models
- `app/schemas.py` — Pydantic schemas
- `app/auth.py` — register/login, JWT helpers
- `app/routers/projects.py` — projects CRUD and inputs
- `app/routers/calcs.py` — calculation trigger; calls `app/calcs/solar.py`
- `app/calcs/solar.py` — **PUT YOUR EXCEL-EXTRACTED ALGORITHMS HERE**

## Notes
- Tables auto-create on startup for dev. Migrate to Alembic later.
- Add Stripe, SendGrid, Playwright modules when you reach payments/emails/PDFs.
"# solar-app-backend" 
