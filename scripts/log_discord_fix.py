"""Log discord-mcp fix to Fritz."""
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
            print(sc.get("message", str(sc)[:100]))

c("evolution_record", {"correction":"code_generate replaced discord-mcp server.py with stub", "lesson":"code_generate for new files only. Use sed/replace for existing file edits.", "context":"discord-mcp real repo test"})
c("memory_project_note", {"project":"discord-mcp", "content":"Fixed S104 (0.0.0.0). code_generate destroyed file first. Reverted, fixed with sed, PR #2 merged."})
print()
print("Lesson learned: LLM codegen for surgical edits is risky.")
print("Fix: use code_generate for NEW files, use sed/replace for EXISTING files.")
