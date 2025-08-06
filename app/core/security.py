# ==============================================================================
# File: app/core/security.py  
# Deskripsi: Menangani semua hal terkait keamanan: hashing password dan JWT.
# OPTIMIZED VERSION - Lower bcrypt rounds for development/testing
# ==============================================================================
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from .config import settings

# OPTIMIZED: Lower bcrypt rounds untuk development/testing
# Production: gunakan rounds=12, Development/Testing: gunakan rounds=4-6
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=4  # Drastically faster! (vs default 12)
)

ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi password plain dengan hash."""
    import time
    start = time.time()
    result = pwd_context.verify(plain_password, hashed_password)
    end = time.time()
    print(f"Password verification took: {end - start:.4f}s")
    return result

def get_password_hash(password: str) -> str:
    """Membuat hash dari password."""
    import time
    start = time.time()
    result = pwd_context.hash(password)
    end = time.time()
    print(f"Password hashing took: {end - start:.4f}s")
    return result

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Membuat JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt