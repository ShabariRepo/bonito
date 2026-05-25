#!/usr/bin/env python3
"""100-Ticket Agentic Load Test for HPA Autoscaling.

End-to-end test simulating a Bulletproof Tier 1 IT support workflow:
- Triage Router (RPM=10, autoscale at 60%) delegates to specialists
- Password Specialist + Connectivity Specialist handle tickets
- Validates: routing accuracy, response quality, scaling events, no hallucinations

Usage:
    python backend/tests/test_hpa_100_tickets.py
"""

import asyncio
import json
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

# ─── Config ───
BASE = "http://localhost:8001/api"
EMAIL = "hpa-test@bonito.ai"
PASSWORD = "HpaTest123!"

TRIAGE_ID = "d150a53f-8490-4188-a785-6500444b4cf5"
PASSWORD_AGENT_ID = "b50a1143-aa7d-41ef-bdd7-fd995e97935e"
CONNECTIVITY_AGENT_ID = "3033ccf6-47be-4c2b-9723-65169af53523"

CONCURRENCY = 5  # requests in flight at once
BATCH_DELAY = 0.3  # seconds between batches

# ─── Ticket Templates ───
PASSWORD_TICKETS = [
    "I can't log into my email. It says my password expired.",
    "My Active Directory password needs to be reset. Username: jdoe",
    "I'm locked out of my account after too many failed attempts.",
    "MFA is not sending me a code on my phone. I changed phones last week.",
    "SSO login for Salesforce keeps redirecting to an error page.",
    "My VPN password expired but the self-service portal is down.",
    "I need to set up MFA for my new laptop. How do I enroll?",
    "Getting 'invalid credentials' on Outlook but I just changed my password.",
    "My account got locked after the password policy change last night.",
    "I forgot my password for the HR portal. Can you reset it?",
    "The Microsoft Authenticator app shows 'account not found'.",
    "I'm getting 'your session has expired' every 5 minutes in SharePoint.",
    "Need to reset my admin password for the CRM system urgently.",
    "Two-factor authentication keeps failing with the code I enter.",
    "My service account password for the API integration is expiring tomorrow.",
    "I can't complete the password reset — the security questions are wrong.",
    "Azure AD is showing 'user not found' when I try to log in.",
    "I need emergency access to the billing system but my account is disabled.",
    "Google Workspace login says my account is suspended.",
    "I keep getting password complexity errors — what are the requirements?",
    "My RSA token is out of sync. I can't generate valid codes.",
    "The Okta sign-in page is giving me a 403 Forbidden error.",
    "I changed my password yesterday but old password still works sometimes.",
    "Need help setting up a hardware security key for my account.",
    "My temporary password expired before I could use it.",
    "I'm a new employee and haven't received my login credentials yet.",
    "Can't log into the project management tool — says license expired.",
    "My YubiKey stopped working for authentication.",
    "Password sync between AD and O365 seems broken for my account.",
    "I'm getting 'account locked due to suspicious activity' on my email.",
    "Need to reset the break-glass admin account password.",
    "The SAML assertion for our custom app keeps failing.",
    "My Duo push notifications aren't coming through anymore.",
    "Can you extend my temporary elevated access for another 24 hours?",
    "I accidentally revealed my password — need an immediate change.",
    "The password manager extension isn't autofilling correctly.",
    "My Kerberos ticket keeps expiring mid-session.",
    "I need my API key rotated — the old one may have been compromised.",
    "Getting 'certificate error' when trying to authenticate to the portal.",
    "My biometric login (fingerprint) stopped working on the company laptop.",
    "I can't access the VDI — says my credentials are invalid.",
    "The self-service password reset tool says my email isn't registered.",
    "I need a temporary password bypass for the demo environment.",
    "My Azure MFA is set to phone call but my number changed.",
    "Getting 'token expired' error every time I try to approve MFA on my phone.",
    "I was just promoted and need access to the leadership dashboard.",
    "My password was changed by someone else — possible security breach.",
    "Can't complete onboarding — the credentials email went to spam.",
    "I need my old account merged with my new department account.",
    "The conditional access policy is blocking me from logging in from home.",
]

