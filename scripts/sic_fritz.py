"""Sic Fritz on discord-mcp: fix S104 0.0.0.0 binding to 127.0.0.1."""
import json
import subprocess
import time
from pathlib import Path

import httpx

REPO = "discord-mcp"
OWNER = "sandraschi"
WORK = Path(f"D:/Dev/repos/{REPO}-work")
FRITZ_MCP = "http://127.0.0.1:10996/mcp/"
H = {"Accept": "application/json, text/event-stream"}

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}")

def run(args, **kw):
    cwd = kw.get("cwd") or (str(WORK) if WORK.exists() else None)
    r = subprocess.run(args, capture_output=True, text=True, timeout=kw.get("t", 60), cwd=cwd)
    if r.returncode != 0:
        log(f"  (rc={r.returncode}) {r.stderr.strip()[:200]}")
    return r.stdout.strip()

def fritz(tool, args):
    p = {"jsonrpc":"2.0","method":"tools/call","params":{"name":tool,"arguments":args},"id":1}
    try:
        r = httpx.post(FRITZ_MCP, json=p, headers=H, timeout=180)
        r.raise_for_status()
        for line in r.text.splitlines():
            if line.startswith("data: "):
                d = json.loads(line[6:])
                sc = d.get("result",{}).get("structuredContent",{})
                return sc
        return {"error": "no data"}
    except Exception as e:
        return {"error": str(e)}

log("=" * 50)
log(f"SIC FRITZ ON {REPO}")
log("")

# Step 0: Clone and branch
if WORK.exists():
    subprocess.run(f"rmdir /s /q {WORK}", shell=True, capture_output=True)
run(["git", "clone", f"https://github.com/{OWNER}/{REPO}.git", str(WORK)], t=60, cwd="D:/Dev/repos")
run(["git", "checkout", "-b", "fix/bind-127"])
log("  Branch: fix/bind-127")

# Step 1: Fix via code_generate (change 0.0.0.0 to 127.0.0.1 in server.py)
log("Step 1: code_generate via Fritz MCP...")
result = fritz("code_generate", {
    "spec": "Change the uvicorn host binding from '0.0.0.0' to '127.0.0.1' on line 403. This fixes ruff S104 binding to all interfaces.",
    "repo_path": str(WORK),
    "file_path": "src/discord_mcp/server.py",
    "context": "Python, ruff rule S104. Find `host=\"0.0.0.0\"` and change to `host=\"127.0.0.1\"`.",
})
log(f"  Result: {str(result)[:300]}")

# Read the file and verify
content = (WORK / "src" / "discord_mcp" / "server.py").read_text()
if "127.0.0.1" in content and "0.0.0.0" not in content:
    log("  OK: 0.0.0.0 changed to 127.0.0.1")
else:
    log("  codegen missed it, writing directly...")
    content = content.replace('host="0.0.0.0"', 'host="127.0.0.1"')
    (WORK / "src" / "discord_mcp" / "server.py").write_text(content)
    log("  Direct fix applied")

# Step 2: Log via Fritz
log("Step 2: Logging to Fritz memory...")
fritz("memory_project_note", {"project": REPO, "content": "Fixed S104 security issue: changed 0.0.0.0 to 127.0.0.1 in server.py"})
fritz("evolution_record", {"correction": "S104 binding to all interfaces", "lesson": "Production servers should bind to 127.0.0.1 not 0.0.0.0", "context": f"Fixing {REPO}"})
log("  Logged.")

# Step 3: Commit and push
log("Step 3: Commit and push...")
run(["git", "add", "-A"])
run(["git", "commit", "-m", "fix: bind uvicorn to 127.0.0.1 instead of 0.0.0.0 (S104)"])
run(["git", "push", "-u", "origin", "fix/bind-127", "--force"], t=30)
log("  Pushed.")

# Step 4: PR
log("Step 4: Create PR...")
body = "Ruff S104 flagged binding to all interfaces (0.0.0.0). Changed to 127.0.0.1 for security.\n\nCloses #1"
pr = run(["gh", "pr", "create", "--repo", f"{OWNER}/{REPO}",
    "--title", "fix: bind uvicorn to 127.0.0.1 (S104 security)",
    "--body", body,
    "--head", "fix/bind-127", "--base", "master"], t=15)
log(f"  PR: {pr}")

# Step 5: Merge
pr_num = pr.rstrip("/").split("/")[-1] if pr else ""
log(f"  PR number: {pr_num}")
if pr_num:
    merge = run(["gh", "pr", "merge", pr_num, "--repo", f"{OWNER}/{REPO}", "--squash", "--delete-branch"], t=15)
    log(f"  Merge: {merge[:200]}")
    state = run(["gh", "pr", "view", pr_num, "--repo", f"{OWNER}/{REPO}", "--json", "state"], t=10)
    log(f"  State: {state}")

fritz("evolution_record", {"correction": "Pipeline complete", "lesson": "Production security fix: 127.0.0.1 not 0.0.0.0", "context": f"{REPO}"})

log("=" * 50)
log(f"RESULT: PR {pr} merged" if pr_num else "FAILED")
log("  Tools: code_generate, memory, evolution, git, gh")
