#!/usr/bin/env python3
"""
Real Bonobot LOCOMO Benchmark

Tests Bonobot's actual pgvector memory system against LOCOMO QA pairs.
Creates a test agent, feeds conversations, queries with questions, scores answers.

Uses JWT auth + correct API routes for Railway prod.
"""

import json
import time
import sys
import requests
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

API_URL = "https://celebrated-contentment-production-0fc4.up.railway.app"
LOGIN_EMAIL = "cat.shabari@gmail.com"
LOGIN_PASSWORD = "Bonito2026!"
PROJECT_ID = "212a46d8-7ce4-4c66-8ed4-bfa466418fa3"

DATA_FILE = Path(__file__).parent / "locomo10.json"
RESULTS_FILE = Path(__file__).parent / "bonobot_real_results.md"
RESULTS_JSON = Path(__file__).parent / "bonobot_real_results.json"

# Config
SAMPLES_TO_TEST = [0, 1, 2]  # All 3 samples
DELAY_BETWEEN_CALLS = 0.8  # seconds
FUZZY_THRESHOLD = 0.5  # SequenceMatcher ratio threshold


def get_jwt() -> str:
    """Login and return JWT access token."""
    resp = requests.post(f"{API_URL}/api/auth/login", json={
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    })
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token in login response")
    return token


def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_agent(token: str, name: str) -> str:
    """Create a Bonobot agent and return its ID."""
    resp = requests.post(
        f"{API_URL}/api/projects/{PROJECT_ID}/agents",
        headers=get_headers(token),
        json={
            "name": name,
            "description": f"LOCOMO benchmark test agent - {name}",
            "system_prompt": (
                "You are a memory recall assistant. When asked questions about "
                "past conversations, retrieve and provide accurate answers from "
                "your memory. Be concise and factual. If you remember the "
                "information, state it directly."
            ),
            "model": "groq/llama-3.1-8b-instant"
        }
    )
    resp.raise_for_status()
    data = resp.json()
    agent_id = data.get("id") or data.get("agent_id")
    print(f"  Created agent: {agent_id}")
    return agent_id


def delete_agent(token: str, agent_id: str):
    """Clean up test agent."""
    try:
        requests.delete(
            f"{API_URL}/api/agents/{agent_id}",
            headers=get_headers(token)
        )
    except Exception:
        pass