CONNECTIVITY_TICKETS = [
    "My VPN keeps disconnecting every 5 minutes. Windows 11.",
    "I can't connect to the office Wi-Fi. Other devices work fine.",
    "DNS resolution is failing — can't reach internal sites.",
    "My internet is extremely slow today, less than 1 Mbps.",
    "Remote desktop to my office PC keeps timing out.",
    "The network printer on 3rd floor isn't showing up on my laptop.",
    "I can't access the file server from home over VPN.",
    "Getting 'connection timed out' when accessing the internal wiki.",
    "My Teams calls keep dropping — seems like a network issue.",
    "I need port 8080 opened on the firewall for development.",
    "VPN client says 'authentication failed' but my password is correct.",
    "Wi-Fi is connected but I have no internet access in the conference room.",
    "My desktop lost network connectivity after the Windows update.",
    "Can't SSH into the staging server — connection refused on port 22.",
    "The guest Wi-Fi is down in the lobby. We have a client meeting.",
    "Slow network performance when accessing cloud resources.",
    "My Ethernet connection keeps dropping. Cable was replaced.",
    "Need VPN access set up for a new contractor starting Monday.",
    "The internal dashboard at dashboard.internal is unreachable.",
    "My video calls keep freezing — upload speed seems throttled.",
    "Can't reach the database server at 10.0.1.50 from my workstation.",
    "The captive portal for guest Wi-Fi won't load.",
    "I need a static IP assigned for my workstation for the security audit.",
    "Network drive Z: disconnected and won't map again.",
    "My phone can't connect to the corporate Wi-Fi (802.1X issue).",
    "Accessing Office 365 is very slow, but other sites load fine.",
    "My Zoom calls are getting jitter and packet loss warnings.",
    "I need proxy exceptions for our new SaaS tools.",
    "The switch in server room B seems to have a flashing amber light.",
    "I can't access any .gov websites from the office network.",
    "My laptop's Wi-Fi adapter keeps showing 'limited connectivity'.",
    "Remote desktop from home is lagging badly — 2+ second delay.",
    "Need to whitelist our new vendor's IP range in the firewall.",
    "The network is completely down in building 2, 4th floor.",
    "My Docker containers can't reach external APIs — DNS issue?",
    "I'm getting certificate warnings when connecting to the VPN.",
    "The load balancer seems to be routing all traffic to one server.",
    "My Citrix session disconnects after exactly 15 minutes idle.",
    "Need VLAN configuration for the new IoT devices in the warehouse.",
    "My wired connection gets 100Mbps but should be 1Gbps.",
    "Can't access the Git server through the VPN.",
    "The DHCP server seems to be assigning duplicate IPs.",
    "My laptop can ping the gateway but can't reach the internet.",
    "Need to set up site-to-site VPN with our new partner company.",
    "The wireless access point in meeting room 3 seems dead.",
    "My network traffic is being blocked by the content filter incorrectly.",
    "I can't access shared drives after the server migration last night.",
    "DNS entries for our new staging environment haven't propagated.",
    "My connection drops whenever I switch between Wi-Fi and Ethernet.",
    "Need bandwidth increased for the video editing workstation.",
]


@dataclass
class TicketResult:
    ticket_id: int
    category: str  # "password" or "connectivity"
    message: str
    response: str
    delegations: list = field(default_factory=list)
    effective_rpm: Optional[int] = None
    scaling_active: bool = False
    rate_limit_remaining: Optional[int] = None
    status_code: int = 0
    latency_ms: float = 0
    error: Optional[str] = None
    routed_correctly: Optional[bool] = None
    response_quality: Optional[str] = None  # "good", "hallucinated", "empty", "error"


