"""Authentication service"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..models.user import User, APIKey
from ..schemas.user import UserCreate, UserUpdate, LoginResponse
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, generate_api_key
)
from ..config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def login(self, username: str, password: str) -> Optional[LoginResponse]:
        """Login and return tokens"""
        user = self.authenticate_user(username, password)
        if not user:
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()

        # Create tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={"role": user.role, "username": user.username}
        )
        refresh_token = create_refresh_token(subject=user.id)

        from ..schemas.user import UserResponse
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )

    def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Refresh access token using refresh token"""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None

        # Create new tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={"role": user.role, "username": user.username}
        )
        new_refresh_token = create_refresh_token(subject=user.id)

        return access_token, new_refresh_token

    def create_user(self, user_data: UserCreate, created_by: Optional[int] = None) -> User:
        """Create a new user"""
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=hash_password(user_data.password)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"User created: {user.username}")
        return user

    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user details"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        logger.info(f"User updated: {user.username}")
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        logger.info(f"User deleted: {user.username}")
        return True

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        if not verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = hash_password(new_password)
        self.db.commit()
        logger.info(f"Password changed for user: {user.username}")
        return True

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def list_users(self, skip: int = 0, limit: int = 100) -> Tuple[list, int]:
        """List all users"""
        total = self.db.query(User).count()
        users = self.db.query(User).offset(skip).limit(limit).all()
        return users, total

    def create_api_key(
        self,
        user_id: int,
        name: str,
        scopes: Optional[list] = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[APIKey, str]:
        """Create API key for user"""
        key, key_hash = generate_api_key()
        key_prefix = key[:8]

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=",".join(scopes) if scopes else None,
            expires_at=expires_at
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        logger.info(f"API key created for user {user_id}: {name}")
        return api_key, key

    def revoke_api_key(self, api_key_id: int, user_id: int) -> bool:
        """Revoke an API key"""
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id,
            APIKey.user_id == user_id
        ).first()

        if not api_key:
            return False

        api_key.is_active = False
        self.db.commit()
        logger.info(f"API key revoked: {api_key.name}")
        return True

    def delete_api_key(self, api_key_id: int, user_id: int) -> bool:
        """Delete an API key"""
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id,
            APIKey.user_id == user_id
        ).first()

        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()
        logger.info(f"API key deleted: {api_key.name}")
        return True

    def list_api_keys(self, user_id: int) -> list:
        """List API keys for user"""
        return self.db.query(APIKey).filter(APIKey.user_id == user_id).all()

    def ensure_admin_exists(self):
        """Ensure at least one admin user exists"""
        admin = self.db.query(User).filter(User.role == "admin").first()
        if admin:
            return

        if not settings.DEFAULT_ADMIN_PASSWORD:
            logger.warning(
                "No admin user found and DEFAULT_ADMIN_PASSWORD is not configured. "
                "Skipping automatic admin creation."
            )
            return

        logger.info("No admin user found, creating default admin")
        admin = User(
            username="admin",
            email="admin@example.com",
            full_name="Administrator",
            role="admin",
            is_superuser=True,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD)
        )
        self.db.add(admin)
        self.db.commit()
        logger.info("Default admin user created (username: admin)")
