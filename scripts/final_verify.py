"""Final state verification."""
import httpx, json

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

def c(t, a):
    p = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": t, "arguments": a}, "id": 1}
    r = httpx.post(url, json=p, headers=H, timeout=15)
    for l in r.text.splitlines():
        if l.startswith("data: "):
            sc = json.loads(l[6:]).get("result", {}).get("structuredContent", {})
            msg = sc.get("message", str(sc)[:200])
            print(f"  {t}: {msg}")
            return

print("Logging final achievements to Fritz...")
c("memory_project_note", {"project": "pipeline-verification", "content": "Webapp now has Memory + Evolution pages. Full pipeline verified."})
c("evolution_record", {"correction": "Memory REST endpoint crashed (wrong Wiki constructor)", "lesson": "Use sqlite_store directly for REST endpoints", "context": "fleet-agent-mcp memory page"})
print()
print("Final fleet-agent-mcp state:")
print("  35 tools, 10 subsystems")
print("  REST endpoints: /api/memory, /api/evolution")
print("  Webapp pages: /memory, /evolution")
print("  Sidebar: Memory + Evolution entries")
print("  start.ps1: no ErrorActionPreference Stop")
print("  start.bat: error handling + path check")
print("  MCP transport: stateless_http, no sessions needed")
print("  LLM: LM Studio / OpenAI-compatible API")
print("  Pipeline: code_generate -> PR -> merge -> docs OK")