def assess_quality(result: TicketResult) -> None:
    """Assess whether the response is relevant and not hallucinated."""
    resp = result.response.lower()

    if not result.response or len(result.response) < 20:
        result.response_quality = "empty"
        return

    if "error" in resp and ("processing your request" in resp or "unable to respond" in resp):
        result.response_quality = "error"
        return

    # Check for hallucination signals
    hallucination_signals = [
        "as an ai language model",
        "i don't have access to your",
        "i cannot actually",
        "in this hypothetical scenario",
        "let me make up",
        "here's a fictional",
    ]
    for signal in hallucination_signals:
        if signal in resp:
            result.response_quality = "hallucinated"
            return

    # Check routing accuracy
    if result.category == "password":
        password_keywords = ["password", "reset", "mfa", "authenticat", "login", "credential",
                             "lock", "account", "sso", "token", "sign-in", "sign in", "access"]
        if any(kw in resp for kw in password_keywords):
            result.routed_correctly = True
        # Check if it was wrongly routed to connectivity
        connectivity_keywords = ["vpn", "wi-fi", "wifi", "dns", "network", "firewall", "ethernet",
                                 "router", "switch", "bandwidth", "ping", "traceroute"]
        if any(kw in resp for kw in connectivity_keywords) and not any(kw in resp for kw in password_keywords):
            result.routed_correctly = False

    elif result.category == "connectivity":
        connectivity_keywords = ["vpn", "wi-fi", "wifi", "dns", "network", "firewall",
                                 "connection", "disconnect", "router", "switch", "bandwidth",
                                 "ping", "ethernet", "ip", "port", "latency", "timeout"]
        if any(kw in resp for kw in connectivity_keywords):
            result.routed_correctly = True
        password_keywords = ["password", "reset password", "mfa setup", "authenticator app"]
        if any(kw in resp for kw in password_keywords) and not any(kw in resp for kw in connectivity_keywords):
            result.routed_correctly = False

    result.response_quality = "good"


def generate_tickets(n: int) -> list[tuple[int, str, str]]:
    """Generate n tickets with roughly 50/50 split between categories."""
    tickets = []
    for i in range(n):
        if i % 2 == 0:
            category = "password"
            msg = random.choice(PASSWORD_TICKETS)
        else:
            category = "connectivity"
            msg = random.choice(CONNECTIVITY_TICKETS)
        tickets.append((i + 1, category, msg))
    random.shuffle(tickets)
    return tickets


