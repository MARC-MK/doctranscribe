"""
Authentication router for DocTranscribe.
"""
import logging
from datetime import timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from ..auth import (authenticate_user, create_access_token, get_current_user,
                   get_password_hash)
from ..database import get_session
from ..models import User, UserRole

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)


# Request and response models
class UserCreate(BaseModel):
    """User creation request model."""
    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: EmailStr
    name: str
    role: str
    is_active: bool
    created_at: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/register", response_model=LoginResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_session)) -> LoginResponse:
    """Register a new user."""
    # Check if user already exists
    existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password=hashed_password,
        name=user_data.name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": str(new_user.id)}
    )
    
    # Return user with token
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            name=new_user.name,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat()
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
) -> LoginResponse:
    """Authenticate user and return JWT token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create and return token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> List[UserResponse]:
    """Get all users (admin only)."""
    # Check if user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    # Get all users
    users = db.exec(select(User)).all()
    
    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ] 