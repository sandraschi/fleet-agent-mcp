"""Call fritz_contribute and show raw response."""
import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"
p = {"jsonrpc":"2.0","method":"tools/call","params":{"name":"fritz_contribute","arguments":{"repo_url":"https://github.com/StephanSchipal/edge-bookmark-mcp-server","dry_run":False}},"id":1}

print("Calling Fritz...")
r = httpx.post(url, json=p, headers=H, timeout=300)
print(f"HTTP {r.status_code}")
print(f"Raw ({len(r.text)} chars):")
print(r.text[:2000])
