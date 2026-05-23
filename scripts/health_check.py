"""Fritz health check."""
import httpx, json

r = httpx.get("http://127.0.0.1:10996/api/whoami", timeout=5)
print(f"Fritz says: {r.json()['name']}")

r = httpx.get("http://127.0.0.1:10996/api/tools", timeout=5)
t = r.json()
print(f"Tools: {t['total']} across {len(t['subsystems'])} subsystems")

init = {
    "jsonrpc": "2.0", "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    },
    "id": 1,
}
r = httpx.post(
    "http://127.0.0.1:10996/mcp/",
    json=init,
    headers={"Accept": "application/json, text/event-stream"},
    timeout=10,
)
print(f"MCP init: HTTP {r.status_code}")
print(f"Response: {r.text[:300]}")
