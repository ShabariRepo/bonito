# Proposal: Session-Scoped Rolling Transcript for Agent Execute

**Author:** Shabari + Claude
**Status:** Draft — needs branch + prototype
**Owners:** Backend (executeAgent path) + Memwright maintainers
**Target users:** Any Bonito app that builds a chat UI on top of `/api/agents/{id}/execute` (ouchgpt, AdVan, future apps)

---

## TL;DR

`POST /api/agents/{id}/execute` accepts a single `message` and runs the agent with no awareness of prior turns. Apps are reinventing transcript handling on their side — and doing it badly. **ouchgpt's chat felt amnesiac because it was sending one message at a time to an agent with no session memory; the only thing Bonito offered for recall was Memwright similarity search, which is wrong for "what did the user just say."**

We propose: `executeAgent` accepts an optional `session_id`. When provided, Bonito automatically (a) writes the user message and agent reply to a session-scoped rolling transcript, and (b) injects the last N turns into the prompt before calling the LLM.

Apps stop reinventing this. Hermes, Bonobot, and any future orchestrator inherit short-term memory for free.

---

## The problem in concrete terms

**Current state of `/api/agents/{id}/execute`:**

```json
POST /api/agents/{id}/execute
{ "message": "what should I do about the tingling?" }
```

The agent runs with this single string. It has zero knowledge of:
- What the user said two messages ago
- What advice the agent gave two messages ago
- Whether this is turn 1 or turn 50

**What apps do today (ouchgpt example):**

1. Maintain `Conversation` rows in their own DB
2. Maintain message state in React
3. On each turn, call `searchMemories()` (Memwright similarity search) to pull "related" memories
4. Glue everything into a prompt manually
5. Hope the similarity search surfaces the recent stuff (it doesn't reliably)

**The user-visible symptom:** "I have tingling at 6/10" → "ok" → "what should I do?" → agent has forgotten about the tingling, asks a generic question.

This is not a Memwright bug. Memwright is doing exactly what it was designed for (long-horizon, similarity-retrieved extracted memories). The missing primitive is **a recency-ordered rolling transcript per session**.

---

## Why similarity search doesn't fix this

Memwright (`searchMemories`) ranks memories by vector similarity to the current query. Two failure modes:

1. **Recency loss.** "What should I do about the tingling?" doesn't necessarily have higher cosine similarity to "I have tingling around 6/10" than to some older note about Achilles exercises. The most-relevant-by-meaning memory might not be the most-recently-said one.
2. **Extraction lag.** `extractConversationMemories` runs *after* `executeAgent` returns. So the user's most recent message is not even searchable until the next turn — and only if it was deemed "worth extracting." Most casual conversational glue ("ok", "yes", "I'm not sure") never gets extracted.

A recency window doesn't replace memory — it complements it. We need both.

---

## Proposed API

### Backwards-compatible additions

```http
POST /api/agents/{agent_id}/execute
{
  "message": "what should I do?",
  "session_id": "user-42-chat",        // NEW (optional)
  "transcript_window": 8,              // NEW (optional, default 8)
  "include_transcript": true           // NEW (optional, default true when session_id is set)
}
```

- If `session_id` is omitted: behavior is unchanged. (Backward compatible.)
- If `session_id` is provided: Bonito performs a rolling-window transcript inject + write, scoped to `(org_id, agent_id, session_id)`.
- `transcript_window`: how many prior turns to inject. Cap at e.g. 50 server-side.
- `include_transcript`: lets the caller temporarily skip injection (e.g. tools that want a clean slate) without losing the write.

### Response (additive)

```json
{
  "content": "...",
  "tool_calls": [...],
  "session_id": "user-42-chat",
  "transcript_turns_used": 6
}
```

`transcript_turns_used` makes it cheap for the app to verify the agent actually saw context, useful when debugging "did it forget again?"

### CLI (`bonito agents run`)

```bash
bonito agents run my-agent --session user-42-chat --message "what should I do?"
```

---

## Storage

Two reasonable options. Recommend **Option A** — reuse what's already there.

### Option A — reuse Memwright session storage (recommended)

Memwright already maintains session-scoped messages in SQLite + ChromaDB ("Per-session memory via SQLite + ChromaDB", per Bonito CLAUDE.md, Feature 6). The piece we'd add:

- A direct SQLite query `get_recent_turns(session_id, n)` that bypasses Chroma similarity and returns plain recency-ordered turns.
- A write-on-every-turn path: after `executeAgent` completes, write `{role: "user", content: message}` and `{role: "assistant", content: response}` to the same Memwright session.

**Pros:** no new table, single source of truth, free retention from existing Memwright LRU eviction (256-instance cap noted in CLAUDE.md).
**Cons:** Memwright was designed for "extract → embed → similarity search". Adding a "give me raw recent rows" path is a small extension but slightly muddies its purpose.

### Option B — new `agent_sessions` Postgres table

```sql
CREATE TABLE agent_sessions (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  session_key TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_session_turns (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
  content TEXT NOT NULL,
  tool_calls JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX (session_id, created_at)
);

CREATE UNIQUE INDEX ON agent_sessions (org_id, agent_id, session_key);
```

**Pros:** clean separation, queryable, multi-tenant retention policies trivial.
**Cons:** new migration, new code path, duplication with Memwright session state.

### Hybrid (optional later)

Memwright stays for similarity / extraction; new Postgres table stays for transcript. They're conceptually different layers anyway — short-term recency vs. long-term semantic.

---

## Prompt assembly inside `executeAgent`

Pseudocode for the gateway-side change (Python, in the agent execute path):

```python
async def execute_agent(agent_id, message, session_id=None, transcript_window=8, include_transcript=True):
    transcript_block = ""
    if session_id and include_transcript:
        turns = await memwright.get_recent_turns(session_id, n=transcript_window)
        if turns:
            transcript_block = "[RECENT CONVERSATION — oldest first]\n" + "\n\n".join(
                f"{t.role.title()}: {t.content}" for t in turns
            )

    enriched = "\n\n".join(filter(None, [
        agent.system_prompt,
        transcript_block,
        f"[USER MESSAGE]\n{message}",
    ]))

    response = await llm.complete(enriched, ...)

    if session_id:
        await memwright.append_turn(session_id, role="user", content=message)
        await memwright.append_turn(session_id, role="assistant", content=response.content)

    return response
```

Key invariants:
- Writes happen **after** the LLM call so a failed call doesn't pollute the transcript.
- Reads happen **before** the LLM call, so the current message is NOT in the transcript yet (avoids duplication).
- `session_id` is namespaced server-side as `(org_id, agent_id, session_id)`. Apps can use arbitrary strings — "user-42", "lead-abc", whatever.

---

## Tier gating

Per Bonito CLAUDE.md, Memwright is already model-tier-gated (zero memory for small models). The transcript primitive should follow the same rule: if the agent is wired to a small model, the transcript window auto-clamps to e.g. 2-3 turns instead of 8. Tunable in `core/feature_gate.py`.

Free/Starter tier could be capped at 4 turns; Pro+ at 16-32.

---

## Retention

- Default: 30 days, then evicted by background job.
- Configurable per agent via `agent.session_retention_days`.
- `DELETE /api/agents/{id}/sessions/{session_id}` for app-driven cleanup (e.g. when ouchgpt deletes a user).

---

## Migration path for existing apps

1. **ouchgpt**: change `executeAgent(agentId, message)` to `executeAgent(agentId, message, { session_id: \`ouchgpt-user-\${user.id}\` })`. Delete the homegrown transcript injection code added in this iteration.
2. **AdVan**: uses memwright standalone — unaffected. Their server-side memwright instance is independent of Bonito's transcript primitive.
3. **Future apps**: just pass a session_id. Done.

---

## Risks & tradeoffs

- **Prompt length growth.** Each turn adds N×~200 tokens of transcript. At window 8, that's ~1.6K tokens of overhead per call. Acceptable. Apps that want lean prompts can pass `include_transcript: false`.
- **Stale transcripts after persona/system-prompt changes.** If the agent's persona changes mid-session (ouchgpt's exact use case!), the transcript still contains the old persona's replies. **This is desired** — the new persona seeing old replies is what enables seamless handoff. The handoff-acknowledgement instruction goes in the system prompt, not the transcript.
- **PII in transcripts.** Same as any chat log. Subject to the same encryption + retention rules. Audit log entries for delete/access. No new attack surface beyond what Memwright already has.
- **Memwright LRU eviction (256 instances).** Could prematurely evict an active session. Need to verify eviction is by recency-of-access, not creation. If not, raise the cap or move to Postgres.

