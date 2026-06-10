from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class Position(str, Enum):
    goalkeeper = "goalkeeper"
    defender = "defender"
    midfielder = "midfielder"
    forward = "forward"


class PlayerStats(BaseModel):
    goals: int = 0
    assists: int = 0
    minutesPlayed: int = 0
    fouls: int = 0
    gamesPlayed: int = 0


class UserOut(BaseModel):
    id: str
    phone: str
    name: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    position: Optional[Position] = None
    jerseyNumber: Optional[int] = None
    photoUrl: Optional[str] = None
    stats: PlayerStats
    createdAt: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    position: Optional[Position] = None
    jerseyNumber: Optional[int] = None
    photoUrl: Optional[str] = None
