"""FastAPI dependencies for authentication and authorization"""

from typing import Annotated, Optional, List

from fastapi import Depends, HTTPException, status, Cookie, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, APIKey
from .security import decode_token, verify_api_key
from .permissions import Role, Permission, has_permission, has_any_permission


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_token_from_cookie_or_header(
    authorization: Annotated[Optional[str], Header()] = None,
    access_token: Annotated[Optional[str], Cookie()] = None,
) -> Optional[str]:
    """Extract token from Authorization header or cookie"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return access_token


async def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(get_token_from_cookie_or_header)] = None,
    api_key: Annotated[Optional[str], Depends(api_key_header)] = None,
) -> User:
    """Get current authenticated user from token or API key"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = None

    # Try token authentication first
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()

    # Try API key authentication if token didn't work
    if not user and api_key:
        # Get first 8 chars as prefix for faster lookup
        prefix = api_key[:8] if len(api_key) >= 8 else api_key
        api_key_records = db.query(APIKey).filter(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True
        ).all()

        for key_record in api_key_records:
            if verify_api_key(api_key, key_record.key_hash):
                # Check expiration
                if key_record.expires_at and key_record.expires_at < __import__('datetime').datetime.utcnow():
                    continue
                user = key_record.user
                # Update last used
                key_record.last_used_at = __import__('datetime').datetime.utcnow()
                db.commit()
                break

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_optional_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(get_token_from_cookie_or_header)] = None,
    api_key: Annotated[Optional[str], Depends(api_key_header)] = None,
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    if not token and not api_key:
        return None

    try:
        user = await get_current_user(db, token, api_key)
        return user
    except HTTPException:
        return None


def require_role(allowed_roles: List[Role]):
    """Dependency to require specific roles"""
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role = Role(current_user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


def require_permission(permission: Permission):
    """Dependency to require a specific permission"""
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role = Role(current_user.role)
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        return current_user
    return permission_checker


def require_any_permission(permissions: List[Permission]):
    """Dependency to require any of the specified permissions"""
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role = Role(current_user.role)
        if not has_any_permission(user_role, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker


# Convenience dependencies for common role checks
RequireAdmin = Depends(require_role([Role.ADMIN]))
RequireOperator = Depends(require_role([Role.ADMIN, Role.OPERATOR]))
RequireViewer = Depends(require_role([Role.ADMIN, Role.OPERATOR, Role.VIEWER]))


# Typed annotations for common use
CurrentUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_current_user)]
AdminUser = Annotated[User, Depends(require_role([Role.ADMIN]))]
OperatorUser = Annotated[User, Depends(require_role([Role.ADMIN, Role.OPERATOR]))]
