#!/usr/bin/env python3
"""Separate-orgs hackathon — each persona runs in its OWN prod org (isolated,
no cross-project contamination). Logs every prompt + outcome to a JSONL file
so we can see which prompts land and which don't, and why.

Usage: python3 hackathon.py            (runs all provisioned orgs)
Reads /tmp/htest_orgs.json (list of {tag, org_id, token})."""
import asyncio, json, re, time, uuid, os, urllib.request, urllib.error

API = os.getenv("BONITO_API", "https://api.getbonito.com")
ORGS = json.load(open(os.getenv("LOADTEST_ORGS", "/tmp/htest_orgs.json")))
RUN_DIR = os.getenv("LOADTEST_RUNDIR", "/tmp/hackathon-runs")
os.makedirs(RUN_DIR, exist_ok=True)
STAMP = str(int(time.time()))
LOG = open(f"{RUN_DIR}/run-{STAMP}.jsonl", "w")
MAXC = int(os.getenv("LOADTEST_CONCURRENCY", "8"))
LEAK_RE = re.compile(r"```typescript|```json|<function_calls>|<tool_call>|<invoke|invoke_agent\(", re.I)

# (name, role, [ (kind, prompt, expect{p,k,a,key}) ])  — {ns} -> per-persona namespace
P = [
 ("Maya","Healthcare",[("chat","hey what is this?"),("chat","help triage patient symptoms"),
   ("build","create a project {ns}-clinic, a KB {ns}-symptoms, and an agent {ns}-triage that uses the KB",{"p":["{ns}-clinic"],"k":["{ns}-symptoms"],"a":["{ns}-triage"]}),
   ("chat","do you support HIPAA?")]),
 ("Jake","VC",[("build","create a project {ns}-deals",{"p":["{ns}-deals"]}),
   ("build","in {ns}-deals build a hub agent {ns}-intake that routes to three spokes {ns}-market, {ns}-finance, {ns}-team. wire hub to each with handoffs",{"a":["{ns}-intake","{ns}-market","{ns}-finance","{ns}-team"]}),
   ("build","mint a gateway key {ns}-prod",{"key":["{ns}-prod"]})]),
 ("Priya","DevTools",[("chat","building a dev tool, need code review agents"),
   ("build","create a project {ns}-devtools, a KB {ns}-styleguide, and an agent {ns}-reviewer that uses the KB",{"p":["{ns}-devtools"],"k":["{ns}-styleguide"],"a":["{ns}-reviewer"]})]),
 ("Alex","Marketing",[("build","create a project {ns}-marketing",{"p":["{ns}-marketing"]}),
   ("build","build a content team in {ns}-marketing: a strategist hub {ns}-lead that hands off to {ns}-copy and {ns}-seo",{"a":["{ns}-lead","{ns}-copy","{ns}-seo"]})]),
 ("Sam","SoloDev",[("chat","need a chatbot for my shopify store"),
   ("build","set it up in a project {ns}-shopify with a KB {ns}-products and an agent {ns}-support that uses the KB",{"p":["{ns}-shopify"],"k":["{ns}-products"],"a":["{ns}-support"]})]),
 ("Daniela","Ecomm",[("build","make a project {ns}-retail, a KB {ns}-returns, an agent {ns}-rma that uses the KB, and a key {ns}-live",{"p":["{ns}-retail"],"k":["{ns}-returns"],"a":["{ns}-rma"],"key":["{ns}-live"]})]),
 ("Marcus","FinTech",[("build","create a project {ns}-fraud",{"p":["{ns}-fraud"]}),
   ("build","in {ns}-fraud build a triage hub {ns}-triage that hands off to {ns}-rules and {ns}-analyst",{"a":["{ns}-triage","{ns}-rules","{ns}-analyst"]})]),
 ("Wei","Legal",[("build","create project {ns}-legal, KB {ns}-contracts, and agent {ns}-counsel that uses the KB",{"p":["{ns}-legal"],"k":["{ns}-contracts"],"a":["{ns}-counsel"]})]),
 ("Olivia","EdTech",[("build","set up a project {ns}-classroom, a KB {ns}-curriculum, and a tutor agent {ns}-tutor that uses the KB",{"p":["{ns}-classroom"],"k":["{ns}-curriculum"],"a":["{ns}-tutor"]})]),
 ("Raj","Logistics",[("build","create a project {ns}-logistics and an agent {ns}-tracker",{"p":["{ns}-logistics"],"a":["{ns}-tracker"]}),
   ("build","mint a gateway key {ns}-api",{"key":["{ns}-api"]})]),
 ("Sofia","RealEstate",[("build","build a project {ns}-realty, a KB {ns}-listings, and an agent {ns}-concierge that uses the KB",{"p":["{ns}-realty"],"k":["{ns}-listings"],"a":["{ns}-concierge"]})]),
 ("Tom","Gaming",[("build","create a project {ns}-game",{"p":["{ns}-game"]}),
   ("build","in {ns}-game build a dialog hub {ns}-director that hands off to {ns}-npc and {ns}-quest",{"a":["{ns}-director","{ns}-npc","{ns}-quest"]})]),
 ("Nadia","HR",[("build","create project {ns}-hiring, KB {ns}-jobspec, and agent {ns}-screener that uses the KB",{"p":["{ns}-hiring"],"k":["{ns}-jobspec"],"a":["{ns}-screener"]})]),
 ("Ben","Restaurant",[("build","create a project {ns}-dining and an agent {ns}-host",{"p":["{ns}-dining"],"a":["{ns}-host"]})]),
 ("Grace","Nonprofit",[("build","make a project {ns}-nonprofit, a KB {ns}-donorfaq, and an agent {ns}-helper that uses it",{"p":["{ns}-nonprofit"],"k":["{ns}-donorfaq"],"a":["{ns}-helper"]})]),
 ("Hassan","Insurance",[("build","create a project {ns}-insurance",{"p":["{ns}-insurance"]}),
   ("build","build a claims hub {ns}-claims in {ns}-insurance that hands off to {ns}-coverage and {ns}-payout",{"a":["{ns}-claims","{ns}-coverage","{ns}-payout"]})]),
 ("Lena","Travel",[("build","create project {ns}-travel, a KB {ns}-dest, an agent {ns}-planner that uses the KB, and a key {ns}-key",{"p":["{ns}-travel"],"k":["{ns}-dest"],"a":["{ns}-planner"],"key":["{ns}-key"]})]),
 ("Carlos","Mfg",[("build","set up project {ns}-factory, KB {ns}-sops, and agent {ns}-assistant using the KB",{"p":["{ns}-factory"],"k":["{ns}-sops"],"a":["{ns}-assistant"]})]),
 ("Aisha","Media",[("build","create a project {ns}-newsroom and an agent {ns}-summarizer",{"p":["{ns}-newsroom"],"a":["{ns}-summarizer"]})]),
 ("Victor","Security",[("build","create a project {ns}-soc",{"p":["{ns}-soc"]}),
   ("build","build a SOC triage hub {ns}-soctriage in {ns}-soc that hands off to {ns}-malware and {ns}-network",{"a":["{ns}-soctriage","{ns}-malware","{ns}-network"]}),
   ("build","mint a gateway key {ns}-siem",{"key":["{ns}-siem"]})]),
]


