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
