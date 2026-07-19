from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine
from app.models import models  # noqa: F401
from app.routers import tournaments

Base.metadata.create_all(bind=engine)

# Add new columns that may not exist in existing databases
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS anzahl_ansagen INTEGER NOT NULL DEFAULT 1"
    ))
    conn.execute(text(
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS email VARCHAR"
    ))
    conn.execute(text(
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS registered BOOLEAN NOT NULL DEFAULT false"
    ))
    conn.execute(text(
        "ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS players_imported BOOLEAN NOT NULL DEFAULT false"
    ))
    # Backfill any rows left without a number from a previous version, so existing data stays valid.
    conn.execute(text(
        """
        UPDATE players SET player_number = sub.rn + coalesce(existing_max.max_number, 0)
        FROM (
            SELECT id, tournament_id,
                   row_number() OVER (PARTITION BY tournament_id ORDER BY id) AS rn
            FROM players
            WHERE player_number IS NULL
        ) AS sub
        LEFT JOIN (
            SELECT tournament_id, max(player_number) AS max_number
            FROM players
            WHERE player_number IS NOT NULL
            GROUP BY tournament_id
        ) AS existing_max ON existing_max.tournament_id = sub.tournament_id
        WHERE players.id = sub.id
        """
    ))
    conn.execute(text(
        "ALTER TABLE players ALTER COLUMN player_number SET NOT NULL"
    ))
    conn.commit()

app = FastAPI(title="Jass Turnier Verwaltung")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tournaments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
