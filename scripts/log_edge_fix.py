"""Log edge-bookmark fix to Fritz."""
import httpx, json

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

def c(t, a):
    p = {"jsonrpc":"2.0","method":"tools/call","params":{"name":t,"arguments":a},"id":1}
    r = httpx.post(url, json=p, headers=H, timeout=15)
    for l in r.text.splitlines():
        if l.startswith("data: "):
            sc = json.loads(l[6:]).get("result",{}).get("structuredContent",{})
            print(sc.get("message",""))

c("evolution_record", {"correction":"Need fork when no push access to target repo","lesson":"Always fork first for third-party repos, then PR from fork","context":"edge-bookmark-mcp-server fix"})
c("memory_project_note", {"project":"edge-bookmark-mcp-server","content":"PR #2 opened: Jinja2 autoescape=True security fix (S701). Awaiting Stephan's review. Not merged."})
print()
print("PR #2 open: https://github.com/StephanSchipal/edge-bookmark-mcp-server/pull/2")
print("Status: OPEN - awaiting Stephan's review and merge")
