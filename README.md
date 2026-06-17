# Jass Turnier Verwaltung

> Dieses Projekt wurde ausschliesslich mit [Claude Code](https://claude.ai/code) umgesetzt — von der Architektur über die Implementierung bis hin zur Dokumentation.

Werkzeug zur Verwaltung von Jass-Turnieren: Turniere anlegen, Spieler verwalten, Spiele und Ergebnisse erfassen.

## Stack

- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: Vue 3 + Vite
- Persistenz: PostgreSQL via Docker-Volume
- Orchestrierung: Docker Compose

## Lokale Backend-Entwicklung (ohne Docker)

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Hinweis: Für lokale Entwicklung ohne Docker braucht es eine erreichbare Postgres-Instanz
oder eine angepasste `DATABASE_URL` in einer `.env`-Datei im `backend/`-Ordner.

## Mit Docker starten (empfohlen)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend (API + Docs): http://localhost:8000/docs

Die Postgres-Daten werden im Docker-Volume `db_data` persistiert.
