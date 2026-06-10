from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..schemas.game import (
    GameOut, GameSummaryOut, CreateGameRequest, JoinGameRequest,
    AddGuestRequest, AssignPlayerRequest, GuestPlayer, UpdateScoreRequest,
)
from ..services import game as game_service
from ..signaling import room_manager

router = APIRouter(prefix="/games", tags=["games"])


def _out(game) -> GameOut:
    return GameOut(**game_service.game_to_schema(game))


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=GameOut, status_code=201)
def create_game(
    req: CreateGameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.create_game(db, current_user.id, req.teamAName, req.teamBName)
    return _out(game)


@router.post("/join", response_model=GameOut)
def join_game(
    req: JoinGameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_code(db, req.code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return _out(game)


@router.get("/my", response_model=list[GameSummaryOut])
def my_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    games = game_service.get_games_for_user(db, current_user.id)
    return [
        GameSummaryOut(
            id=g.id,
            code=g.code,
            teamAName=g.team_a_name,
            teamBName=g.team_b_name,
            scoreA=g.score_a or 0,
            scoreB=g.score_b or 0,
            status=g.status.value,
            createdAt=g.created_at.isoformat(),
            startedAt=g.started_at.isoformat() if g.started_at else None,
            finishedAt=g.finished_at.isoformat() if g.finished_at else None,
        )
        for g in games
    ]


@router.get("/{game_id}", response_model=GameOut)
def get_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return _out(game)


# ── Players ───────────────────────────────────────────────────────────────────

@router.post("/{game_id}/guests", response_model=GuestPlayer, status_code=201)
def add_guest(
    game_id: str,
    req: AddGuestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    guest = game_service.add_guest(db, game, req.teamSide, req.name, req.jerseyNumber, req.position)
    return GuestPlayer(**guest)


@router.post("/{game_id}/players", status_code=204)
def assign_player(
    game_id: str,
    req: AssignPlayerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    target_user = db.query(User).filter(User.id == req.userId).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    game_service.assign_player(db, game, target_user, req.teamSide)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@router.post("/{game_id}/start", status_code=204)
def start_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can start the game")
    game_service.start_game(db, game)


@router.post("/{game_id}/finish", status_code=204)
async def finish_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    game_service.finish_game(db, game)
    await room_manager.notify_monitors(game_id, {"type": "game_finished"})


# ── Score ─────────────────────────────────────────────────────────────────────

@router.put("/{game_id}/score", status_code=204)
async def update_score(
    game_id: str,
    req: UpdateScoreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game = game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    game_service.update_score(db, game, req.scoreA, req.scoreB)
    await room_manager.notify_monitors(game_id, {
        "type": "score_update",
        "scoreA": req.scoreA,
        "scoreB": req.scoreB,
    })
