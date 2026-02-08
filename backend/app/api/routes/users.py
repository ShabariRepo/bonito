import uuid
from uuid import UUID
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.audit_service import MOCK_USERS

router = APIRouter(prefix="/users", tags=["users"])

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# In-memory store seeded with mock data
_users: dict[str, dict] = {}

def _seed():
    if _users:
        return
    roles = ["admin", "admin", "editor", "viewer"]
    for i, u in enumerate(MOCK_USERS):
        _users[u["id"]] = {
            "id": u["id"],
            "org_id": str(DEFAULT_ORG_ID),
            "email": u["email"],
            "name": u["name"],
            "role": roles[i],
            "avatar_url": None,
            "created_at": "2026-01-15T10:00:00Z",
        }

_seed()


@router.get("/", response_model=List[UserResponse])
async def list_users():
    return list(_users.values())


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate):
    uid = str(uuid.uuid4())
    user = {
        "id": uid,
        "org_id": str(DEFAULT_ORG_ID),
        "email": data.email,
        "name": data.name,
        "role": data.role,
        "avatar_url": None,
        "created_at": "2026-02-07T10:00:00Z",
    }
    _users[uid] = user
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(user_id: str, data: UserUpdate):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    if data.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=422, detail="Invalid role")
    _users[user_id]["role"] = data.role
    return _users[user_id]


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: str):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    del _users[user_id]
