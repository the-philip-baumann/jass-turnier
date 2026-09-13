from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_player, get_tournament
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/tournaments/{tournament_id}/players", tags=["players"])


@router.post("", response_model=schemas.Player)
def add_player(
    player: schemas.PlayerCreate,
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    if tournament.status == "started":
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – keine Spieler mehr hinzufügen",
        )
    if player.player_number is not None:
        next_number = player.player_number
        if any(p.player_number == next_number for p in tournament.players):
            raise HTTPException(status_code=400, detail="Spielernummer ist bereits vergeben")
    else:
        next_number = max((p.player_number for p in tournament.players), default=0) + 1
    name = f"{player.vorname.strip()} {player.nachname.strip()}".strip()
    db_player = models.Player(
        name=name,
        player_number=next_number,
        tournament_id=tournament.id,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.patch("/{player_id}", response_model=schemas.Player)
def update_player(
    update: schemas.PlayerUpdate,
    player: models.Player = Depends(get_player),
    db: Session = Depends(get_db),
):
    player.name = update.name
    db.commit()
    db.refresh(player)
    return player


@router.delete("/{player_id}", status_code=204)
def remove_player(
    tournament: models.Tournament = Depends(get_tournament),
    player: models.Player = Depends(get_player),
    db: Session = Depends(get_db),
):
    if tournament.status == "started":
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – Spieler können nicht entfernt werden",
        )
    db.delete(player)
    db.commit()
