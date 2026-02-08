import uuid
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyResponse

router = APIRouter(prefix="/policies", tags=["policies"])

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

_policies: dict[str, dict] = {}

def _seed():
    if _policies:
        return
    seeds = [
        {"name": "Production Model Whitelist", "type": "model_access",
         "description": "Only approved models can be deployed to production environments",
         "rules_json": {"allowed_models": ["GPT-4o", "Claude 3.5 Sonnet"], "environment": "production"},
         "enabled": True},
        {"name": "Daily Spend Cap", "type": "spend_limits",
         "description": "Maximum daily spend across all providers",
         "rules_json": {"max_daily_spend": 500, "alert_at_percentage": 80, "action": "alert_and_block"},
         "enabled": True},
        {"name": "EU Data Residency", "type": "region_restrictions",
         "description": "Customer data must stay within EU regions",
         "rules_json": {"allowed_regions": ["eu-west-1", "eu-central-1", "westeurope"], "applies_to": "customer_data"},
         "enabled": False},
        {"name": "PII Detection Required", "type": "data_classification",
         "description": "All inputs must be scanned for PII before processing",
         "rules_json": {"scan_inputs": True, "scan_outputs": True, "block_on_detection": False, "log_detections": True},
         "enabled": True},
    ]
    for s in seeds:
        pid = str(uuid.uuid4())
        _policies[pid] = {"id": pid, "org_id": DEFAULT_ORG_ID, "created_at": "2026-01-20T10:00:00Z", **s}

_seed()


@router.get("/", response_model=List[PolicyResponse])
async def list_policies():
    return list(_policies.values())


@router.post("/", response_model=PolicyResponse, status_code=201)
async def create_policy(data: PolicyCreate):
    pid = str(uuid.uuid4())
    policy = {
        "id": pid, "org_id": DEFAULT_ORG_ID,
        "name": data.name, "type": data.type,
        "rules_json": data.rules_json,
        "description": data.description,
        "enabled": data.enabled,
        "created_at": "2026-02-07T10:00:00Z",
    }
    _policies[pid] = policy
    return policy


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(policy_id: str, data: PolicyUpdate):
    if policy_id not in _policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    p = _policies[policy_id]
    if data.name is not None: p["name"] = data.name
    if data.type is not None: p["type"] = data.type
    if data.rules_json is not None: p["rules_json"] = data.rules_json
    if data.description is not None: p["description"] = data.description
    if data.enabled is not None: p["enabled"] = data.enabled
    return p


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(policy_id: str):
    if policy_id not in _policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    del _policies[policy_id]
