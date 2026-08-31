import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
def update_tournament(
    tournament_id: int, update: schemas.TournamentUpdate, db: Session = Depends(get_db)
):
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
            t
            for t in combinations(cands, 3)
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

    raise ValueError("Konnte keinen gültigen Spielplan generieren — bitte Rundenanzahl reduzieren")


@router.post("/{tournament_id}/start", response_model=schemas.TournamentDetail)
def start_tournament(tournament_id: int, db: Session = Depends(get_db)):
    import random

    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.status == "started":
        raise HTTPException(status_code=400, detail="Turnier wurde bereits gestartet")
    registered_players = [p for p in tournament.players if p.registered]
    if len(registered_players) < 2:
        raise HTTPException(
            status_code=400, detail="Es müssen mindestens 2 angemeldete Spieler erfasst sein"
        )
    if tournament.num_groups < 1:
        raise HTTPException(status_code=400, detail="Anzahl Gruppen muss mindestens 1 sein")
    if len(registered_players) < tournament.num_groups:
        raise HTTPException(
            status_code=400,
            detail="Mehr Gruppen als angemeldete Spieler — bitte Konfiguration anpassen",
        )

    # Assign only registered/present players to groups; no-shows are left out of the schedule.
    shuffled = registered_players[:]
    random.shuffle(shuffled)
    for i, player in enumerate(shuffled):
        player.group_number = (i % tournament.num_groups) + 1

    db.flush()  # ensure group_number is set before scheduling

    # Build group → player id map
    from collections import defaultdict

    groups: dict[int, list[int]] = defaultdict(list)
    for player in registered_players:
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


@router.post("/{tournament_id}/players", response_model=schemas.Player)
def add_player(tournament_id: int, player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
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
    # Manually added players are walk-ins without prior CSV pre-registration.
    db_player = models.Player(
        name=name,
        player_number=next_number,
        registered=True,
        tournament_id=tournament_id,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.post("/{tournament_id}/players/import", response_model=schemas.PlayerImportResult)
def import_players(tournament_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    tournament = db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.status == "started":
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – keine Spieler mehr hinzufügen",
        )
    if tournament.players_imported:
        raise HTTPException(
            status_code=400,
            detail=(
                "Die Anmeldeliste wurde bereits importiert – ein erneuter Import ist nicht möglich"
            ),
        )

    raw = file.file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="CSV-Datei konnte nicht gelesen werden (Encoding)"
        )

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = {(f or "").strip() for f in (reader.fieldnames or [])}
    required = {"Zeitstempel", "Vorname", "Nachname", "E-Mail-Adresse"}
    if not required.issubset(fieldnames):
        raise HTTPException(
            status_code=400,
            detail=f"CSV muss die Spalten {', '.join(sorted(required))} enthalten",
        )

    existing_emails = {p.email.strip().lower() for p in tournament.players if p.email}
    next_number = max((p.player_number for p in tournament.players), default=0) + 1

    created: list[models.Player] = []
    skipped_duplicates = 0
    skipped_invalid = 0

    for row in reader:
        vorname = (row.get("Vorname") or "").strip()
        nachname = (row.get("Nachname") or "").strip()
        email = (row.get("E-Mail-Adresse") or "").strip()
        name = f"{vorname} {nachname}".strip()

        if not name:
            skipped_invalid += 1
            continue

        email_key = email.lower() if email else None
        if email_key and email_key in existing_emails:
            skipped_duplicates += 1
            continue

        db_player = models.Player(
            name=name,
            email=email or None,
            registered=False,
            player_number=next_number,
            tournament_id=tournament_id,
        )
        db.add(db_player)
        created.append(db_player)
        next_number += 1
        if email_key:
            existing_emails.add(email_key)

    tournament.players_imported = True
    db.commit()
    for p in created:
        db.refresh(p)

    return schemas.PlayerImportResult(
        created=created,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
    )


@router.patch("/{tournament_id}/players/{player_id}", response_model=schemas.Player)
def update_player(
    tournament_id: int, player_id: int, update: schemas.PlayerUpdate, db: Session = Depends(get_db)
):
    player = db.get(models.Player, player_id)
    if not player or player.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Player not found")
    player.name = update.name
    db.commit()
    db.refresh(player)
    return player


@router.patch("/{tournament_id}/players/{player_id}/registered", response_model=schemas.Player)
def update_player_registered(
    tournament_id: int,
    player_id: int,
    update: schemas.PlayerRegisteredUpdate,
    db: Session = Depends(get_db),
):
    player = db.get(models.Player, player_id)
    if not player or player.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Player not found")
    player.registered = update.registered
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
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – Spieler können nicht entfernt werden",
        )
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
def update_game_score(
    tournament_id: int, game_id: int, score: schemas.GameScoreUpdate, db: Session = Depends(get_db)
):
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


@router.post("/{tournament_id}/games/{game_id}/results", response_model=schemas.GameResult)
def add_result(
    tournament_id: int,
    game_id: int,
    result: schemas.GameResultCreate,
    db: Session = Depends(get_db),
):
    game = db.get(models.Game, game_id)
    if not game or game.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Game not found")
    db_result = models.GameResult(**result.model_dump(), game_id=game_id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result
