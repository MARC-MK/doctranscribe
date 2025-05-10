"""
Authentication module with JWT support for DocTranscribe.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Session, select

from .database import get_session
from .models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-here-make-it-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    user: Dict


class TokenData(BaseModel):
    """Token data model."""
    email: Optional[str] = None
    user_id: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        logger.info(f"Token payload: email={email}, user_id={user_id}")
        
        if email is None or user_id is None:
            logger.warning("Missing email or user_id in token")
            raise credentials_exception
            
        TokenData(email=email, user_id=user_id)
        
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception
    
    try:
        # Properly handle the string user_id - convert to UUID before querying
        try:
            # Convert string user_id to UUID
            user_uuid = UUID(user_id)
            logger.info(f"Converted user_id to UUID: {user_uuid}")
            
            # Use the UUID object for querying
            user = db.exec(select(User).where(User.id == user_uuid)).first()
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert user_id to UUID: {str(e)}")
            # Fallback to query by email
            user = db.exec(select(User).where(User.email == email)).first()
            
        if user is None:
            logger.warning(f"No user found for ID: {user_id} or email: {email}")
            raise credentials_exception
        
        logger.info(f"Found user: {user.email}")
        return user
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise credentials_exception 