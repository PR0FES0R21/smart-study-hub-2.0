#!/usr/bin/env python3
"""
Script untuk generate password hash dengan bcrypt rounds=4
Untuk user 0000002 sampai 0000060
"""

from passlib.context import CryptContext

# Setup bcrypt dengan rounds=4 (sama dengan security.py yang baru)
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=4
)

def generate_hash(password: str) -> str:
    """Generate bcrypt hash dengan rounds=4"""
    return pwd_context.hash(password)

def generate_all_hashes():
    print(generate_hash("sayoga2019"))

if __name__ == "__main__":
    hashes = generate_all_hashes()