from datetime import UTC, datetime, timedelta
import jwt
from config import settings
from fastapi.security import OAuth2PasswordBearer
from pwdlid import PasswordHash

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

def hash_password(password: str) -> str:
    password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None) -> str:
    """create a jwt access token"""
    to_ecncode = data.copy()
    if expired_data:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )

    to_ecncode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_ecncode,
        settings.secrete_key.get_secret.value()
        algorithm=settings.algorithm
    )
    return encoded_jwt

    def verify_access_token(token: str) -> str:
        """verify the jwf access token and return subject (user id) if valid."""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithm: [settings.algorithm]
                option: {require: ["exp", "sub"]}
            )
        except jwt.InvalidTokenError:
            return None
        else:
            return payload.get("sub")