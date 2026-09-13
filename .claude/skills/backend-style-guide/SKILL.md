---
name: backend-style-guide
description: Conventions for backend/app (FastAPI + SQLAlchemy + Pydantic) in this repo — layering, router/schema/test structure, error handling, migrations, imports, lint. Load before writing or reviewing any backend/app or backend/alembic code, or backend/tests.
---

# Backend style guide

This documents how `backend/` is actually built, not aspirational rules. If you're
about to add or change an endpoint, a model, a migration, or a test, follow the
matching pattern below instead of introducing a new one. If a genuinely better
pattern is warranted, use it — then update this file in the same change so it
doesn't go stale.

## Layering

Four layers, each with one job:

- **`app/routers/`** — HTTP layer. One file per resource. Handles request/response
  shape, calls the DB directly (no repository layer — see "No CRUD service layer"
  below), and does orchestration that's specific to one endpoint (e.g.
  `start_tournament` assigning groups and persisting the generated schedule).
- **`app/dependencies.py`** — shared FastAPI dependencies for path-param lookups
  that 404. `get_tournament`, `get_player`, `get_game`, `get_sponsor` each fetch by
  ID (scoping to the parent where relevant, e.g. `player.tournament_id ==
  tournament_id`) and raise `HTTPException(404, ...)` if missing. Routers depend on
  these instead of repeating `x = db.get(...); if not x: raise ...` inline.
- **`app/services/`** — pure business logic with **no DB or FastAPI dependency**.
  Currently just `scheduling.py` (the backtracking table-assignment algorithm).
  Anything that's "just a computation" and could be unit-tested with plain Python
  values belongs here, not in a router.
- **`app/models/`, `app/schemas/`** — SQLAlchemy models and Pydantic schemas.

### No CRUD service layer

Simple database access (create/list/get/update/delete) stays inline in routers —
there is no `app/crud.py` or repository abstraction. This app is small enough that
the indirection wouldn't pay for itself, and the test suite already exercises
routers end-to-end over HTTP (see Testing below), so a separate service layer
would mostly duplicate what the router does. Don't add one unless a genuine reuse
need appears (the same non-trivial query used from two+ routers).

### One router file per resource

Each resource gets its own `APIRouter` in its own file, prefixed and tagged:

```python
router = APIRouter(prefix="/tournaments/{tournament_id}/players", tags=["players"])
```

`routers/tournaments.py` (top-level tournament CRUD + start/reset), `players.py`,
`games.py`, `sponsors.py` are the current split — mirrored 1:1 by
`tests/test_tournaments.py`, `test_players.py`, `test_games.py`, `test_sponsors.py`.
When a router file would cover more than one resource, split it before it grows
past ~150 lines, not after — that's what happened to the old
`routers/tournaments.py` (372 lines covering four resources) and it's why the
split exists now.

## Imports

Always at the top of the module — stdlib, then third-party, then local
(`app.*`), sorted (ruff's `I` rule enforces this — `ruff check --fix` will do it
for you). No function-local imports "to avoid circular imports" or "because it's
only used once" — if you hit a real circular import, that's a sign the layering
above is being violated, not a reason to hide the import.

## Schemas (`app/schemas/schemas.py`)

Single file — it's small; don't split it per-resource preemptively. Pattern per
resource:

- `XCreate` — input for `POST`, only the fields a client actually provides.
- `XUpdate` — input for `PATCH`, only the fields that endpoint allows changing.
- `X` — output model, `model_config = ConfigDict(from_attributes=True)`.
- `XDetail(X)` — only when a response needs an expanded nested relationship
  (e.g. `TournamentDetail` adds `players: list[Player]`). Don't nest by default.

## Models (`app/models/models.py`)

Single file too, for the same reason — SQLAlchemy relationships cross-reference
each other by string name, so file boundaries add friction without helping
readability at this size. Split it if it grows past ~200 lines or gains a second
clearly-separable domain (e.g. a whole new bounded context).

## Error handling

`HTTPException` raised directly — in `app/dependencies.py` for the shared 404
lookups, inline in routers for endpoint-specific validation (400/422). No central
exception-handler module; there aren't enough distinct error types to justify one
yet.

**User-facing `detail` strings are German** (the app's UI language — Swiss Jass
tournaments), e.g. `"Turnier wurde bereits gestartet"`. Everything else — code,
identifiers, comments, commit messages, this file — is English. Don't translate
existing German detail strings to English or vice versa; match whichever
convention the string you're touching already follows.

## Migrations (Alembic)

Schema changes go through Alembic — **never inline DDL in application code**.
`app/main.py` has zero DB side effects at import time; schema creation is
entirely `alembic upgrade head`'s job, run by `backend/entrypoint.sh` before
`uvicorn` starts.

```bash
cd backend
alembic revision --autogenerate -m "short description"   # after changing models.py
alembic upgrade head                                       # apply locally
```

Always inspect an autogenerated migration before committing it — autogenerate
gets new tables/columns right but doesn't know about data backfills or
Postgres-specific constraints you might need to add by hand.

## Testing (`backend/tests/`)

- Black-box over HTTP via `TestClient`, never call router functions directly.
- One test file per resource, matching the router split.
- Group related cases in a class per endpoint:
  `class TestCreateTournament:`, `class TestAddSponsor:`.
- Small `make_x(client, ...)` helper functions at module scope for the common
  "create a tournament/player/etc. and return its JSON" setup — see
  `make_tournament` repeated (deliberately, not a shared import) across test
  files.
- Fixtures come from `conftest.py`: SQLite **in-memory** + `StaticPool` per test
  (`db_engine`), the real `app.main.app` with `get_db` overridden to it
  (`app`/`client`). Don't build a second app or mock the DB — the real app has no
  import-time DB side effects, so using it directly in tests is exactly the
  point.

## Lint & format

`ruff` enforces `E, F, I, UP` at 100 columns; `ruff format` is the formatter. Both
are CI-enforced (`ruff check .` and `ruff format --check .`) — run them locally
before considering a change done:

```bash
cd backend
ruff check --fix .
ruff format .
```