def req(path, token, body=None):
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    return urllib.request.Request(API + path, data=data, headers=h, method="POST" if body else "GET")


def get(path, token):
    for _ in range(3):
        try:
            with urllib.request.urlopen(req(path, token), timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2)
    return []


async def turn(token, conv, msg):
    """Stream a studio turn; return (tools_started, tools_completed, tools_failed, text, error)."""
    loop = asyncio.get_event_loop()
    def _run():
        ts, tc, tf, text, err = [], [], [], "", None
        try:
            with urllib.request.urlopen(req("/api/studio/turn", token, {"message": msg, "conversation_id": conv}), timeout=200) as r:
                for raw in r:
                    line = raw.decode().strip()
                    if not line.startswith("data: "):
                        continue
                    try: ev = json.loads(line[6:])
                    except: continue
                    t = ev.get("type")
                    if t == "tool_started": ts.append(ev.get("tool_name"))
                    elif t == "tool_completed": tc.append(ev.get("tool_name"))
                    elif t == "tool_failed": tf.append((ev.get("tool_name"), str(ev.get("error"))[:100]))
                    elif t == "message_complete": text = ev.get("text", "")
                    elif t == "error": err = str(ev.get("message"))[:160]
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
        except Exception as e:
            err = str(e)[:120]
        return ts, tc, tf, text, err
    return await loop.run_in_executor(None, _run)


