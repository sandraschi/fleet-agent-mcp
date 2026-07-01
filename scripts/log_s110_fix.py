"""Log discord-mcp S110 fix to Fritz."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

def c(t, a):
    p = {"jsonrpc":"2.0","method":"tools/call","params":{"name":t,"arguments":a},"id":1}
    r = httpx.post(url, json=p, headers=H, timeout=15)
    for l in r.text.splitlines():
        if l.startswith("data: "):
            sc = json.loads(l[6:]).get("result",{}).get("structuredContent",{})
            print(sc.get("message",""))

c("evolution_record", {"correction":"Bare except Exception: pass in discord-mcp","lesson":"file_edit is safe for surgical edits. code_generate is not.","context":"discord-mcp S110 fix via file_edit"})
c("memory_project_note", {"project":"discord-mcp","content":"File_edit used to fix S110 bare except. Backup+verify worked perfectly. PR #4 merged."})
print()
print("discord-mcp PRs merged by Fritz:")
print("  PR #2: 0.0.0.0 -> 127.0.0.1 (S104, via sed)")
print("  PR #4: bare except -> logger.warning (S110, via file_edit)")
print()
print("file_edit proven: .bak backup + auto-verify both confirmed.")
