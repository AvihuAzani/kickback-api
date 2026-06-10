from sqlalchemy import Column, String, Enum, DateTime, JSON, Integer
from datetime import datetime, timezone
import uuid
import enum
from ..database import Base


class GameStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    finished = "finished"


class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(6), unique=True, nullable=False, index=True)
    created_by = Column(String, nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.waiting)
    team_a_name = Column(String, default="Team A")
    team_b_name = Column(String, default="Team B")

    # Stored as JSON list of {type, userId/id, name, jerseyNumber, position}
    team_a_players = Column(JSON, default=list)
    team_b_players = Column(JSON, default=list)

    score_a = Column(Integer, default=0)
    score_b = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
