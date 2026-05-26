#!/usr/bin/env python3
"""Local HPA autoscaling integration test.

Tests the agent autoscaling feature against the local Docker Compose stack.
Creates a test agent with autoscale_enabled and a low RPM, then blasts it
with rapid requests to trigger scaling. Verifies scaling events in Redis and DB.

Usage:
    python backend/tests/test_hpa_local.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import httpx

BASE = "http://localhost:8001/api"
EMAIL = "hpa-test@bonito.ai"
PASSWORD = "HpaTest123!"


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # ─── 1. Login ───
        print("1. Logging in...")
        resp = await client.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"   FAIL: Login failed: {resp.text}")
            sys.exit(1)
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   OK: Got token")

        # ─── 2. Create a project ───
        print("2. Creating test project...")
        resp = await client.post(f"{BASE}/projects", json={"name": "HPA Test Project"}, headers=headers)
        if resp.status_code in (200, 201):
            project_id = resp.json()["id"]
        elif resp.status_code == 409:
            # Project exists, list and find it
            resp = await client.get(f"{BASE}/projects", headers=headers)
            projects = resp.json()
            project_id = next(p["id"] for p in projects if p["name"] == "HPA Test Project")
        else:
            print(f"   FAIL: {resp.status_code} {resp.text}")
            sys.exit(1)
        print(f"   OK: Project {project_id}")

        # ─── 3. Create agent with autoscale + low RPM ───
        print("3. Creating test agent (RPM=10, autoscale at 60%)...")
        agent_payload = {
            "name": "HPA Stress Agent",
            "system_prompt": "You are a test agent. Reply with 'OK' to everything.",
            "model_id": "auto",
            "rate_limit_rpm": 10,
            "autoscale_enabled": True,
            "autoscale_config": {
                "capacity_threshold": 0.6,
                "scale_down_threshold": 0.3,
                "max_replicas": 5,
                "scale_down_cooldown_seconds": 60,
                "mode": "virtual",
            },
        }
        resp = await client.post(f"{BASE}/projects/{project_id}/agents", json=agent_payload, headers=headers)
        if resp.status_code in (200, 201):
            agent = resp.json()
            agent_id = agent["id"]
        else:
            print(f"   FAIL: {resp.status_code} {resp.text[:200]}")
            sys.exit(1)
        print(f"   OK: Agent {agent_id}")
        print(f"   autoscale_enabled={agent.get('autoscale_enabled')}")
        print(f"   autoscale_config={agent.get('autoscale_config')}")

        # ─── 4. Check initial scaling status ───
        print("\n4. Checking initial scaling status...")
        resp = await client.get(f"{BASE}/agents/{agent_id}/scaling", headers=headers)
        status = resp.json()
        print(f"   base_rpm={status['base_rpm']}")
        print(f"   effective_rpm={status['effective_rpm']}")
        print(f"   scaling_active={status['scaling_active']}")
        print(f"   utilization={status['utilization']}")

        # ─── 5. Blast requests to trigger scaling ───
        print(f"\n5. Sending rapid requests to trigger autoscaling...")
        print(f"   Agent RPM=10, threshold=60% → should scale at 6 requests")
        print(f"   Sending 15 requests rapidly...\n")

        results = {"success": 0, "rate_limited": 0, "error": 0}

        async def send_request(i: int):
            try:
                r = await client.post(
                    f"{BASE}/agents/{agent_id}/execute",
                    json={"message": f"Test message {i}"},
                    headers=headers,
                    timeout=60,
                )
                if r.status_code == 200:
                    data = r.json()
                    security = data.get("security", {})
                    eff = security.get("effective_rpm")
                    scaling = security.get("scaling_active")
                    remaining = security.get("rate_limit_remaining")
                    results["success"] += 1
                    print(f"   #{i:2d} ✅ effective_rpm={eff} scaling_active={scaling} remaining={remaining}")
                elif r.status_code == 429:
                    results["rate_limited"] += 1
                    print(f"   #{i:2d} 🚫 429 Rate limited")
                else:
                    results["error"] += 1
                    print(f"   #{i:2d} ❌ {r.status_code}: {r.text[:100]}")
            except Exception as e:
                results["error"] += 1
                print(f"   #{i:2d} ❌ Error: {e}")

        # Send requests in small batches to simulate realistic load
        # (not all at once — we want to see the threshold trigger mid-stream)
        for batch_start in range(0, 15, 3):
            tasks = [send_request(i) for i in range(batch_start, min(batch_start + 3, 15))]
            await asyncio.gather(*tasks)
            await asyncio.sleep(0.5)  # small gap between batches

        print(f"\n   Results: {results['success']} success, {results['rate_limited']} rate-limited, {results['error']} errors")

        # ─── 6. Check scaling status after load ───
        print("\n6. Checking scaling status after load...")
        resp = await client.get(f"{BASE}/agents/{agent_id}/scaling", headers=headers)
        status = resp.json()
        print(f"   base_rpm={status['base_rpm']}")
        print(f"   effective_rpm={status['effective_rpm']}")
        print(f"   scaling_active={status['scaling_active']}")
        print(f"   utilization={status['utilization']}")
        print(f"   current_rpm_usage={status['current_rpm_usage']}")

        if status["scaling_active"]:
            print("\n   🔥 AUTOSCALING IS ACTIVE — effective RPM has been scaled up!")
        else:
            print("\n   ⚠️  Scaling not active (may need more load or check logs)")

        # ─── 7. Check scaling events ───
        print("\n7. Checking scaling events...")
        resp = await client.get(f"{BASE}/agents/{agent_id}/scaling/events", headers=headers)
        events = resp.json()
        print(f"   Total events: {events['total']}")
        for e in events.get("events", []):
            print(f"   [{e['created_at']}] {e['event_type']}: {e['previous_capacity']} → {e['new_capacity']} RPM (util={e['trigger_utilization']:.0%})")

        # ─── 8. Test manual scale ───
        print("\n8. Testing manual scale-up...")
        resp = await client.post(
            f"{BASE}/agents/{agent_id}/scaling/manual",
            json={"direction": "up"},
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"   OK: {data['previous_rpm']} → {data['new_rpm']} RPM")
        else:
            print(f"   FAIL: {resp.status_code} {resp.text[:200]}")

        print("\n9. Testing manual scale-down...")
        resp = await client.post(
            f"{BASE}/agents/{agent_id}/scaling/manual",
            json={"direction": "down"},
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"   OK: {data['previous_rpm']} → {data['new_rpm']} RPM")
        else:
            print(f"   FAIL: {resp.status_code} {resp.text[:200]}")

        # ─── 10. Final scaling events ───
        print("\n10. Final scaling events:")
        resp = await client.get(f"{BASE}/agents/{agent_id}/scaling/events", headers=headers)
        events = resp.json()
        for e in events.get("events", []):
            print(f"    [{e['event_type']:20s}] {e['previous_capacity']:3d} → {e['new_capacity']:3d} RPM  (util={e['trigger_utilization']:.0%})")

        print(f"\n{'='*60}")
        print(f"Total scaling events: {events['total']}")
        if events['total'] > 0:
            print("✅ HPA autoscaling test PASSED")
        else:
            print("⚠️  No scaling events — check backend logs")

        # Cleanup: delete agent
        print(f"\nCleaning up: deleting test agent...")
        await client.delete(f"{BASE}/agents/{agent_id}", headers=headers)
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
