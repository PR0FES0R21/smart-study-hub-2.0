# ==============================================================================
# File: app/schemas/token.py
# Deskripsi: Skema Pydantic untuk response token JWT.
# ==============================================================================
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None