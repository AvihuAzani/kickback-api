import random
import string
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models.game import Game, GameStatus
from ..models.user import User


def generate_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def create_game(db: Session, creator_id: str, team_a_name: str, team_b_name: str) -> Game:
    for _ in range(10):
        code = generate_code()
        if not db.query(Game).filter(Game.code == code).first():
            break
    game = Game(
        code=code,
        created_by=creator_id,
        team_a_name=team_a_name,
        team_b_name=team_b_name,
        team_a_players=[],
        team_b_players=[],
        score_a=0,
        score_b=0,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def get_game_by_id(db: Session, game_id: str) -> Game | None:
    return db.query(Game).filter(Game.id == game_id).first()


def get_game_by_code(db: Session, code: str) -> Game | None:
    return db.query(Game).filter(Game.code == code.upper()).first()


def get_games_for_user(db: Session, user_id: str) -> list[Game]:
    """Return all games the user created, ordered newest first."""
    return (
        db.query(Game)
        .filter(Game.created_by == user_id)
        .order_by(Game.created_at.desc())
        .limit(20)
        .all()
    )


def add_guest(
    db: Session,
    game: Game,
    team_side: str,
    name: str,
    jersey_number: int | None,
    position: str | None,
) -> dict:
    guest = {
        "type": "guest",
        "id": str(uuid.uuid4()),
        "name": name,
        "jerseyNumber": jersey_number,
        "position": position,
    }
    if team_side == "a":
        players = list(game.team_a_players or [])
        players.append(guest)
        game.team_a_players = players
    else:
        players = list(game.team_b_players or [])
        players.append(guest)
        game.team_b_players = players
    db.commit()
    db.refresh(game)
    return guest


def assign_player(db: Session, game: Game, user: User, team_side: str) -> None:
    entry = {
        "type": "registered",
        "userId": user.id,
        "name": user.name or user.phone,
        "jerseyNumber": user.jersey_number,
        "position": user.position.value if user.position else None,
    }
    for side in ("a", "b"):
        players = list((game.team_a_players if side == "a" else game.team_b_players) or [])
        filtered = [p for p in players if not (p.get("type") == "registered" and p.get("userId") == user.id)]
        if side == "a":
            game.team_a_players = filtered
        else:
            game.team_b_players = filtered

    if team_side == "a":
        players = list(game.team_a_players or [])
        players.append(entry)
        game.team_a_players = players
    else:
        players = list(game.team_b_players or [])
        players.append(entry)
        game.team_b_players = players
    db.commit()


def update_score(db: Session, game: Game, score_a: int, score_b: int) -> None:
    game.score_a = max(0, score_a)
    game.score_b = max(0, score_b)
    db.commit()


def start_game(db: Session, game: Game) -> None:
    game.status = GameStatus.active
    game.started_at = datetime.now(timezone.utc)
    db.commit()


def finish_game(db: Session, game: Game) -> None:
    game.status = GameStatus.finished
    game.finished_at = datetime.now(timezone.utc)
    db.commit()


def game_to_schema(game: Game) -> dict:
    return {
        "id": game.id,
        "code": game.code,
        "createdBy": game.created_by,
        "status": game.status.value,
        "teamA": {"name": game.team_a_name, "players": game.team_a_players or []},
        "teamB": {"name": game.team_b_name, "players": game.team_b_players or []},
        "scoreA": game.score_a or 0,
        "scoreB": game.score_b or 0,
        "createdAt": game.created_at.isoformat(),
        "startedAt": game.started_at.isoformat() if game.started_at else None,
        "finishedAt": game.finished_at.isoformat() if game.finished_at else None,
    }
