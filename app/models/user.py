from sqlalchemy import Column, String, Integer, Float, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from ..database import Base


class Position(str, enum.Enum):
    goalkeeper = "goalkeeper"
    defender = "defender"
    midfielder = "midfielder"
    forward = "forward"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    position = Column(Enum(Position), nullable=True)
    jersey_number = Column(Integer, nullable=True)
    photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # stats (denormalized for fast reads)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
