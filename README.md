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
alembic upgrade head
uvicorn app.main:app --reload
```

Hinweis: Für lokale Entwicklung ohne Docker braucht es eine erreichbare Postgres-Instanz
oder eine angepasste `DATABASE_URL` in einer `.env`-Datei im `backend/`-Ordner. Die App
legt das Schema nicht mehr selbst an — das übernimmt ausschliesslich Alembic
(siehe unten).

## Mit Docker starten (empfohlen)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend (API + Docs): http://localhost:8000/docs

Die Postgres-Daten werden im Docker-Volume `db_data` persistiert. Der Backend-Container
führt `alembic upgrade head` automatisch aus, bevor er startet (siehe `backend/entrypoint.sh`).

## Datenbank-Migrationen (Alembic)

Schemaänderungen laufen ausschliesslich über Alembic-Migrationen unter
`backend/alembic/versions/` — nie über Ad-hoc-DDL im Anwendungscode.

```bash
cd backend
# neue Migration nach Modelländerungen erzeugen:
alembic revision --autogenerate -m "kurze beschreibung"
# manuell anwenden (Docker macht das beim Start automatisch):
alembic upgrade head
```

**Bestehende lokale Datenbank von vor der Alembic-Umstellung?** Diese hat bereits das
aktuelle Schema (wurde bisher bei jedem Start per Ad-hoc-SQL nachgezogen), aber keine
`alembic_version`-Tabelle — `alembic upgrade head` schlägt dann mit "relation already
exists" fehl. Zwei Optionen:

- `docker compose down -v` — frisches Volume, Migration läuft sauber durch (ok, wenn die
  lokalen Turnierdaten nicht gebraucht werden), oder
- einmalig `alembic stamp head` gegen die bestehende Datenbank ausführen, um sie als
  aktuell zu markieren, ohne die Migration erneut auszuführen:
  ```bash
  docker compose run --rm --entrypoint alembic backend stamp head
  ```
