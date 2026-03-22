#!/usr/bin/env python3
"""
Bonobot LOCOMO Benchmark
Tests Bonobot's pgvector memory system against the LOCOMO dataset.

NOTE: This benchmark requires either:
1. Production API (https://api.getbonito.com) to be available, OR
2. Local backend with configured LLM deployments

Current status as of 2026-03-22:
- Production API returning 502 Bad Gateway
- Local backend running but missing LiteLLM model deployments
"""

import json
import time
import requests
from thefuzz import fuzz
from datetime import datetime
import os
import sys

# ============================================================================
# Configuration - MODIFY THESE BASED ON YOUR ENVIRONMENT
# ============================================================================

# Option 1: Production API (when available)
# API_BASE = "https://api.getbonito.com"
# JWT_SECRET = None  # Use actual API key

# Option 2: Local Development API
API_BASE = "http://localhost:8001"
JWT_SECRET = "dev-secret-change-in-production"
JWT_ALGORITHM = "HS256"
TEST_USER_ID = "543f4d9b-6a62-42de-970a-73d0808ac668"
TEST_ORG_ID = "9c57acbc-3249-4d3a-9267-a1fee4449843"

MODEL = "groq/llama-3.1-8b-instant"
RATE_LIMIT_DELAY = 0.5

# ============================================================================
# Authentication
# ============================================================================

