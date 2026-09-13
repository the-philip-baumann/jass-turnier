"""Shared FastAPI dependencies for path-param lookups.

Each of these fetches a resource by its path parameters and raises a 404 if it
doesn't exist (or doesn't belong to the given parent), so routers can depend on
an already-validated object instead of repeating the lookup inline.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import models


def get_tournament(tournament_id: int, db: Session = Depends(get_db)) -> models.Tournament:
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


def get_player(tournament_id: int, player_id: int, db: Session = Depends(get_db)) -> models.Player:
    player = db.get(models.Player, player_id)
    if not player or player.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def get_game(tournament_id: int, game_id: int, db: Session = Depends(get_db)) -> models.Game:
    game = db.get(models.Game, game_id)
    if not game or game.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


def get_sponsor(
    tournament_id: int, sponsor_id: int, db: Session = Depends(get_db)
) -> models.Sponsor:
    sponsor = db.get(models.Sponsor, sponsor_id)
    if not sponsor or sponsor.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor
