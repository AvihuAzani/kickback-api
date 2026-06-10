import jwt
import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from ..config import settings
from ..models.user import User

DEV_OTP = "123456"  # used when Twilio is not configured


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def send_otp(phone: str, code: str) -> None:
    if not settings.twilio_account_sid:
        # Dev mode: print to stdout, accept 123456
        print(f"[DEV OTP] {phone} → {code}")
        return
    from twilio.rest import Client  # lazy import
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    client.messages.create(
        body=f"Your Kickback code is {code}",
        from_=settings.twilio_from_number,
        to=phone,
    )


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    return payload["sub"]


def get_or_create_user(db: Session, phone: str) -> tuple[User, bool]:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user, False
    user = User(phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True
