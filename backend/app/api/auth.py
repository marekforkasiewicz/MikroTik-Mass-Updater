"""Authentication API endpoints"""

from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import (
    LoginRequest, LoginResponse, RefreshRequest, TokenResponse,
    PasswordChangeRequest, UserResponse
)
from ..services.auth_service import AuthService
from ..core.deps import get_current_active_user, CurrentUser
from ..config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookie(response: Response, key: str, value: str, max_age: int) -> None:
    """Apply consistent cookie settings for auth tokens."""
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=max_age,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    """Login with username and password"""
    auth_service = AuthService(db)
    result = auth_service.login(form_data.username, form_data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set cookies for browser-based auth
    _set_auth_cookie(
        response,
        "access_token",
        result.access_token,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    _set_auth_cookie(
        response,
        "refresh_token",
        result.refresh_token,
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return result


@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    response: Response,
    login_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Login with JSON body"""
    auth_service = AuthService(db)
    result = auth_service.login(login_data.username, login_data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Set cookies
    _set_auth_cookie(
        response,
        "access_token",
        result.access_token,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    _set_auth_cookie(
        response,
        "refresh_token",
        result.refresh_token,
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[str, Cookie()] = None,
    body: RefreshRequest = None
):
    """Refresh access token"""
    token = refresh_token or (body.refresh_token if body else None)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )

    auth_service = AuthService(db)
    result = auth_service.refresh_tokens(token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    access_token, new_refresh_token = result

    # Update cookies
    _set_auth_cookie(
        response,
        "access_token",
        access_token,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    _set_auth_cookie(
        response,
        "refresh_token",
        new_refresh_token,
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear cookies"""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information"""
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Change current user's password"""
    auth_service = AuthService(db)
    success = auth_service.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    return {"message": "Password changed successfully"}
