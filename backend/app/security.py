import hashlib
import hmac
import ipaddress
import secrets
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return str(payload["sub"])


def opaque_token(prefix: str = "") -> str:
    return prefix + secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def webhook_signature(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def validate_webhook_url(url: str, *, allow_private: bool | None = None) -> None:
    allow_private = settings.allow_private_webhook_urls if allow_private is None else allow_private
    parsed = urlparse(url)
    if parsed.scheme not in ({"http", "https"} if allow_private else {"https"}) or not parsed.hostname:
        raise ValueError("Webhook URL must use HTTPS and include a hostname")
    if allow_private:
        return
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ValueError("Webhook hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private or special network webhook targets are not allowed")

