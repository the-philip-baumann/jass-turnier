from datetime import date

from pydantic import BaseModel, ConfigDict


class PlayerBase(BaseModel):
    name: str
    email: str | None = None
    registered: bool = False


class PlayerCreate(BaseModel):
    vorname: str
    nachname: str
    player_number: int | None = None


class PlayerUpdate(BaseModel):
    name: str


class PlayerRegisteredUpdate(BaseModel):
    registered: bool


class Player(PlayerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    player_number: int
    group_number: int | None
    tournament_id: int


class PlayerImportResult(BaseModel):
    created: list[Player]
    skipped_duplicates: int
    skipped_invalid: int


class TournamentBase(BaseModel):
    name: str
    date: date


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    rounds: int
    num_groups: int
    tables_per_row: int
    anzahl_ansagen: int = 1


class Tournament(TournamentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rounds: int
    num_groups: int
    tables_per_row: int
    anzahl_ansagen: int
    status: str
    players_imported: bool


class TournamentDetail(Tournament):
    players: list[Player] = []


class GameResultCreate(BaseModel):
    player_id: int
    team: int
    points: int


class GameResult(GameResultCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    game_id: int


class GameCreate(BaseModel):
    round_number: int
    table_number: int


class Game(GameCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tournament_id: int
    results: list[GameResult] = []


class GameScoreUpdate(BaseModel):
    team1_score: int
    team2_score: int
