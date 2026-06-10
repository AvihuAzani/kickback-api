from pydantic import BaseModel
from typing import Optional, List, Union, Literal
from enum import Enum
from datetime import datetime


class Position(str, Enum):
    goalkeeper = "goalkeeper"
    defender = "defender"
    midfielder = "midfielder"
    forward = "forward"


class RegisteredPlayer(BaseModel):
    type: Literal["registered"]
    userId: str
    name: str
    jerseyNumber: Optional[int] = None
    position: Optional[Position] = None


class GuestPlayer(BaseModel):
    type: Literal["guest"]
    id: str
    name: str
    jerseyNumber: Optional[int] = None
    position: Optional[Position] = None


PlayerEntry = Union[RegisteredPlayer, GuestPlayer]


class Team(BaseModel):
    name: str
    players: List[PlayerEntry] = []


class GameOut(BaseModel):
    id: str
    code: str
    createdBy: str
    status: str
    teamA: Team
    teamB: Team
    scoreA: int = 0
    scoreB: int = 0
    createdAt: str
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None


class GameSummaryOut(BaseModel):
    id: str
    code: str
    teamAName: str
    teamBName: str
    scoreA: int
    scoreB: int
    status: str
    createdAt: str
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None


class CreateGameRequest(BaseModel):
    teamAName: str = "Team A"
    teamBName: str = "Team B"


class JoinGameRequest(BaseModel):
    code: str


class AddGuestRequest(BaseModel):
    teamSide: Literal["a", "b"]
    name: str
    jerseyNumber: Optional[int] = None
    position: Optional[Position] = None


class AssignPlayerRequest(BaseModel):
    userId: str
    teamSide: Literal["a", "b"]


class UpdateScoreRequest(BaseModel):
    scoreA: int
    scoreB: int
