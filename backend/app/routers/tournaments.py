from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import models
from app.schemas import schemas

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
def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.patch("/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(tournament_id: int, update: schemas.TournamentUpdate, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament.rounds = update.rounds
    tournament.num_groups = update.num_groups
    tournament.tables_per_row = update.tables_per_row
    tournament.anzahl_ansagen = update.anzahl_ansagen
    db.commit()
    db.refresh(tournament)
    return tournament


def _form_round(
    player_ids: list[int],
    played_together: set[tuple[int, int]],
    games_per_round: int,
) -> list[list[int]] | None:
    """
    Backtracking search: partition player_ids into games_per_round tables of 4
    such that no pair appears in played_together or is used twice within this round.
    Returns None if no valid partition exists.
    """
    import random
    from itertools import combinations

    def backtrack(
        available: list[int],
        tables: list[list[int]],
        round_pairs: set[tuple[int, int]],
    ) -> list[list[int]] | None:
        if len(tables) == games_per_round:
            return tables
        if len(available) < 4:
            return None

        all_pairs = played_together | round_pairs
        anchor = available[0]
        rest = available[1:]

        # Only consider players anchor hasn't met
        cands = [p for p in rest if (min(anchor, p), max(anchor, p)) not in all_pairs]

        # Only triples where every internal pair is also fresh
        valid_triples = [
            t for t in combinations(cands, 3)
            if all(
                (min(t[i], t[j]), max(t[i], t[j])) not in all_pairs
                for i in range(3)
                for j in range(i + 1, 3)
            )
        ]
        random.shuffle(valid_triples)

        for triple in valid_triples:
            table = [anchor] + list(triple)
            new_round_pairs = round_pairs | {
                (min(table[i], table[j]), max(table[i], table[j]))
                for i in range(4)
                for j in range(i + 1, 4)
            }
            new_available = [p for p in rest if p not in triple]
            result = backtrack(new_available, tables + [table], new_round_pairs)
            if result is not None:
                return result

        return None

    shuffled = player_ids[:]
    random.shuffle(shuffled)
    return backtrack(shuffled, [], set())


def _generate_schedule(group_player_ids: list[int], num_rounds: int) -> list[list[list[int]]]:
    """
    Generate a round schedule for one group. Each round is a list of tables (list of 4 player ids).
    Hard guarantee: no pair ever shares a table twice across all rounds.
    Raises ValueError if the requested number of rounds is mathematically impossible.
    """
    n = len(group_player_ids)
    games_per_round = n // 4
    if games_per_round == 0:
        return []

    # Each player has n-1 possible partners, uses 3 per round → upper bound
    max_possible = (n - 1) // 3
    if num_rounds > max_possible:
        raise ValueError(
            f"Mit {n} Spielern sind maximal {max_possible} Runden ohne Paar-Wiederholung möglich "
            f"(angefordert: {num_rounds})"
        )

    # Retry outer loop: different initial shuffles escape local dead-ends
    for _ in range(500):
        played_together: set[tuple[int, int]] = set()
        all_rounds: list[list[list[int]]] = []
        failed = False

        for _ in range(num_rounds):
            tables = _form_round(group_player_ids, played_together, games_per_round)
            if tables is None:
                failed = True
                break
            for table in tables:
                for i in range(4):
                    for j in range(i + 1, 4):
                        played_together.add((min(table[i], table[j]), max(table[i], table[j])))
            all_rounds.append(tables)

        if not failed:
            return all_rounds

    raise ValueError(
        "Konnte keinen gültigen Spielplan generieren — bitte Rundenanzahl reduzieren"
    )


@router.post("/{tournament_id}/start", response_model=schemas.TournamentDetail)
def start_tournament(tournament_id: int, db: Session = Depends(get_db)):
    import random
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.status == "started":
        raise HTTPException(status_code=400, detail="Turnier wurde bereits gestartet")
    if len(tournament.players) < 2:
        raise HTTPException(status_code=400, detail="Es müssen mindestens 2 Spieler erfasst sein")
    if tournament.num_groups < 1:
        raise HTTPException(status_code=400, detail="Anzahl Gruppen muss mindestens 1 sein")
    if len(tournament.players) < tournament.num_groups:
        raise HTTPException(status_code=400, detail="Mehr Gruppen als Spieler — bitte Konfiguration anpassen")

    # Assign players to groups
    shuffled = tournament.players[:]
    random.shuffle(shuffled)
    for i, player in enumerate(shuffled):
        player.group_number = (i % tournament.num_groups) + 1

    db.flush()  # ensure group_number is set before scheduling

    # Build group → player id map
    from collections import defaultdict
    groups: dict[int, list[int]] = defaultdict(list)
    for player in tournament.players:
        groups[player.group_number].append(player.id)

    # Generate and persist game schedule
    for group_num, player_ids in groups.items():
        try:
            schedule = _generate_schedule(player_ids, tournament.rounds)
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
def reset_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
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
def delete_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    db.delete(tournament)
    db.commit()


def _check_number_taken(db: Session, tournament_id: int, player_number: int, exclude_player_id: int | None = None):
    query = db.query(models.Player).filter(
        models.Player.tournament_id == tournament_id,
        models.Player.player_number == player_number,
    )
    if exclude_player_id is not None:
        query = query.filter(models.Player.id != exclude_player_id)
    if query.first():
        raise HTTPException(status_code=400, detail="Spielernummer ist bereits vergeben")


@router.post("/{tournament_id}/players", response_model=schemas.Player)
def add_player(tournament_id: int, player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.status == "started":
        raise HTTPException(status_code=400, detail="Turnier wurde bereits gestartet – keine Spieler mehr hinzufügen")
    _check_number_taken(db, tournament_id, player.player_number)
    db_player = models.Player(**player.model_dump(), tournament_id=tournament_id)
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.patch("/{tournament_id}/players/{player_id}", response_model=schemas.Player)
def update_player(tournament_id: int, player_id: int, update: schemas.PlayerUpdate, db: Session = Depends(get_db)):
    player = db.get(models.Player, player_id)
    if not player or player.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Player not found")
    _check_number_taken(db, tournament_id, update.player_number, exclude_player_id=player_id)
    player.name = update.name
    player.player_number = update.player_number
    db.commit()
    db.refresh(player)
    return player


@router.delete("/{tournament_id}/players/{player_id}", status_code=204)
def remove_player(tournament_id: int, player_id: int, db: Session = Depends(get_db)):
    player = db.get(models.Player, player_id)
    if not player or player.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Player not found")
    tournament = db.get(models.Tournament, tournament_id)
    if tournament.status == "started":
        raise HTTPException(status_code=400, detail="Turnier wurde bereits gestartet – Spieler können nicht entfernt werden")
    db.delete(player)
    db.commit()


@router.post("/{tournament_id}/games", response_model=schemas.Game)
def create_game(tournament_id: int, game: schemas.GameCreate, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    db_game = models.Game(**game.model_dump(), tournament_id=tournament_id)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


@router.get("/{tournament_id}/games", response_model=list[schemas.Game])
def list_games(tournament_id: int, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    return (
        db.query(models.Game)
        .filter(models.Game.tournament_id == tournament_id)
        .options(joinedload(models.Game.results))
        .all()
    )


@router.patch("/{tournament_id}/games/{game_id}", response_model=schemas.Game)
def update_game_score(tournament_id: int, game_id: int, score: schemas.GameScoreUpdate, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    game = (
        db.query(models.Game)
        .filter(models.Game.id == game_id, models.Game.tournament_id == tournament_id)
        .options(joinedload(models.Game.results))
        .first()
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    tournament = db.get(models.Tournament, tournament_id)
    expected = 157 * tournament.anzahl_ansagen
    if score.team1_score + score.team2_score != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Summe der Scores muss {expected} ergeben (157 × {tournament.anzahl_ansagen} Ansagen)",
        )
    for result in game.results:
        result.points = score.team1_score if result.team == 1 else score.team2_score
    db.commit()
    db.refresh(game)
    return game


@router.post("/{tournament_id}/games/{game_id}/results", response_model=schemas.GameResult)
def add_result(tournament_id: int, game_id: int, result: schemas.GameResultCreate, db: Session = Depends(get_db)):
    game = db.get(models.Game, game_id)
    if not game or game.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Game not found")
    db_result = models.GameResult(**result.model_dump(), game_id=game_id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result
