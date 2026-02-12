"""
AES-GCM encryption for credential storage in the database.
This provides a durable fallback when Vault is unavailable or loses data.
"""

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(secret: str) -> bytes:
    """Derive a 256-bit AES key from the app secret."""
    return hashlib.sha256(secret.encode()).digest()


def encrypt_credentials(credentials: dict, secret_key: str) -> str:
    """Encrypt credentials dict to a base64 string (AES-256-GCM)."""
    key = _derive_key(secret_key)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(credentials).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    # Encode as: base64(nonce + ciphertext)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_credentials(encrypted: str, secret_key: str) -> dict:
    """Decrypt a base64 encrypted string back to credentials dict."""
    key = _derive_key(secret_key)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())
