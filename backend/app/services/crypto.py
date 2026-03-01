import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise ValueError("FERNET_KEY is not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credentials(data: dict) -> bytes:
    """Encrypt a credentials dict to bytes using Fernet symmetric encryption."""
    fernet = _get_fernet()
    payload = json.dumps(data).encode()
    return fernet.encrypt(payload)


def decrypt_credentials(encrypted: bytes) -> dict:
    """Decrypt Fernet-encrypted bytes back to a credentials dict."""
    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted)
    except InvalidToken:
        raise ValueError("Failed to decrypt credentials — invalid key or corrupted data")
    return json.loads(decrypted)
