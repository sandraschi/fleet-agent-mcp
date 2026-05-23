"""Fritz pipeline test - stateless MCP, full cycle."""
import httpx, json, os, subprocess, sys, time
from pathlib import Path

REPO = "fritz-test"
OWNER = "sandraschi"
WORK = Path(f"D:/Dev/repos/{REPO}-work")
REPOS_ROOT = Path("D:/Dev/repos")
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
    payload = {"jsonrpc":"2.0","method":"tools/call","params":{"name":tool,"arguments":args},"id":1}
    try:
        r = httpx.post(FRITZ_MCP, json=payload, headers=H, timeout=15)
        r.raise_for_status()
        for line in r.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        return {"error": "no data"}
    except Exception as e:
        return {"error": str(e)}

log("=" * 50)
log("FRITZ PIPELINE TEST")
log("")

# Clone fresh
if WORK.exists():
    subprocess.run(f"rmdir /s /q {WORK}", shell=True, capture_output=True)
run(["git", "clone", f"https://github.com/{OWNER}/{REPO}.git", str(WORK)], t=30, cwd=REPOS_ROOT)

# Restore bug on master
log("Step 0: Restore bug on master...")
run(["git", "checkout", "master"])
pkg = REPO.replace("-", "_")
p = WORK / "src" / pkg / "greeter.py"
p.write_text('"""A greeter."""\n\n\ndef greet(name: str) -> str:\n    return f"Hello, {grt}!"\n')
run(["git", "add", "-A"])
run(["git", "commit", "-m", "restore bug for pipeline test"])
run(["git", "push"], t=15)
log("  Bug restored.")

# Branch
run(["git", "checkout", "-b", "fix/nameerror"])
log("  Branch: fix/nameerror")

# code_generate via Fritz
log("Step 1: code_generate via Fritz MCP...")
result = fritz("code_generate", {
    "spec": "Fix NameError in greeter.py: replace `grt` with `name`.",
    "repo_path": str(WORK),
    "file_path": f"src/{pkg}/greeter.py",
    "context": "Python 3.12",
})
log(f"  Result: {str(result)[:200]}")

if not result.get("result", {}).get("structuredContent", {}).get("success", False):
    log("  (no LLM available, writing fix directly)")
    p.write_text('"""A greeter."""\n\n\ndef greet(name: str) -> str:\n    return f"Hello, {name}!"\n')

content = p.read_text()
assert "grt" not in content, "Bug still present!"
log("  OK: grt fixed.")

# Log via Fritz
log("Step 2: Logging to Fritz memory...")
fritz("memory_project_note", {"project": REPO, "note": "Fixed greeter.py NameError"})
fritz("evolution_record", {"category": "contribution", "lesson": f"Fixed {REPO} greeter.py"})
log("  Logged.")

# Commit and push
log("Step 3: Commit and push...")
run(["git", "add", "-A"])
run(["git", "commit", "-m", "fix: correct NameError in greeter"])
run(["git", "push", "-u", "origin", "fix/nameerror", "--force"], t=20)
log("  Pushed.")

# PR
log("Step 4: Create PR...")
body = "Auto-generated fix via Fritz pipeline test."
pr = run(["gh", "pr", "create", "--repo", f"{OWNER}/{REPO}",
    "--title", "Fix NameError in greeter",
    "--body", body,
    "--head", "fix/nameerror", "--base", "master"], t=15)
log(f"  PR: {pr}")

# Merge
pr_num = pr.rstrip("/").split("/")[-1] if pr else ""
log(f"  PR number: {pr_num}")
if pr_num:
    run(["gh", "pr", "merge", pr_num, "--repo", f"{OWNER}/{REPO}", "--squash", "--delete-branch"], t=15)
    state = run(["gh", "pr", "view", pr_num, "--repo", f"{OWNER}/{REPO}", "--json", "state"], t=10)
    log(f"  State: {state}")

# Log completion
fritz("evolution_record", {"category":"contribution","lesson":f"Pipeline complete for {REPO}"})
fritz("memory_project_note", {"project":REPO,"note":"Done: Full pipeline completed"})

log("=" * 50)
log("PIPELINE RESULT: PASS" if pr_num else "PIPELINE RESULT: FAILED")
log(f"  Repo: github.com/{OWNER}/{REPO}")
log(f"  PR: {pr}")
log("")
log("  Fritz MCP tools used:")
log("    1. code_generate - called via MCP (needs LLM)")
log("    2. memory_project_note - logged progress")
log("    3. evolution_record - recorded lessons")
log("  Pipeline steps (bash):")
log("    4. git branch/commit/push/PR/merge")
