"""
WhiteRock Blessings Engine - Authentication Tests
Tests for JWT authentication and password handling.
"""

import pytest
from app.auth import (
    hash_password, verify_password, 
    create_access_token, create_refresh_token,
    decode_access_token, blacklist_token, is_token_blacklisted
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "securepassword123"
    hashed = hash_password(password)
    
    # Hash should be different from original
    assert hashed != password
    
    # Verification should work
    assert verify_password(password, hashed) == True
    assert verify_password("wrongpassword", hashed) == False


def test_access_token_creation():
    """Test JWT access token creation."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)
    
    assert token is not None
    assert len(token) > 0
    
    # Decode and verify
    payload = decode_access_token(token)
    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"


def test_refresh_token_creation():
    """Test JWT refresh token creation."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_refresh_token(data)
    
    assert token is not None
    
    # Decode and verify type
    payload = decode_access_token(token, token_type="refresh")
    assert payload["type"] == "refresh"


def test_token_blacklist():
    """Test token blacklisting for logout."""
    data = {"sub": "123"}
    token = create_access_token(data)
    
    # Token should not be blacklisted initially
    assert is_token_blacklisted(token) == False
    
    # Blacklist the token
    blacklist_token(token)
    
    # Token should now be blacklisted
    assert is_token_blacklisted(token) == True


def test_access_token_type_validation():
    """Test that access tokens cannot be used as refresh tokens."""
    data = {"sub": "123"}
    access_token = create_access_token(data)
    
    # Should fail when trying to decode as refresh token
    with pytest.raises(Exception):  # HTTPException
        decode_access_token(access_token, token_type="refresh")



