from datetime import date

from pydantic import BaseModel, ConfigDict


class PlayerBase(BaseModel):
    name: str


class PlayerCreate(PlayerBase):
    player_number: int


class PlayerUpdate(PlayerBase):
    player_number: int


class Player(PlayerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    player_number: int
    group_number: int | None
    tournament_id: int


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
