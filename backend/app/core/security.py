"""Security utilities for authentication and authorization"""

import base64
import hashlib
import secrets
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ROUTER_PASSWORD_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _get_router_password_fernet() -> Fernet:
    """Create a stable Fernet instance derived from the app secret."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and return (key, hash)"""
    key = secrets.token_urlsafe(32)
    key_hash = pwd_context.hash(key)
    return key, key_hash


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash"""
    return pwd_context.verify(plain_key, hashed_key)


def generate_secret_key() -> str:
    """Generate a random secret key for various purposes"""
    return secrets.token_urlsafe(32)


def is_encrypted_router_password(value: Optional[str]) -> bool:
    """Check whether a stored router password is encrypted."""
    return bool(value and value.startswith(ROUTER_PASSWORD_PREFIX))


def encrypt_router_password(password: Optional[str]) -> Optional[str]:
    """Encrypt a router password for database storage."""
    if not password:
        return None
    if is_encrypted_router_password(password):
        return password
    token = _get_router_password_fernet().encrypt(password.encode("utf-8")).decode("utf-8")
    return f"{ROUTER_PASSWORD_PREFIX}{token}"


def decrypt_router_password(password: Optional[str]) -> Optional[str]:
    """Decrypt a router password loaded from the database."""
    if not password:
        return None
    if not is_encrypted_router_password(password):
        return password
    token = password[len(ROUTER_PASSWORD_PREFIX):]
    try:
        return _get_router_password_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored router password cannot be decrypted") from exc