def send_message(token: str, agent_id: str, message: str, session_id: str = None) -> tuple:
    """Send a message to agent via /execute and get response.
    Returns (response_text, session_id)."""
    body = {"message": message}
    if session_id:
        body["session_id"] = session_id
    resp = requests.post(
        f"{API_URL}/api/agents/{agent_id}/execute",
        headers=get_headers(token),
        json=body,
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    text = data.get("content", data.get("response", data.get("message", str(data))))
    sid = data.get("session_id", session_id)
    return text, sid


def feed_conversations(token: str, agent_id: str, conversation: dict) -> str:
    """Feed LOCOMO conversation sessions into the agent's memory.
    Returns the session_id used."""
    speaker_a = conversation.get("speaker_a", "Speaker A")
    speaker_b = conversation.get("speaker_b", "Speaker B")

    session_keys = sorted([
        k for k in conversation.keys()
        if k.startswith("session_") and "date" not in k
    ], key=lambda x: int(x.split("_")[1]))

    print(f"  Feeding {len(session_keys)} conversation sessions...")

    session_id = None

    for i, session_key in enumerate(session_keys):
        session = conversation[session_key]
        if not isinstance(session, list):
            continue

        date_key = f"{session_key}_date_time"
        date_str = conversation.get(date_key, f"Session {i+1}")

        lines = [f"[Conversation on {date_str}]"]
        for turn in session:
            speaker = turn.get("speaker", "Unknown")
            text = turn.get("text", "")
            lines.append(f"{speaker}: {text}")

        msg = "\n".join(lines)

        try:
            _, session_id = send_message(
                token, agent_id,
                f"Please remember this conversation:\n\n{msg}",
                session_id
            )
            time.sleep(DELAY_BETWEEN_CALLS)
        except Exception as e:
            print(f"    Warning: Failed to send {session_key}: {e}")
            continue

        if (i + 1) % 5 == 0:
            print(f"    Fed {i+1}/{len(session_keys)} sessions")

    print(f"  Done feeding {len(session_keys)} sessions")
    return session_id


def check_answer(ground_truth: str, response: str) -> tuple:
    """Check if the response contains the ground truth answer.
    Returns (is_correct, match_type)."""
    gt_lower = str(ground_truth).lower().strip()
    resp_lower = str(response).lower().strip()

    if gt_lower in resp_lower:
        return True, "substring"

    gt_parts = [p.strip() for p in gt_lower.split(",")]
    parts_found = sum(1 for p in gt_parts if p in resp_lower)
    if parts_found > 0 and parts_found >= len(gt_parts) * 0.5:
        return True, "partial"

    ratio = SequenceMatcher(None, gt_lower, resp_lower).ratio()
    if ratio >= FUZZY_THRESHOLD:
        return True, f"fuzzy({ratio:.2f})"

    gt_words = set(gt_lower.split())
    resp_words = set(resp_lower.split())
    if len(gt_words) <= 3:
        overlap = gt_words & resp_words
        if len(overlap) >= len(gt_words) * 0.7:
            return True, "word_overlap"

    return False, "no_match"


def run_benchmark():
    """Run the full benchmark."""
    print("=" * 60)
    print("BONOBOT LOCOMO BENCHMARK (REAL API)")
    print("=" * 60)

    # Auth
    print("Authenticating...")
    token = get_jwt()
    print("  OK")

    # Load data
    with open(DATA_FILE) as f:
        data = json.load(f)

    all_results = []
    category_stats = {}
    sample_stats = {}
    total_correct = 0
    total_questions = 0
    total_response_time = 0
    sample_details = []

    for sample_idx in SAMPLES_TO_TEST:
        sample = data[sample_idx]
        conv = sample["conversation"]
        qa_list = sample["qa"]
        speaker_a = conv.get("speaker_a", "A")
        speaker_b = conv.get("speaker_b", "B")

        print(f"\n{'='*50}")
        print(f"Sample {sample_idx}: {speaker_a} & {speaker_b} ({len(qa_list)} questions)")
        print(f"{'='*50}")

        agent_name = f"locomo-bench-s{sample_idx}-{int(time.time())}"
        try:
            agent_id = create_agent(token, agent_name)
        except Exception as e:
            print(f"  ERROR creating agent: {e}")
            continue

        try:
            session_id = feed_conversations(token, agent_id, conv)
            print(f"\n  Querying {len(qa_list)} questions...")

            sample_correct = 0
            sample_results = []

            for q_idx, qa in enumerate(qa_list):
                question = qa["question"]
                ground_truth = qa.get("answer") or qa.get("adversarial_answer", "unknown")
                category = qa.get("category", 0)

                start_time = time.time()
                try:
                    response, session_id = send_message(
                        token, agent_id, question, session_id
                    )
                    elapsed = time.time() - start_time
                except Exception as e:
                    response = f"ERROR: {e}"
                    elapsed = 0

                total_response_time += elapsed
                time.sleep(DELAY_BETWEEN_CALLS)

                is_correct, match_type = check_answer(ground_truth, response)
                if is_correct:
                    sample_correct += 1
                    total_correct += 1

                total_questions += 1

                if category not in category_stats:
                    category_stats[category] = {"correct": 0, "total": 0}
                category_stats[category]["total"] += 1
                if is_correct:
                    category_stats[category]["correct"] += 1

                result = {
                    "sample": sample_idx,
                    "question_idx": q_idx,
                    "category": category,
                    "question": question,
                    "ground_truth": ground_truth,
                    "response": response[:500],
                    "correct": is_correct,
                    "match_type": match_type,
                    "response_time": elapsed,
                }
                sample_results.append(result)
                all_results.append(result)

                if (q_idx + 1) % 10 == 0:
                    acc = sample_correct / (q_idx + 1) * 100
                    print(f"    [{q_idx+1}/{len(qa_list)}] Running accuracy: {acc:.1f}%")

            sample_acc = sample_correct / len(qa_list) * 100 if qa_list else 0
            sample_stats[sample_idx] = {
                "correct": sample_correct,
                "total": len(qa_list),
                "accuracy": sample_acc
            }
            sample_details.append({
                "idx": sample_idx,
                "speakers": f"{speaker_a} & {speaker_b}",
                "results": sample_results[:10]
            })

            print(f"\n  Sample {sample_idx} accuracy: {sample_correct}/{len(qa_list)} = {sample_acc:.1f}%")

        finally:
            delete_agent(token, agent_id)
            print(f"  Agent cleaned up")

    # Final report
    overall_acc = total_correct / total_questions * 100 if total_questions else 0
    avg_time = total_response_time / total_questions if total_questions else 0

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Overall: {total_correct}/{total_questions} = {overall_acc:.1f}%")
    print(f"Avg response time: {avg_time:.2f}s")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        print(f"  Cat {cat}: {s['correct']}/{s['total']} = {s['correct']/s['total']*100:.1f}%")

    # Write results
    cat_names = {1: "single-hop", 2: "multi-hop", 3: "temporal", 4: "open-domain", 5: "adversarial"}

    with open(RESULTS_FILE, "w") as f:
        f.write(f"# Bonobot LOCOMO Benchmark (Real pgvector)\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Samples Tested | {SAMPLES_TO_TEST} |\n")
        f.write(f"| Total Questions | {total_questions} |\n")
        f.write(f"| Correct Answers | {total_correct} |\n")
        f.write(f"| **Overall Accuracy** | **{overall_acc:.1f}%** |\n")
        f.write(f"| Average Response Time | {avg_time:.2f}s |\n")
        f.write(f"| Model | groq/llama-3.1-8b-instant |\n")
        f.write(f"| Memory | pgvector (Google text-embedding-005, 768d) |\n\n")

        f.write(f"## Accuracy by Category\n\n")
        f.write(f"| Category | Correct | Total | Accuracy |\n")
        f.write(f"|----------|---------|-------|----------|\n")
        for cat in sorted(category_stats.keys()):
            s = category_stats[cat]
            name = cat_names.get(cat, f"unknown-{cat}")
            acc = s['correct']/s['total']*100 if s['total'] else 0
            f.write(f"| {cat} ({name}) | {s['correct']} | {s['total']} | {acc:.1f}% |\n")

        f.write(f"\n## Per-Sample Breakdown\n\n")
        f.write(f"| Sample | Correct | Total | Accuracy |\n")
        f.write(f"|--------|---------|-------|----------|\n")
        for idx in sorted(sample_stats.keys()):
            s = sample_stats[idx]
            f.write(f"| {idx} | {s['correct']} | {s['total']} | {s['accuracy']:.1f}% |\n")

        f.write(f"\n## Sample Results (first 10 per sample)\n\n")
        for sd in sample_details:
            f.write(f"### Sample {sd['idx']} ({sd['speakers']})\n\n")
            for r in sd["results"]:
                status = "CORRECT" if r["correct"] else "WRONG"
                f.write(f"**Q{r['question_idx']} (Cat {r['category']}):** {status}\n")
                f.write(f"- Question: {r['question']}\n")
                f.write(f"- Ground Truth: {r['ground_truth']}\n")
                f.write(f"- Response: {r['response'][:200]}...\n")
                f.write(f"- Match: {r['match_type']} | Time: {r['response_time']:.2f}s\n\n")

        f.write(f"\n## Failure Analysis\n\n")
        failures = [r for r in all_results if not r["correct"]]
        if failures:
            cat_failures = {}
            for r in failures:
                cat = r["category"]
                if cat not in cat_failures:
                    cat_failures[cat] = []
                cat_failures[cat].append(r)
            for cat in sorted(cat_failures.keys()):
                name = cat_names.get(cat, f"unknown-{cat}")
                f.write(f"### Category {cat} ({name}): {len(cat_failures[cat])} failures\n\n")
                for r in cat_failures[cat][:3]:
                    f.write(f"- Q: {r['question']}\n")
                    f.write(f"  Expected: {r['ground_truth']}\n")
                    f.write(f"  Got: {r['response'][:150]}...\n\n")
        else:
            f.write("No failures.\n")

    with open(RESULTS_JSON, "w") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "overall_accuracy": overall_acc,
            "total_correct": total_correct,
            "total_questions": total_questions,
            "avg_response_time": avg_time,
            "category_stats": category_stats,
            "sample_stats": {str(k): v for k, v in sample_stats.items()},
            "results": all_results,
        }, f, indent=2)

    print(f"\nResults written to {RESULTS_FILE}")
    print(f"JSON written to {RESULTS_JSON}")


if __name__ == "__main__":
    run_benchmark()
