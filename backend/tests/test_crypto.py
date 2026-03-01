import pytest
from cryptography.fernet import Fernet
from unittest.mock import patch

from app.services.crypto import encrypt_credentials, decrypt_credentials


TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _set_fernet_key():
    with patch("app.services.crypto.settings") as mock_settings:
        mock_settings.FERNET_KEY = TEST_KEY
        yield


def test_round_trip():
    """Encrypting then decrypting returns the original data."""
    creds = {"username": "admin", "password": "s3cret"}
    encrypted = encrypt_credentials(creds)
    assert isinstance(encrypted, bytes)
    assert decrypt_credentials(encrypted) == creds


def test_encrypted_is_opaque():
    """Encrypted output doesn't contain plaintext."""
    creds = {"username": "admin", "password": "s3cret"}
    encrypted = encrypt_credentials(creds)
    assert b"admin" not in encrypted
    assert b"s3cret" not in encrypted


def test_decrypt_bad_data():
    """Decrypting garbage raises ValueError."""
    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_credentials(b"not-valid-fernet-data")


def test_missing_key():
    """Missing FERNET_KEY raises ValueError."""
    with patch("app.services.crypto.settings") as mock_settings:
        mock_settings.FERNET_KEY = ""
        with pytest.raises(ValueError, match="FERNET_KEY is not configured"):
            encrypt_credentials({"user": "x"})


def test_different_keys_cannot_decrypt():
    """Data encrypted with one key can't be decrypted with another."""
    creds = {"username": "test"}
    encrypted = encrypt_credentials(creds)

    other_key = Fernet.generate_key().decode()
    with patch("app.services.crypto.settings") as mock_settings:
        mock_settings.FERNET_KEY = other_key
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_credentials(encrypted)