def classify(expect, tc, tf, err):
    if err and "429" in str(err): return "CAP_429"
    if err: return "ERROR"
    need = set()
    for k in ("p", "k", "key"): need |= {"create_project" if k == "p" else "create_kb" if k == "k" else "mint_gateway_key"} if expect.get(k) else set()
    if expect.get("a"): need.add("create_agent")
    got = set(tc)
    if need <= got:
        # team builds need N agents
        if expect.get("a") and len(expect["a"]) > 1 and tc.count("create_agent") < len(expect["a"]):
            return "MODEL_UNDERDELIVER" if not tf else "WIRING_FAIL"
        return "SUCCESS"
    if any("not_found" in str(e[1]) or "different project" in str(e[1]) for e in tf):
        return "CONTAMINATION"
    return "MODEL_UNDERDELIVER"


async def run_persona(org, name, role, turns):
    ns = f"{name.lower()}-{uuid.uuid4().hex[:5]}"
    token = org["token"]
    conv = str(uuid.uuid4())
    want = {"p": set(), "k": set(), "a": set(), "key": set()}
    for ti, t in enumerate(turns):
        kind, prompt = t[0], t[1].replace("{ns}", ns)
        expect = {k: [v.replace("{ns}", ns) for v in vals] for k, vals in (t[2].items() if len(t) > 2 else [])}
        for k, vals in expect.items():
            want[k] |= set(vals)
        ts, tc, tf, text, err = await turn(token, conv, prompt)
        cls = classify(expect, tc, tf, err) if kind == "build" else ("LEAK" if LEAK_RE.search(text or "") else "CHAT_OK")
        rec = {"org": org["tag"], "persona": name, "role": role, "turn": ti, "kind": kind,
               "prompt": prompt, "tools_completed": tc, "tools_failed": tf,
               "error": err, "text_preview": (text or "")[:160], "classify": cls}
        LOG.write(json.dumps(rec) + "\n"); LOG.flush()
    return name, ns, want, token


def login(org):
    """Log in via the API so the running server signs the token."""
    body = {"email": org["email"], "password": org["password"]}
    with urllib.request.urlopen(req("/api/auth/login", None, body) if False else
        urllib.request.Request(API + "/api/auth/login",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST"),
        timeout=30) as r:
        return json.loads(r.read())["access_token"]


async def main():
    print(f"=== SEPARATE-ORGS HACKATHON · {len(ORGS)} orgs · prod Sonnet · log: {LOG.name} ===")
    for org in ORGS:
        org["token"] = login(org)
    print(f"logged in {len(ORGS)} orgs")
    sem = asyncio.Semaphore(MAXC)
    async def guarded(org, p):
        async with sem: return await run_persona(org, p[0], p[1], p[2])
    tasks = [guarded(org, P[i % len(P)]) for i, org in enumerate(ORGS)]
    t0 = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0
    # verify per-org (isolated)
    npass = 0
    for name, ns, want, token in results:
        proj = {p["name"] for p in get("/api/projects", token)}
        kbs = {k["name"] for k in get("/api/knowledge-bases", token)}
        keys = {k["name"] for k in get("/api/gateway/keys", token)}
        agents = set()
        for p in get("/api/projects", token):
            for a in get(f"/api/projects/{p['id']}/agents", token) or []:
                agents.add(a["name"])
        ok = (want["p"] <= proj and want["k"] <= kbs and want["a"] <= agents and want["key"] <= keys)
        npass += ok
        miss = []
        if want["p"] - proj: miss.append(f"proj:{sorted(want['p']-proj)}")
        if want["k"] - kbs: miss.append(f"kb:{sorted(want['k']-kbs)}")
        if want["a"] - agents: miss.append(f"agent:{sorted(want['a']-agents)}")
        if want["key"] - keys: miss.append(f"key:{sorted(want['key']-keys)}")
        print(f"  {'🟢' if ok else '🔴'} {name:9} " + ("OK" if ok else "MISS " + " ".join(miss)))
    print(f"\nRESULT: {npass}/{len(ORGS)} passed | wall={elapsed:.0f}s | log={LOG.name}")
    LOG.close()

asyncio.run(main())
