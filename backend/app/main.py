from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import models  # noqa: F401
from app.routers import games, players, sponsors, tournaments

app = FastAPI(title="Jass Turnier Verwaltung")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tournaments.router)
app.include_router(players.router)
app.include_router(games.router)
app.include_router(sponsors.router)


@app.get("/health")
def health():
    return {"status": "ok"}
