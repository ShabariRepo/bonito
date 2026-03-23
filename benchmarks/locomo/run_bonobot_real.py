#!/usr/bin/env python3
"""
Bonobot LOCOMO Benchmark - Real API
Runs against the actual Bonito API to test pgvector memory retrieval.
"""

import json
import time
import requests
import sys
from datetime import datetime
from thefuzz import fuzz
from collections import defaultdict

# ============================================================================
# Config - Railway direct (api.getbonito.com has DNS issues, custom domain lost)
# ============================================================================
API_BASE = "https://celebrated-contentment-production-0fc4.up.railway.app"
LOGIN_EMAIL = "cat.shabari@gmail.com"
LOGIN_PASSWORD = "Bonito2026!"
MODEL = "groq/llama-3.1-8b-instant"  # Fast + cheap for benchmark volume
RATE_LIMIT_DELAY = 1.0  # seconds between API calls

# Will be populated after login
HEADERS = {
    "Content-Type": "application/json",
}


def login():
    """Authenticate and set Bearer token."""
    r = requests.post(f"{API_BASE}/api/auth/login", json={
        "email": LOGIN_EMAIL, "password": LOGIN_PASSWORD
    }, timeout=15)
    r.raise_for_status()
    token = r.json()["access_token"]
    HEADERS["Authorization"] = f"Bearer {token}"
    print(f"Authenticated as {LOGIN_EMAIL}")

CATEGORY_NAMES = {
    1: "single-hop",
    2: "multi-hop",
    3: "temporal",
    4: "open-domain",
    5: "adversarial",
}

# ============================================================================
# API Client
# ============================================================================

def health_check():
    """Verify API is reachable."""
    r = requests.get(f"{API_BASE}/api/health", timeout=10)
    print(f"Health: {r.status_code} {r.json()}")
    return r.status_code == 200


