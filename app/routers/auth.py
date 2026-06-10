from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from ..database import get_db
from ..config import settings
from ..services.auth import (
    generate_otp,
    send_otp,
    create_token,
    get_or_create_user,
    DEV_OTP,
)
from ..schemas.user import UserOut, PlayerStats

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory OTP store: {phone: (code, expires_at)}
_otp_store: dict[str, tuple[str, datetime]] = {}


def _store_otp(phone: str, code: str) -> None:
    _otp_store[phone] = (code, datetime.now(timezone.utc) + timedelta(minutes=5))


def _verify_otp(phone: str, code: str) -> bool:
    entry = _otp_store.get(phone)
    if not entry:
        return False
    stored_code, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        del _otp_store[phone]
        return False
    if stored_code != code:
        return False
    del _otp_store[phone]
    return True


class SendOTPRequest(BaseModel):
    phone: str


class VerifyOTPRequest(BaseModel):
    phone: str
    code: str


def _user_out(user) -> UserOut:
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


@router.post("/send-otp")
def send_otp_endpoint(req: SendOTPRequest):
    code = generate_otp() if settings.twilio_account_sid else DEV_OTP
    _store_otp(req.phone, code)
    send_otp(req.phone, code)
    return {"message": "Code sent"}


@router.post("/verify-otp")
def verify_otp_endpoint(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    if not _verify_otp(req.phone, req.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
    user, is_new = get_or_create_user(db, req.phone)
    token = create_token(user.id)
    return {
        "token": token,
        "user": _user_out(user),
        "isNewUser": is_new,
    }
