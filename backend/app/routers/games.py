from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.dependencies import get_game, get_tournament
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/tournaments/{tournament_id}/games", tags=["games"])


@router.post("", response_model=schemas.Game)
def create_game(
    game: schemas.GameCreate,
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    db_game = models.Game(**game.model_dump(), tournament_id=tournament.id)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


@router.get("", response_model=list[schemas.Game])
def list_games(
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Game)
        .filter(models.Game.tournament_id == tournament.id)
        .options(joinedload(models.Game.results))
        .all()
    )


@router.patch("/{game_id}", response_model=schemas.Game)
def update_game_score(
    score: schemas.GameScoreUpdate,
    tournament: models.Tournament = Depends(get_tournament),
    game: models.Game = Depends(get_game),
    db: Session = Depends(get_db),
):
    expected = 157 * tournament.anzahl_ansagen
    if score.team1_score + score.team2_score != expected:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Summe der Scores muss {expected} ergeben "
                f"(157 × {tournament.anzahl_ansagen} Ansagen)"
            ),
        )
    for result in game.results:
        result.points = score.team1_score if result.team == 1 else score.team2_score
    db.commit()
    db.refresh(game)
    return game


@router.post("/{game_id}/results", response_model=schemas.GameResult)
def add_result(
    result: schemas.GameResultCreate,
    game: models.Game = Depends(get_game),
    db: Session = Depends(get_db),
):
    db_result = models.GameResult(**result.model_dump(), game_id=game.id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result
