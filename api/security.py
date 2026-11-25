import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException, Request

from .services import verify_password

SESSION_COOKIE = "caderneta_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


def _secret() -> bytes:
    value = os.environ.get("SESSION_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("SESSION_SECRET precisa ter pelo menos 32 caracteres.")
    return value.encode()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_session(username: str, role: str) -> str:
    payload = _encode(json.dumps({
        "sub": username,
        "role": role,
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
    }, separators=(",", ":")).encode())
    signature = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_session(token: str | None):
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(_decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(data.get("exp", 0)) <= int(time.time()):
        return None
    return {"username": data["sub"], "role": data["role"]}


def current_user(request: Request):
    session = read_session(request.cookies.get(SESSION_COOKIE))
    if not session:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Entre para continuar."})
    return session


def require_roles(*roles):
    def dependency(user=current_user):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Ação não autorizada."})
        return user
    return dependency


def integration_auth(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    expected = os.environ.get("API_INTEGRATION_KEY", "")
    if len(expected) < 24 or not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Chave de integração inválida."})
    return "sistema_relacional"


def authenticate_user(db, username: str, password: str):
    user = db.usuarios.find_one({"username": username, "active": True})
    if not user or not verify_password(password, user.get("password", {})):
        return None
    return {"username": user["username"], "role": user.get("role", "LEITURA")}