def get_project_id():
    """Get or create a project for the benchmark."""
    # List existing projects
    r = requests.get(f"{API_BASE}/api/projects", headers=HEADERS, timeout=15)
    if r.status_code == 200:
        projects = r.json()
        if isinstance(projects, list) and len(projects) > 0:
            return projects[0]["id"]
        elif isinstance(projects, dict) and projects.get("items"):
            return projects["items"][0]["id"]
    
    # If no project, create one
    payload = {"name": "LOCOMO Benchmark", "description": "Memory benchmark testing"}
    r = requests.post(f"{API_BASE}/api/projects", headers=HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("id") or data.get("data", {}).get("id")


def create_agent(name, project_id):
    """Create a Bonobot agent for this benchmark sample."""
    payload = {
        "name": name,
        "system_prompt": (
            "You are a memory recall assistant. You have had previous conversations with users. "
            "When asked questions about those conversations, answer based on what you remember. "
            "Be concise and direct. If you do not remember, say so honestly."
        ),
        "model_id": MODEL,
        "max_turns": 1,
        "compaction_enabled": False,  # Don't compact - we want full memory
        "max_session_messages": 1000,
    }
    r = requests.post(
        f"{API_BASE}/api/projects/{project_id}/agents",
        headers=HEADERS, json=payload, timeout=15
    )
    r.raise_for_status()
    return r.json()["id"]


def delete_agent(agent_id):
    """Clean up benchmark agent."""
    try:
        requests.delete(f"{API_BASE}/api/agents/{agent_id}", headers=HEADERS, timeout=10)
    except Exception:
        pass


def send_message(agent_id, message, session_id=None, timeout=60):
    """Send a message to the agent and get response."""
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    r = requests.post(
        f"{API_BASE}/api/agents/{agent_id}/execute",
        headers=HEADERS, json=payload, timeout=timeout
    )
    r.raise_for_status()
    return r.json()


def get_sessions(agent_id):
    """List sessions for an agent."""
    r = requests.get(
        f"{API_BASE}/api/agents/{agent_id}/sessions",
        headers=HEADERS, timeout=15
    )
    r.raise_for_status()
    return r.json()


def extract_memories(agent_id, session_id):
    """Explicitly extract memories from a session into pgvector."""
    r = requests.post(
        f"{API_BASE}/api/agents/{agent_id}/sessions/{session_id}/extract-memories",
        headers=HEADERS, timeout=120  # Memory extraction can be slow
    )
    r.raise_for_status()
    return r.json()


def get_memory_stats(agent_id):
    """Check how many memories the agent has."""
    r = requests.get(
        f"{API_BASE}/api/agents/{agent_id}/memories/stats",
        headers=HEADERS, timeout=15
    )
    r.raise_for_status()
    return r.json()


def check_answer(agent_response, ground_truth):
    """Score the agent's answer against ground truth."""
    if not agent_response or not ground_truth:
        return False, "empty"
    
    resp_lower = agent_response.lower().strip()
    truth_lower = str(ground_truth).lower().strip()
    
    # Direct substring match
    if truth_lower in resp_lower or resp_lower in truth_lower:
        return True, "substring"
    
    # Fuzzy matching
    ratio = fuzz.ratio(resp_lower, truth_lower)
    partial = fuzz.partial_ratio(resp_lower, truth_lower)
    token_sort = fuzz.token_sort_ratio(resp_lower, truth_lower)
    
    if ratio > 80 or partial > 85 or token_sort > 80:
        return True, f"fuzzy(r={ratio},pr={partial},ts={token_sort})"
    
    return False, f"fuzzy(r={ratio},pr={partial},ts={token_sort})"


# ============================================================================
# Benchmark Runner
# ============================================================================

def feed_conversations(agent_id, conversation):
    """Feed all conversation sessions to the agent, then extract memories."""
    sessions = []
    for key in sorted(conversation.keys()):
        if key.startswith("session_") and not key.endswith("_date_time"):
            session_num = int(key.replace("session_", ""))
            date_key = f"{key}_date_time"
            session_date = conversation.get(date_key, f"Session {session_num}")
            if conversation[key]:
                sessions.append((session_num, session_date, conversation[key]))
    
    print(f"  Feeding {len(sessions)} conversation sessions...")
    
    # First message creates a session; reuse session_id for all subsequent
    feed_session_id = None
    fed = 0
    
    for session_num, session_date, session_data in sessions:
        lines = [f"[Conversation from {session_date}]"]
        for entry in session_data:
            lines.append(f"{entry['speaker']}: {entry['text']}")
        
        text = "\n".join(lines)
        
        # Feed in chunks if too long
        if len(text) > 4000:
            chunks = []
            current = []
            current_len = 0
            for line in lines:
                if current_len + len(line) > 3500 and current:
                    chunks.append("\n".join(current))
                    current = [f"[Conversation from {session_date}, continued]"]
                    current_len = len(current[0])
                current.append(line)
                current_len += len(line)
            if current:
                chunks.append("\n".join(current))
            
            for chunk in chunks:
                try:
                    resp = send_message(agent_id, chunk, session_id=feed_session_id, timeout=90)
                    if not feed_session_id:
                        feed_session_id = resp.get("session_id")
                    fed += 1
                    time.sleep(RATE_LIMIT_DELAY)
                except Exception as e:
                    print(f"    ERROR feeding session {session_num} chunk: {e}")
        else:
            try:
                resp = send_message(agent_id, text, session_id=feed_session_id, timeout=90)
                if not feed_session_id:
                    feed_session_id = resp.get("session_id")
                fed += 1
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                print(f"    ERROR feeding session {session_num}: {e}")
    
    print(f"  Fed {fed} message batches (session: {feed_session_id})")
    
    # Extract memories from the feeding session
    if feed_session_id:
        print(f"  Extracting memories from session...")
        try:
            mem_result = extract_memories(agent_id, feed_session_id)
            print(f"  Memory extraction result: {json.dumps(mem_result)[:200]}")
        except Exception as e:
            print(f"  Memory extraction error: {e}")
            # Try to get session ID from listing if extract failed
    
    # Check memory stats
    try:
        stats = get_memory_stats(agent_id)
        print(f"  Memory stats: {json.dumps(stats)[:200]}")
    except Exception as e:
        print(f"  Could not get memory stats: {e}")
    
    return fed, feed_session_id


def run_benchmark(sample_indices=None, max_questions=None):
    """Run the full benchmark."""
    # Load data
    with open("locomo10.json") as f:
        data = json.load(f)
    
    if sample_indices is None:
        sample_indices = [0, 1, 2]  # Default: 3 samples
    
    # Verify API
    print("Checking API health...")
    if not health_check():
        print("API is not healthy. Aborting.")
        return None
    
    # Login
    print("Authenticating...")
    login()
    
    # Get project
    print("Getting project...")
    project_id = get_project_id()
    print(f"Project: {project_id}")
    
    all_results = []
    category_stats = {i: {"correct": 0, "total": 0} for i in range(1, 6)}
    total_correct = 0
    total_questions = 0
    total_response_time = 0
    errors = 0
    
    for sample_idx in sample_indices:
        sample = data[sample_idx]
        sample_id = sample.get("sample_id", sample_idx)
        qa_list = sample["qa"]
        conversation = sample["conversation"]
        
        if max_questions:
            qa_list = qa_list[:max_questions]
        
        print(f"\n{'='*60}")
        print(f"Sample {sample_idx} (ID: {sample_id}) - {len(qa_list)} questions")
        print(f"{'='*60}")
        
        # Create agent
        agent_name = f"locomo-bench-{sample_idx}-{int(time.time())}"
        print(f"Creating agent: {agent_name}")
        try:
            agent_id = create_agent(agent_name, project_id)
            print(f"Agent: {agent_id}")
        except Exception as e:
            print(f"ERROR creating agent: {e}")
            continue
        
        try:
            # Phase 1: Feed conversations and extract memories
            fed_count, feed_session_id = feed_conversations(agent_id, conversation)
            print("  Conversations fed and memories extracted. Starting QA...")
            
            # Delay to let memory indexing settle (pgvector embedding)
            time.sleep(3)
            
            # Phase 2: Query
            sample_correct = 0
            for i, qa in enumerate(qa_list):
                question = qa["question"]
                answer = qa.get("answer") or qa.get("adversarial_answer", "")
                category = qa.get("category", 1)
                
                start = time.time()
                try:
                    resp = send_message(agent_id, question, timeout=60)
                    elapsed = time.time() - start
                    agent_response = resp.get("content", "") or resp.get("response", "") or str(resp)
                except Exception as e:
                    elapsed = time.time() - start
                    agent_response = f"ERROR: {e}"
                    errors += 1
                
                total_response_time += elapsed
                
                is_correct, match_type = check_answer(agent_response, answer)
                if is_correct:
                    sample_correct += 1
                    total_correct += 1
                
                total_questions += 1
                category_stats[category]["total"] += 1
                if is_correct:
                    category_stats[category]["correct"] += 1
                
                result = {
                    "sample_idx": sample_idx,
                    "q_idx": i,
                    "question": question,
                    "ground_truth": answer,
                    "agent_response": agent_response[:500],
                    "correct": is_correct,
                    "match_type": match_type,
                    "category": category,
                    "response_time": round(elapsed, 2),
                }
                all_results.append(result)
                
                if (i + 1) % 10 == 0:
                    acc = sample_correct / (i + 1) * 100
                    print(f"    Q{i+1}/{len(qa_list)} | Acc: {acc:.1f}% | Last: {elapsed:.1f}s | {'CORRECT' if is_correct else 'WRONG'}")
                
                time.sleep(RATE_LIMIT_DELAY)
            
            sample_acc = sample_correct / len(qa_list) * 100 if qa_list else 0
            print(f"  Sample {sample_idx}: {sample_correct}/{len(qa_list)} ({sample_acc:.1f}%)")
            
        finally:
            print(f"  Cleaning up agent {agent_id}...")
            delete_agent(agent_id)
            time.sleep(RATE_LIMIT_DELAY)
    
    # Compile report
    overall_acc = total_correct / total_questions * 100 if total_questions > 0 else 0
    avg_time = total_response_time / total_questions if total_questions > 0 else 0
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "model": MODEL,
        "samples_tested": sample_indices,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "overall_accuracy": round(overall_acc, 1),
        "avg_response_time": round(avg_time, 2),
        "errors": errors,
        "category_breakdown": {},
        "results": all_results,
    }
    
    print(f"\n{'='*60}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*60}")
    print(f"Accuracy: {overall_acc:.1f}% ({total_correct}/{total_questions})")
    print(f"Avg response time: {avg_time:.2f}s")
    print(f"Errors: {errors}")
    print(f"\nBy category:")
    
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        if s["total"] > 0:
            acc = s["correct"] / s["total"] * 100
            name = CATEGORY_NAMES.get(cat, f"cat-{cat}")
            print(f"  {cat} ({name}): {acc:.1f}% ({s['correct']}/{s['total']})")
            report["category_breakdown"][cat] = {
                "name": name,
                "correct": s["correct"],
                "total": s["total"],
                "accuracy": round(acc, 1),
            }
    
    # Save
    with open("bonobot_real_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Markdown report
    md = f"""# Bonobot LOCOMO Benchmark (Real API)

**Date:** {report['timestamp']}
**API:** {API_BASE}
**Model:** {MODEL}

## Summary

| Metric | Value |
|--------|-------|
| Samples | {sample_indices} |
| Questions | {total_questions} |
| Correct | {total_correct} |
| **Accuracy** | **{overall_acc:.1f}%** |
| Avg Response Time | {avg_time:.2f}s |
| Errors | {errors} |

## By Category

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
"""
    for cat in sorted(report["category_breakdown"].keys()):
        s = report["category_breakdown"][cat]
        md += f"| {cat} ({s['name']}) | {s['correct']} | {s['total']} | {s['accuracy']}% |\n"
    
    md += "\n## Sample Results (first 20)\n\n"
    for r in all_results[:20]:
        icon = "OK" if r["correct"] else "MISS"
        md += f"**[{icon}] S{r['sample_idx']} Q{r['q_idx']} (cat {r['category']}, {r['response_time']}s)**\n"
        md += f"- Q: {r['question']}\n"
        md += f"- Truth: {r['ground_truth']}\n"
        md += f"- Agent: {r['agent_response'][:200]}\n"
        md += f"- Match: {r['match_type']}\n\n"
    
    with open("bonobot_real_results.md", "w") as f:
        f.write(md)
    
    print(f"\nSaved: bonobot_real_results.json, bonobot_real_results.md")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, nargs="+", default=[0], help="Sample indices to test")
    parser.add_argument("--max-q", type=int, default=None, help="Max questions per sample")
    parser.add_argument("--check", action="store_true", help="Health check only")
    args = parser.parse_args()
    
    if args.check:
        health_check()
        sys.exit(0)
    
    run_benchmark(sample_indices=args.samples, max_questions=args.max_q)