async def main():
    print("=" * 70)
    print("  BULLETPROOF 100-TICKET AGENTIC LOAD TEST")
    print("  HPA Autoscaling Validation")
    print("=" * 70)
    print(f"\n  Triage Router RPM: 10")
    print(f"  Autoscale threshold: 60% (triggers at ~6 RPM)")
    print(f"  Max replicas: 5 (max effective RPM: 50)")
    print(f"  Concurrency: {CONCURRENCY} parallel requests")
    print(f"  Total tickets: 100")
    print(f"  Start time: {datetime.now().isoformat()}")
    print()

    async with httpx.AsyncClient(timeout=120) as client:
        # ─── 1. Login ───
        print("1. Authenticating...")
        resp = await client.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"   FAIL: {resp.text}")
            sys.exit(1)
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   OK\n")

        # ─── 2. Check initial scaling status ───
        print("2. Initial scaling status:")
        resp = await client.get(f"{BASE}/agents/{TRIAGE_ID}/scaling", headers=headers)
        status = resp.json()
        print(f"   base_rpm={status['base_rpm']}")
        print(f"   effective_rpm={status['effective_rpm']}")
        print(f"   scaling_active={status['scaling_active']}")
        print()

        # ─── 3. Generate tickets ───
        tickets = generate_tickets(100)
        results: list[TicketResult] = []
        semaphore = asyncio.Semaphore(CONCURRENCY)

        scaling_transitions = []  # Track when scaling kicks in

        queued_tickets = []  # Track (ticket_id, queue_ticket_id, category, message)
        queue_stats = {"queued": 0, "poll_success": 0, "poll_fail": 0}

        async def process_ticket(ticket_id: int, category: str, message: str) -> TicketResult:
            result = TicketResult(
                ticket_id=ticket_id,
                category=category,
                message=message,
                response="",
            )

            async with semaphore:
                start = time.monotonic()
                try:
                    r = await client.post(
                        f"{BASE}/agents/{TRIAGE_ID}/execute",
                        json={"message": message},
                        headers=headers,
                        timeout=120,
                    )
                    result.latency_ms = (time.monotonic() - start) * 1000
                    result.status_code = r.status_code

                    if r.status_code == 200:
                        data = r.json()
                        result.response = data.get("content", "") or data.get("response", "")
                        result.delegations = data.get("delegations", [])
                        sec = data.get("security", {})
                        result.effective_rpm = sec.get("effective_rpm")
                        result.scaling_active = sec.get("scaling_active", False)
                        result.rate_limit_remaining = sec.get("rate_limit_remaining")
                    elif r.status_code == 202:
                        # Request queued — will poll later
                        data = r.json()
                        qtid = data.get("ticket_id", "")
                        pos = data.get("position", "?")
                        queued_tickets.append((ticket_id, qtid, category, message, result))
                        queue_stats["queued"] += 1
                        result.error = None
                        result.status_code = 202
                        print(
                            f"   #{ticket_id:3d} 📋 [{category:12s}] "
                            f"QUEUED pos={pos} ticket={qtid[:8]}..."
                        )
                        return result
                    elif r.status_code == 429:
                        result.error = "429 Rate Limited"
                        result.response = ""
                    elif r.status_code == 500 and "rate limit" in r.text.lower():
                        result.error = "429 Rate Limited (wrapped)"
                        result.status_code = 429
                        result.response = ""
                    else:
                        result.error = f"{r.status_code}: {r.text[:200]}"
                        result.response = ""

                except Exception as e:
                    result.latency_ms = (time.monotonic() - start) * 1000
                    result.error = str(e)

                assess_quality(result)
                _print_result(result)
                return result

        def _print_result(result: TicketResult):
            status_icon = {
                "good": "✅",
                "empty": "⚠️ ",
                "error": "❌",
                "hallucinated": "🚫",
                None: "❓",
            }.get(result.response_quality, "❓")

            scaling_tag = f" 🔥RPM={result.effective_rpm}" if result.scaling_active else ""
            route_tag = ""
            if result.routed_correctly is True:
                route_tag = " ✅routed"
            elif result.routed_correctly is False:
                route_tag = " ❌misrouted"

            err_tag = f" ERR={result.error}" if result.error else ""

            print(
                f"   #{result.ticket_id:3d} {status_icon} "
                f"[{result.category:12s}] "
                f"{result.latency_ms:6.0f}ms"
                f"{scaling_tag}{route_tag}{err_tag}"
            )

        # ─── 4. Execute load test ───
        print("3. Executing 100 tickets...")
        print(f"   {'─' * 60}")
        test_start = time.monotonic()

        # Process in batches to create realistic load pattern
        tasks = [process_ticket(tid, cat, msg) for tid, cat, msg in tickets]

        # Use gather with semaphore controlling concurrency
        results = await asyncio.gather(*tasks)

        initial_duration = time.monotonic() - test_start
        print(f"   {'─' * 60}")
        print(f"   Initial pass: {initial_duration:.1f}s")
        print(f"   Immediate: {len([r for r in results if r.status_code == 200])}")
        print(f"   Queued:    {queue_stats['queued']}")
        print()

        # ─── 4b. Poll queued tickets ───
        if queued_tickets:
            print(f"4. Polling {len(queued_tickets)} queued tickets...")
            print(f"   {'─' * 60}")
            poll_start = time.monotonic()

            MAX_POLL_WAIT = 300  # 5 min max
            POLL_INTERVAL = 3.0

            for ticket_id, qtid, category, message, result in queued_tickets:
                poll_deadline = time.monotonic() + MAX_POLL_WAIT
                while time.monotonic() < poll_deadline:
                    try:
                        pr = await client.get(
                            f"{BASE}/agents/{TRIAGE_ID}/queue/{qtid}",
                            headers=headers,
                            timeout=30,
                        )
                        if pr.status_code != 200:
                            await asyncio.sleep(POLL_INTERVAL)
                            continue

                        pdata = pr.json()
                        pstatus = pdata.get("status", "")

                        if pstatus == "completed":
                            res = pdata.get("result", {})
                            result.response = res.get("content", "")
                            result.effective_rpm = res.get("effective_rpm")
                            result.scaling_active = res.get("scaling_active", False)
                            result.status_code = 200
                            result.error = None
                            result.latency_ms = (time.monotonic() - poll_start) * 1000
                            assess_quality(result)
                            queue_stats["poll_success"] += 1
                            _print_result(result)
                            break
                        elif pstatus == "failed":
                            result.error = pdata.get("error", "Queue processing failed")
                            result.status_code = 500
                            result.response_quality = "error"
                            queue_stats["poll_fail"] += 1
                            print(f"   #{ticket_id:3d} ❌ [{category:12s}] QUEUE FAILED: {result.error[:80]}")
                            break
                        else:
                            # Still queued/processing
                            await asyncio.sleep(POLL_INTERVAL)

                    except Exception as e:
                        await asyncio.sleep(POLL_INTERVAL)
                else:
                    result.error = "Queue poll timeout (5 min)"
                    result.status_code = 408
                    result.response_quality = "error"
                    queue_stats["poll_fail"] += 1
                    print(f"   #{ticket_id:3d} ⏰ [{category:12s}] POLL TIMEOUT")

            poll_duration = time.monotonic() - poll_start
            print(f"   {'─' * 60}")
            print(f"   Queue drain: {poll_duration:.1f}s")
            print(f"   Resolved: {queue_stats['poll_success']}  Failed: {queue_stats['poll_fail']}")
            print()

        test_duration = time.monotonic() - test_start

        # ─── 5. Analyze Results ───
        print("=" * 70)
        print("  RESULTS SUMMARY")
        print("=" * 70)

        # Status breakdown
        success = [r for r in results if r.status_code == 200]
        rate_limited = [r for r in results if r.status_code == 429]
        errors = [r for r in results if r.error and r.status_code not in (429, 200)]

        print(f"\n  Status:")
        print(f"    Successful:    {len(success):3d} / 100")
        print(f"    Rate Limited:  {len(rate_limited):3d} / 100")
        print(f"    Errors:        {len(errors):3d} / 100")
        if queue_stats["queued"]:
            print(f"    Queued → resolved: {queue_stats['poll_success']}")
            print(f"    Queued → failed:   {queue_stats['poll_fail']}")
        print(f"    Total duration:    {test_duration:.1f}s")

        # Quality breakdown
        good = [r for r in results if r.response_quality == "good"]
        empty = [r for r in results if r.response_quality == "empty"]
        hallucinated = [r for r in results if r.response_quality == "hallucinated"]
        error_resp = [r for r in results if r.response_quality == "error"]

        print(f"\n  Response Quality:")
        print(f"    Good:          {len(good):3d}")
        print(f"    Empty:         {len(empty):3d}")
        print(f"    Hallucinated:  {len(hallucinated):3d}")
        print(f"    Error:         {len(error_resp):3d}")

        # Routing accuracy
        correctly_routed = [r for r in results if r.routed_correctly is True]
        misrouted = [r for r in results if r.routed_correctly is False]
        unclassified = [r for r in results if r.routed_correctly is None and r.response_quality == "good"]

        total_classifiable = len(correctly_routed) + len(misrouted)
        routing_accuracy = (len(correctly_routed) / total_classifiable * 100) if total_classifiable else 0

        print(f"\n  Routing Accuracy:")
        print(f"    Correctly routed: {len(correctly_routed):3d}")
        print(f"    Misrouted:        {len(misrouted):3d}")
        print(f"    Unclassified:     {len(unclassified):3d}")
        print(f"    Accuracy:         {routing_accuracy:.1f}%")

        # Scaling analysis
        scaled_requests = [r for r in results if r.scaling_active]
        unscaled_requests = [r for r in results if not r.scaling_active and r.status_code == 200]

        print(f"\n  Autoscaling:")
        print(f"    Requests with scaling active:   {len(scaled_requests):3d}")
        print(f"    Requests without scaling:       {len(unscaled_requests):3d}")
        if scaled_requests:
            rpms_seen = set(r.effective_rpm for r in scaled_requests if r.effective_rpm)
            print(f"    Effective RPMs observed:        {sorted(rpms_seen)}")

        # Latency stats
        latencies = [r.latency_ms for r in success if r.latency_ms > 0]
        if latencies:
            latencies.sort()
            print(f"\n  Latency (successful requests):")
            print(f"    Min:    {latencies[0]:8.0f} ms")
            print(f"    Median: {latencies[len(latencies)//2]:8.0f} ms")
            print(f"    P95:    {latencies[int(len(latencies)*0.95)]:8.0f} ms")
            print(f"    Max:    {latencies[-1]:8.0f} ms")
            print(f"    Avg:    {sum(latencies)/len(latencies):8.0f} ms")

        # Quality comparison: pre-scale vs post-scale
        if scaled_requests and unscaled_requests:
            pre_good = len([r for r in unscaled_requests if r.response_quality == "good"])
            post_good = len([r for r in scaled_requests if r.response_quality == "good"])
            pre_pct = pre_good / len(unscaled_requests) * 100 if unscaled_requests else 0
            post_pct = post_good / len(scaled_requests) * 100 if scaled_requests else 0

            print(f"\n  Quality: Pre-Scale vs Post-Scale:")
            print(f"    Pre-scale good responses:  {pre_good}/{len(unscaled_requests)} ({pre_pct:.0f}%)")
            print(f"    Post-scale good responses: {post_good}/{len(scaled_requests)} ({post_pct:.0f}%)")
            if post_pct >= pre_pct - 5:
                print(f"    ✅ No quality degradation from autoscaling")
            else:
                print(f"    ⚠️  Quality drop of {pre_pct - post_pct:.0f}% after scaling")

        # ─── 6. Check scaling events ───
        print(f"\n  Scaling Events:")
        resp = await client.get(f"{BASE}/agents/{TRIAGE_ID}/scaling/events", headers=headers)
        events = resp.json()
        events_total = events.get("total", len(events.get("events", [])))
        print(f"    Total events: {events_total}")
        for e in events.get("events", []):
            print(
                f"    [{e['created_at'][11:19]}] {e['event_type']:12s} "
                f"{e['previous_capacity']:3d} → {e['new_capacity']:3d} RPM "
                f"(util={e['trigger_utilization']:.0%})"
            )

        # ─── 7. Final scaling status ───
        print(f"\n  Final Scaling Status:")
        resp = await client.get(f"{BASE}/agents/{TRIAGE_ID}/scaling", headers=headers)
        if resp.status_code == 200:
            fstatus = resp.json()
            print(f"    base_rpm={fstatus.get('base_rpm')}")
            print(f"    effective_rpm={fstatus.get('effective_rpm')}")
            print(f"    scaling_active={fstatus.get('scaling_active')}")
            print(f"    utilization={fstatus.get('utilization')}")
        else:
            print(f"    (could not fetch: {resp.status_code})")

        # ─── 8. Hallucination details ───
        if hallucinated:
            print(f"\n  ⚠️  HALLUCINATED RESPONSES ({len(hallucinated)}):")
            for r in hallucinated:
                print(f"    Ticket #{r.ticket_id}: {r.message[:60]}...")
                print(f"    Response: {r.response[:200]}...")
                print()

        if misrouted:
            print(f"\n  ⚠️  MISROUTED TICKETS ({len(misrouted)}):")
            for r in misrouted:
                print(f"    Ticket #{r.ticket_id} [{r.category}]: {r.message[:60]}...")
                print(f"    Response: {r.response[:200]}...")
                print()

        # ─── 9. Verdict ───
        print("\n" + "=" * 70)
        passed = True
        verdicts = []

        if len(rate_limited) > 60:
            verdicts.append(f"❌ Too many rate limits: {len(rate_limited)}/100 (autoscaling may not be working)")
            passed = False
        elif len(rate_limited) > 20:
            verdicts.append(f"⚠️  Rate limited {len(rate_limited)}/100 (expected — 100 tickets exceeds max 50 RPM)")
        else:
            verdicts.append(f"✅ Rate limiting minimal: {len(rate_limited)}/100")

        if len(hallucinated) > 0:
            verdicts.append(f"❌ Hallucinations detected: {len(hallucinated)}")
            passed = False
        else:
            verdicts.append(f"✅ No hallucinations")

        if routing_accuracy < 85:
            verdicts.append(f"⚠️  Routing accuracy low: {routing_accuracy:.0f}%")
        else:
            verdicts.append(f"✅ Routing accuracy: {routing_accuracy:.0f}%")

        if len(scaled_requests) == 0:
            verdicts.append(f"❌ Autoscaling never triggered")
            passed = False
        else:
            verdicts.append(f"✅ Autoscaling triggered ({len(scaled_requests)} requests served at higher RPM)")

        if events_total == 0:
            verdicts.append(f"❌ No scaling events recorded")
            passed = False
        else:
            verdicts.append(f"✅ {events_total} scaling events recorded")

        if queue_stats["queued"] > 0:
            if queue_stats["poll_fail"] == 0:
                verdicts.append(f"✅ Queue: {queue_stats['queued']} queued, {queue_stats['poll_success']} resolved, 0 lost")
            else:
                verdicts.append(f"⚠️  Queue: {queue_stats['poll_fail']} failed out of {queue_stats['queued']} queued")

        for v in verdicts:
            print(f"  {v}")

        print()
        if passed:
            print("  ✅ HPA LOAD TEST PASSED")
        else:
            print("  ❌ HPA LOAD TEST FAILED")
        print("=" * 70)

        # Write results to JSON for review
        output = {
            "test_time": datetime.now().isoformat(),
            "duration_seconds": round(test_duration, 1),
            "total_tickets": 100,
            "successful": len(success),
            "rate_limited": len(rate_limited),
            "errors": len(errors),
            "quality": {
                "good": len(good),
                "empty": len(empty),
                "hallucinated": len(hallucinated),
                "error": len(error_resp),
            },
            "routing": {
                "correct": len(correctly_routed),
                "misrouted": len(misrouted),
                "accuracy_pct": round(routing_accuracy, 1),
            },
            "scaling": {
                "requests_with_scaling": len(scaled_requests),
                "total_events": events_total,
                "effective_rpms_seen": sorted(set(r.effective_rpm for r in scaled_requests if r.effective_rpm)),
            },
            "latency": {
                "min_ms": round(min(latencies), 0) if latencies else None,
                "median_ms": round(latencies[len(latencies) // 2], 0) if latencies else None,
                "p95_ms": round(latencies[int(len(latencies) * 0.95)], 0) if latencies else None,
                "max_ms": round(max(latencies), 0) if latencies else None,
                "avg_ms": round(sum(latencies) / len(latencies), 0) if latencies else None,
            },
            "queue": {
                "queued": queue_stats["queued"],
                "resolved": queue_stats["poll_success"],
                "failed": queue_stats["poll_fail"],
            },
            "passed": passed,
        }

        with open("backend/tests/hpa_load_test_results.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n  Results saved to backend/tests/hpa_load_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
