"""Authentication module for JWT and user management"""
import os
from datetime import datetime, timedelta
from typing import Optional
import logging

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing (bcrypt; replaces the unmaintained passlib, which is
# incompatible with modern bcrypt releases). Existing passlib-hashed
# $2b$ passwords in the database remain verifiable via bcrypt.checkpw.


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Hash password with bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class TokenData(BaseModel):
    """JWT token data"""
    user_id: str
    email: str
    role: str


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("email")
        role = payload.get("role")
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, email=email, role=role)
    except InvalidTokenError as e:
        logger.error(f"Token decode error: {e}")
        return None
