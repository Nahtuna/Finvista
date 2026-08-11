# -*- coding: utf-8 -*-
"""FastAPI dependencies: JWT auth, password hashing, rate limiting."""

import os
import base64
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

# Config
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Security validation
if not JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is required. "
        "Please set a strong random secret key in your environment."
    )

if len(JWT_SECRET_KEY) < 32:
    raise ValueError(
        "JWT_SECRET_KEY must be at least 32 characters long for security. "
        "Current length is insufficient."
    )


def validate_environment_variables():
    """Validate that required environment variables are set."""
    required_vars = {
        "DATABASE_URL": "Database connection string",
        "JWT_SECRET_KEY": "JWT secret key for authentication",
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.getenv(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables:\n" + 
            "\n".join(f"  - {var}" for var in missing_vars) +
            "\nPlease set these variables in your .env file or environment."
        )
    
    return True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)


def _verify_pbkdf2(password: str, hashed: str) -> bool:
    """Verify PBKDF2 SHA-256 hash."""
    try:
        parts = hashed.split("$")
        if len(parts) < 4:
            return False
        
        iterations = int(parts[1])
        salt = parts[2].encode("utf-8")
        target_hash = parts[3]
        
        calc_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        calc_hash_b64 = base64.b64encode(calc_hash).decode("ascii")
        return hmac.compare_digest(target_hash.encode("ascii"), calc_hash_b64.encode("ascii"))
    except Exception:
        return False


def verify_password(password: str, hashed: str) -> bool:
    """Verify password using PBKDF2."""
    return _verify_pbkdf2(password, hashed)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength requirements."""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character."
    
    return True, "Password meets strength requirements."


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 HMAC SHA-256."""
    salt = base64.b64encode(os.urandom(12)).decode("ascii")
    iterations = 30000
    calc_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    calc_hash_b64 = base64.b64encode(calc_hash).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt}${calc_hash_b64}"


def create_access_token(data: dict) -> str:
    """Generate JWT token with dynamic expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to retrieve the currently authenticated user."""
    from backend.core.database import SessionLocal, User
    
    db = SessionLocal()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"id": user.id, "username": user.username}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()
