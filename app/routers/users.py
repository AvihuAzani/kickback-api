from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..schemas.user import UserOut, UserUpdate, PlayerStats

router = APIRouter(prefix="/users", tags=["users"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        phone=user.phone,
        name=user.name,
        height=user.height,
        weight=user.weight,
        position=user.position,
        jerseyNumber=user.jersey_number,
        photoUrl=user.photo_url,
        stats=PlayerStats(
            goals=user.goals,
            assists=user.assists,
            minutesPlayed=user.minutes_played,
            fouls=user.fouls,
            gamesPlayed=user.games_played,
        ),
        createdAt=user.created_at.isoformat(),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_none=True).items():
        snake = {
            "jerseyNumber": "jersey_number",
            "photoUrl": "photo_url",
        }.get(field, field)
        setattr(current_user, snake, value)
    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)