---

## Open questions for the branch

1. Option A (extend Memwright) vs Option B (new Postgres table)? My read: A.
2. Should `session_id` be auto-derived from auth context (e.g. user_id + agent_id) when omitted, or strictly opt-in? My read: strictly opt-in for now, auto-derive in a later iteration.
3. Should tool calls + tool results land in the transcript too? Probably yes for agents with tools, but it bloats the prompt fast. Maybe a `transcript_include_tools` flag.
4. What's the right CLI ergonomic for inspecting a session? `bonito agents sessions list <agent>` + `bonito agents sessions show <agent> <session_id>`?

---

## Test plan (when we branch)

- Unit: `get_recent_turns` returns rows in correct order, respects `n`.
- Integration: two consecutive `executeAgent` calls with same `session_id` — second call's prompt contains the first call's user message + assistant response. Verified by capturing the upstream LLM request.
- E2E: ouchgpt branch that uses `session_id` — repro the original "I have tingling" / "what should I do?" sequence and confirm the agent references tingling in the second response.
- Load: 100 concurrent sessions, verify Memwright LRU doesn't evict active ones.
- Tier gate: small-model agent receives transcript clamped to 2-3 turns.

---

## What we're NOT proposing

- Replacing Memwright. Long-horizon extracted memory is still useful — this proposal is purely about the recency window that Memwright doesn't cleanly serve.
- Streaming transcripts back to the client. Apps already have their own UI message state.
- Cross-agent transcripts. If user talks to Agent A then Agent B in the same session, that's a separate, harder problem (would require explicit ACL on cross-agent reads).

---

## Next step

Branch `feat/agent-session-transcript`, implement Option A + the API additions, run the ouchgpt repro, ship behind a feature flag.
