import random
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tournament
from app.models import models
from app.schemas import schemas
from app.services.scheduling import generate_schedule

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("", response_model=schemas.Tournament)
def create_tournament(tournament: schemas.TournamentCreate, db: Session = Depends(get_db)):
    db_tournament = models.Tournament(**tournament.model_dump())
    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


@router.get("", response_model=list[schemas.Tournament])
def list_tournaments(db: Session = Depends(get_db)):
    return db.query(models.Tournament).all()


@router.get("/{tournament_id}", response_model=schemas.TournamentDetail)
def get_tournament_detail(tournament: models.Tournament = Depends(get_tournament)):
    return tournament


@router.patch("/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(
    update: schemas.TournamentUpdate,
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    tournament.rounds = update.rounds
    tournament.num_groups = update.num_groups
    tournament.tables_per_row = update.tables_per_row
    tournament.anzahl_ansagen = update.anzahl_ansagen
    db.commit()
    db.refresh(tournament)
    return tournament


@router.post("/{tournament_id}/start", response_model=schemas.TournamentDetail)
def start_tournament(
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    if tournament.status == "started":
        raise HTTPException(status_code=400, detail="Turnier wurde bereits gestartet")
    if len(tournament.players) < 2:
        raise HTTPException(status_code=400, detail="Es müssen mindestens 2 Spieler erfasst sein")
    if tournament.num_groups < 1:
        raise HTTPException(status_code=400, detail="Anzahl Gruppen muss mindestens 1 sein")
    if len(tournament.players) < tournament.num_groups:
        raise HTTPException(
            status_code=400,
            detail="Mehr Gruppen als Spieler — bitte Konfiguration anpassen",
        )

    # Assign players to groups
    shuffled = tournament.players[:]
    random.shuffle(shuffled)
    for i, player in enumerate(shuffled):
        player.group_number = (i % tournament.num_groups) + 1

    db.flush()  # ensure group_number is set before scheduling

    # Build group → player id map
    groups: dict[int, list[int]] = defaultdict(list)
    for player in tournament.players:
        groups[player.group_number].append(player.id)

    # Generate and persist game schedule
    for group_num, player_ids in groups.items():
        try:
            schedule = generate_schedule(player_ids, tournament.rounds)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        table_offset = (group_num - 1) * (len(player_ids) // 4)
        for round_idx, round_tables in enumerate(schedule):
            for table_idx, table_player_ids in enumerate(round_tables):
                game = models.Game(
                    tournament_id=tournament.id,
                    round_number=round_idx + 1,
                    table_number=table_offset + table_idx + 1,
                )
                db.add(game)
                db.flush()
                for seat, pid in enumerate(table_player_ids):
                    result = models.GameResult(
                        game_id=game.id,
                        player_id=pid,
                        team=(seat // 2) + 1,
                        points=0,
                    )
                    db.add(result)

    tournament.status = "started"
    db.commit()
    db.refresh(tournament)
    return tournament


@router.post("/{tournament_id}/reset", response_model=schemas.TournamentDetail)
def reset_tournament(
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    if tournament.status != "started":
        raise HTTPException(status_code=400, detail="Turnier wurde noch nicht gestartet")

    for game in list(tournament.games):
        db.delete(game)

    for player in tournament.players:
        player.group_number = None

    tournament.status = "setup"
    db.commit()
    db.refresh(tournament)
    return tournament


@router.delete("/{tournament_id}", status_code=204)
def delete_tournament(
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    db.delete(tournament)
    db.commit()
