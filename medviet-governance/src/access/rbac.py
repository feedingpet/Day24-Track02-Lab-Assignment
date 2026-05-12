import casbin
from functools import wraps
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Header

MOCK_USERS = {
    "token-alice": {"username": "alice", "role": "admin"},
    "token-bob": {"username": "bob", "role": "ml_engineer"},
    "token-carol": {"username": "carol", "role": "data_analyst"},
    "token-dave": {"username": "dave", "role": "intern"},
}

_BASE = Path(__file__).resolve().parent
enforcer = casbin.Enforcer(
    str(_BASE / "model.conf"),
    str(_BASE / "policy.csv"),
)


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1].strip()
    user = MOCK_USERS.get(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user


def require_permission(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Unauthorized")

            username = current_user["username"]
            allowed = enforcer.enforce(username, resource, action)

            if not allowed:
                role = current_user["role"]
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{role}' cannot '{action}' on '{resource}'",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