def get_auth_token():
    """Generate a valid JWT for local testing."""
    if JWT_SECRET is None:
        # Production mode - use API key
        return "bn-2e01eec735aa106c01f70c702d18bf4d42e521b73725e63cc8ef421c67e95257"
    
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    payload = {
        "sub": TEST_USER_ID,
        "org_id": TEST_ORG_ID,
        "role": "admin",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def api_headers():
    if JWT_SECRET is None:
        return {"X-API-Key": get_auth_token(), "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {get_auth_token()}", "Content-Type": "application/json"}


# ============================================================================
# API Client Functions
# ============================================================================

def get_or_create_project():
    """Get first available project or create one."""
    url = f"{API_BASE}/api/projects"
    resp = requests.get(url, headers=api_headers())
    if resp.status_code == 200:
        data = resp.json()
        if data and len(data) > 0:
            return data[0]["id"]
    
    # Create a project
    payload = {"name": "LOCOMO Benchmark", "description": "Benchmark project", "org_id": TEST_ORG_ID}
    resp = requests.post(url, headers=api_headers(), json=payload)
    resp.raise_for_status()
    result = resp.json()
    return result.get("id") or result.get("data", {}).get("id")


def create_agent(name, project_id):
    """Create a new Bonobot agent for testing."""
    url = f"{API_BASE}/api/projects/{project_id}/agents"
    payload = {
        "name": name,
        "description": "LOCOMO benchmark test agent",
        "system_prompt": "You are a conversational memory test agent. Answer questions based on your memory of previous conversations. Be concise and direct.",
        "model_id": MODEL
    }
    resp = requests.post(url, headers=api_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def delete_agent(agent_id):
    """Delete the test agent."""
    url = f"{API_BASE}/api/agents/{agent_id}"
    requests.delete(url, headers=api_headers())


def send_message(agent_id, message):
    """Send a message to the agent."""
    url = f"{API_BASE}/api/agents/{agent_id}/execute"
    payload = {"message": message}
    resp = requests.post(url, headers=api_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


# ============================================================================
# Data Processing
# ============================================================================

def format_session(session_num, session_data, session_date):
    """Format a conversation session for the agent."""
    lines = [f"Session {session_num} on {session_date}:"]
    for entry in session_data:
        lines.append(f"{entry['speaker']}: {entry['text']}")
    return "\n".join(lines)


def feed_conversations(agent_id, conversation):
    """Feed all conversation sessions to the agent."""
    sessions = []
    for key in conversation.keys():
        if key.startswith('session_') and not key.endswith('_date_time'):
            session_num = int(key.replace('session_', ''))
            date_key = f"{key}_date_time"
            session_date = conversation.get(date_key, f"Session {session_num}")
            if conversation[key]:  # Only add non-empty sessions
                sessions.append((session_num, session_date, conversation[key]))
    
    sessions.sort(key=lambda x: x[0])
    
    print(f"  Feeding {len(sessions)} sessions...")
    for session_num, session_date, session_data in sessions:
        formatted = format_session(session_num, session_data, session_date)
        send_message(agent_id, formatted)
        time.sleep(RATE_LIMIT_DELAY)


def check_answer(agent_response, ground_truth):
    """Check if the agent's answer matches the ground truth."""
    agent_lower = agent_response.lower()
    truth_lower = str(ground_truth).lower()
    
    # Direct substring match
    if truth_lower in agent_lower or agent_lower in truth_lower:
        return True, "substring"
    
    # Fuzzy match
    ratio = fuzz.ratio(agent_lower, truth_lower)
    partial_ratio = fuzz.partial_ratio(agent_lower, truth_lower)
    token_sort = fuzz.token_sort_ratio(agent_lower, truth_lower)
    
    # Consider correct if any fuzzy score is high
    if ratio > 80 or partial_ratio > 85 or token_sort > 80:
        return True, f"fuzzy(r={ratio},pr={partial_ratio},ts={token_sort})"
    
    return False, f"fuzzy(r={ratio},pr={partial_ratio},ts={token_sort})"


# ============================================================================
# Benchmark Runner
# ============================================================================

def run_benchmark(samples_to_test=None, skip_llm=False):
    """Run the benchmark on specified samples.
    
    Args:
        samples_to_test: List of sample indices to test (default: [0, 1, 2])
        skip_llm: If True, skip actual LLM calls and simulate responses for testing
    """
    # Load dataset
    with open('locomo10.json') as f:
        data = json.load(f)
    
    if samples_to_test is None:
        samples_to_test = [0, 1, 2]  # Default to first 3 samples
    
    # Get project for agent creation
    print("Getting project...")
    try:
        project_id = get_or_create_project()
        print(f"Using project: {project_id}")
    except Exception as e:
        print(f"ERROR: Could not get/create project: {e}")
        print("Make sure the API is running and accessible.")
        return None
    
    all_results = []
    category_stats = {1: {'correct': 0, 'total': 0},
                      2: {'correct': 0, 'total': 0},
                      3: {'correct': 0, 'total': 0},
                      4: {'correct': 0, 'total': 0},
                      5: {'correct': 0, 'total': 0}}
    
    total_correct = 0
    total_questions = 0
    total_time = 0
    
    for sample_idx in samples_to_test:
        sample = data[sample_idx]
        sample_id = sample.get('sample_id', sample_idx)
        qa_list = sample['qa']
        conversation = sample['conversation']
        
        print(f"\n{'='*60}")
        print(f"Sample {sample_idx} (ID: {sample_id}) - {len(qa_list)} questions")
        print(f"{'='*60}")
        
        # Create agent for this sample
        agent_name = f"locomo-benchmark-sample-{sample_idx}-{int(time.time())}"
        print(f"Creating agent: {agent_name}")
        try:
            agent_id = create_agent(agent_name, project_id)
            print(f"Agent ID: {agent_id}")
        except Exception as e:
            print(f"ERROR creating agent: {e}")
            if skip_llm:
                print("Skipping sample (skip_llm=False would be needed for real testing)")
                continue
            raise
        
        try:
            # Phase 1: Feed conversations
            if not skip_llm:
                feed_conversations(agent_id, conversation)
                print(f"  Done feeding conversations. Starting QA...")
            else:
                print("  [SIMULATION] Skipping conversation feeding (skip_llm=True)")
            
            # Phase 2: Query and score
            sample_correct = 0
            
            for i, qa in enumerate(qa_list):
                question = qa['question']
                # Handle adversarial questions which have 'adversarial_answer' instead of 'answer'
                answer = qa.get('answer') or qa.get('adversarial_answer', '')
                category = qa.get('category', 1)
                
                if skip_llm:
                    # Simulate response for testing infrastructure
                    agent_response = f"[SIMULATED] The answer is {answer}"
                    elapsed = 0.1
                else:
                    # Query agent
                    start_time = time.time()
                    try:
                        response_data = send_message(agent_id, question)
                        elapsed = time.time() - start_time
                        total_time += elapsed
                        agent_response = response_data.get('content', '')
                    except Exception as e:
                        print(f"  ERROR on Q{i}: {e}")
                        agent_response = f"ERROR: {e}"
                        elapsed = 0
                
                # Check answer
                is_correct, match_type = check_answer(agent_response, answer)
                
                if is_correct:
                    sample_correct += 1
                    total_correct += 1
                
                total_questions += 1
                category_stats[category]['total'] += 1
                if is_correct:
                    category_stats[category]['correct'] += 1
                
                result = {
                    'sample_idx': sample_idx,
                    'question_idx': i,
                    'question': question,
                    'ground_truth': answer,
                    'agent_response': agent_response,
                    'correct': is_correct,
                    'match_type': match_type,
                    'category': category,
                    'response_time': elapsed
                }
                all_results.append(result)
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i+1}/{len(qa_list)} - Current accuracy: {sample_correct/(i+1)*100:.1f}%")
                
                if not skip_llm:
                    time.sleep(RATE_LIMIT_DELAY)
            
            sample_accuracy = sample_correct / len(qa_list) * 100
            print(f"  Sample {sample_idx} complete: {sample_correct}/{len(qa_list)} correct ({sample_accuracy:.1f}%)")
            
        finally:
            # Cleanup
            if not skip_llm:
                delete_agent(agent_id)
                time.sleep(RATE_LIMIT_DELAY)
    
    # Calculate final stats
    overall_accuracy = total_correct / total_questions * 100 if total_questions > 0 else 0
    avg_response_time = total_time / total_questions if total_questions > 0 else 0
    
    return {
        'timestamp': datetime.now().isoformat(),
        'samples_tested': samples_to_test,
        'total_questions': total_questions,
        'total_correct': total_correct,
        'overall_accuracy': overall_accuracy,
        'avg_response_time': avg_response_time,
        'category_breakdown': {
            cat: {
                'correct': stats['correct'],
                'total': stats['total'],
                'accuracy': stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
            }
            for cat, stats in category_stats.items() if stats['total'] > 0
        },
        'category_names': {
            1: 'single-hop',
            2: 'multi-hop', 
            3: 'temporal',
            4: 'open-domain',
            5: 'adversarial'
        },
        'results': all_results
    }


# ============================================================================
# Results Reporting
# ============================================================================

def save_results(report, output_file='bonobot_results.json', md_file='bonobot_results.md'):
    """Save results to JSON and Markdown."""
    if report is None:
        print("No report to save.")
        return
    
    # Save full JSON
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    # Generate markdown report
    cat_names = report['category_names']
    
    md = f"""# Bonobot LOCOMO Benchmark Results

**Date:** {report['timestamp']}

## Summary

| Metric | Value |
|--------|-------|
| Samples Tested | {report['samples_tested']} |
| Total Questions | {report['total_questions']} |
| Correct Answers | {report['total_correct']} |
| **Overall Accuracy** | **{report['overall_accuracy']:.1f}%** |
| Average Response Time | {report['avg_response_time']:.2f}s |

## Accuracy by Category

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
"""
    
    for cat, stats in sorted(report['category_breakdown'].items()):
        name = cat_names.get(cat, f'cat-{cat}')
        md += f"| {cat} ({name}) | {stats['correct']} | {stats['total']} | {stats['accuracy']:.1f}% |\n"
    
    md += "\n## Per-Sample Breakdown\n\n"
    
    # Group by sample
    from collections import defaultdict
    by_sample = defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in report['results']:
        by_sample[r['sample_idx']]['total'] += 1
        if r['correct']:
            by_sample[r['sample_idx']]['correct'] += 1
    
    md += "| Sample | Correct | Total | Accuracy |\n|--------|---------|-------|----------|\n"
    for sample_idx in sorted(by_sample.keys()):
        s = by_sample[sample_idx]
        acc = s['correct'] / s['total'] * 100
        md += f"| {sample_idx} | {s['correct']} | {s['total']} | {acc:.1f}% |\n"
    
    md += "\n## Sample Results\n\n"
    
    # Show first 10 results
    for r in report['results'][:10]:
        md += f"**Sample {r['sample_idx']}, Q{r['question_idx']} (Cat {r['category']}):** {'✓' if r['correct'] else '✗'}\n"
        md += f"- Question: {r['question']}\n"
        md += f"- Ground Truth: {r['ground_truth']}\n"
        md += f"- Agent Response: {r['agent_response'][:200]}...\n"
        md += f"- Match Type: {r['match_type']}\n\n"
    
    md += "\n## Failure Analysis\n\n"
    
    # Show some failures
    failures = [r for r in report['results'] if not r['correct']][:10]
    if failures:
        md += "### Sample Failures\n\n"
        for f in failures:
            md += f"**Sample {f['sample_idx']}, Q{f['question_idx']} (Cat {f['category']}):**\n"
            md += f"- Question: {f['question']}\n"
            md += f"- Ground Truth: {f['ground_truth']}\n"
            md += f"- Agent Response: {f['agent_response'][:200]}...\n"
            md += f"- Match Type: {f['match_type']}\n\n"
    else:
        md += "No failures recorded.\n"
    
    with open(md_file, 'w') as f:
        f.write(md)
    print(f"Markdown report saved to {md_file}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Bonobot LOCOMO Benchmark')
    parser.add_argument('--all', action='store_true', help='Run on all 10 samples (default: samples 0-2)')
    parser.add_argument('--skip-llm', action='store_true', help='Skip LLM calls (for testing infrastructure)')
    parser.add_argument('--check', action='store_true', help='Check API connectivity and exit')
    args = parser.parse_args()
    
    if args.check:
        print("Checking API connectivity...")
        try:
            resp = requests.get(f"{API_BASE}/api/health", timeout=10)
            print(f"Health check: {resp.status_code}")
            print(f"Response: {resp.text}")
            
            # Try authenticated endpoint
            resp = requests.get(f"{API_BASE}/api/projects", headers=api_headers(), timeout=10)
            print(f"Auth check: {resp.status_code}")
            if resp.status_code == 200:
                print("API is ready for benchmarking!")
            else:
                print(f"Auth failed: {resp.text}")
        except Exception as e:
            print(f"ERROR: {e}")
        sys.exit(0)
    
    if args.all:
        samples = list(range(10))
        print("Running benchmark on all 10 samples...")
    else:
        samples = [0, 1, 2]
        print("Running benchmark on samples 0-2 (use --all for all 10)...")
    
    if args.skip_llm:
        print("NOTE: Running in simulation mode (--skip-llm). No actual LLM calls will be made.")
    
    report = run_benchmark(samples, skip_llm=args.skip_llm)
    
    if report:
        save_results(report)
        
        print(f"\n{'='*60}")
        print(f"BENCHMARK COMPLETE")
        print(f"{'='*60}")
        print(f"Overall Accuracy: {report['overall_accuracy']:.1f}%")
        print(f"Total Questions: {report['total_questions']}")
        print(f"Correct: {report['total_correct']}")
        print(f"Avg Response Time: {report['avg_response_time']:.2f}s")
        print(f"\nCategory Breakdown:")
        for cat, stats in sorted(report['category_breakdown'].items()):
            name = report['category_names'].get(cat, f'cat-{cat}')
            print(f"  {cat} ({name}): {stats['accuracy']:.1f}% ({stats['correct']}/{stats['total']})")
    else:
        print("\nBenchmark failed. Check errors above.")
