from datetime import timedelta
import asyncio
import jwt
import pytest
from fastapi import HTTPException
from routers import auth


def test_token_round_trip():
    token = auth.create_access_token("alice", "42", "admin", timedelta(minutes=5))
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "alice" and payload["id"] == "42" and payload["role"] == "admin"
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


@pytest.mark.parametrize("delta", [timedelta(seconds=-5)])
def test_expired_token_rejected(delta):
    token = auth.create_access_token("alice", "42", "admin", delta)
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_user(token, db=None))
    assert e.value.status_code == 401
