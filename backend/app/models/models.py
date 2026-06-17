from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    rounds = Column(Integer, nullable=False, default=4, server_default="4")
    num_groups = Column(Integer, nullable=False, default=2, server_default="2")
    tables_per_row = Column(Integer, nullable=False, default=4, server_default="4")
    anzahl_ansagen = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String, nullable=False, default="setup", server_default="setup")

    players = relationship("Player", back_populates="tournament", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="tournament", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    player_number = Column(Integer, nullable=False)
    group_number = Column(Integer, nullable=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)

    tournament = relationship("Tournament", back_populates="players")
    results = relationship("GameResult", back_populates="player", cascade="all, delete-orphan")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    table_number = Column(Integer, nullable=False)

    tournament = relationship("Tournament", back_populates="games")
    results = relationship("GameResult", back_populates="game", cascade="all, delete-orphan")


class GameResult(Base):
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)

    game = relationship("Game", back_populates="results")
    player = relationship("Player", back_populates="results")
