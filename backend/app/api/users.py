"""User management API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    APIKeyCreate, APIKeyResponse, APIKeyCreatedResponse, APIKeyListResponse
)
from ..services.auth_service import AuthService
from ..core.deps import CurrentUser, AdminUser
from ..core.permissions import Role

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all users (admin only)"""
    auth_service = AuthService(db)
    users, total = auth_service.list_users(skip, limit)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new user (admin only)"""
    auth_service = AuthService(db)

    # Check for existing username
    if auth_service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check for existing email
    if auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    user = auth_service.create_user(user_data, current_user.id)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Get user by ID"""
    # Users can view their own profile, admins can view anyone
    if current_user.id != user_id and current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    auth_service = AuthService(db)
    user = auth_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Update user"""
    # Users can update their own profile (limited), admins can update anyone
    is_self = current_user.id == user_id
    is_admin = current_user.role == Role.ADMIN.value

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Non-admins can't change their own role
    if is_self and not is_admin and user_data.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )

    # Non-admins can't deactivate themselves
    if is_self and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )

    auth_service = AuthService(db)
    user = auth_service.update_user(user_id, user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Delete user (admin only)"""
    # Can't delete yourself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    auth_service = AuthService(db)
    success = auth_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


# API Key endpoints
@router.get("/me/api-keys", response_model=APIKeyListResponse)
async def list_my_api_keys(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """List current user's API keys"""
    auth_service = AuthService(db)
    keys = auth_service.list_api_keys(current_user.id)

    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in keys],
        total=len(keys)
    )


@router.post("/me/api-keys", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new API key for current user"""
    auth_service = AuthService(db)
    api_key, full_key = auth_service.create_api_key(
        user_id=current_user.id,
        name=key_data.name,
        scopes=key_data.scopes,
        expires_in_days=key_data.expires_in_days
    )

    return APIKeyCreatedResponse(
        **APIKeyResponse.model_validate(api_key).model_dump(),
        key=full_key,
    )


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_api_key(
    key_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Delete an API key"""
    auth_service = AuthService(db)
    success = auth_service.delete_api_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.post("/me/api-keys/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)]
):
    """Revoke an API key (keep but deactivate)"""
    auth_service = AuthService(db)
    success = auth_service.revoke_api_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
