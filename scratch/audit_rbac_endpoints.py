import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000"

roles = [
    ("No Header", None),
    ("admin", "admin"),
    ("reviewer", "reviewer"),
    ("sme_user", "sme_user"),
    ("invalid_role", "hacker"),
]

endpoints = [
    ("GET", "/health"),
    ("GET", "/regulations"),
    ("GET", "/evaluation/results"),
    ("GET", "/admin/reviews"),
    ("POST", "/admin/documents/upload"),
]

print("=== ROLE-BASED ACCESS CONTROL AUDIT ===")
for method, path in endpoints:
    print(f"\n--- Testing Endpoint: {method} {path} ---")
    for label, role in roles:
        headers = {}
        if role is not None:
            headers["X-User-Role"] = role
        
        req = urllib.request.Request(f"{base_url}{path}", headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                body_bytes = response.read()
                try:
                    body = json.loads(body_bytes.decode('utf-8'))
                    if isinstance(body, list):
                        detail = f" | returned {len(body)} items"
                    elif isinstance(body, dict):
                        detail = f" | keys: {list(body.keys())[:3]}"
                    else:
                        detail = f" | {body}"
                except Exception:
                    detail = f" | text: {body_bytes[:40]}"
                print(f"  [{label.ljust(12)}] Status: {status}{detail}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            detail = ""
            try:
                ej = json.loads(err_body)
                detail = f" | detail: {ej.get('detail')}"
            except Exception:
                detail = f" | body: {err_body[:60]}"
            print(f"  [{label.ljust(12)}] Status: {e.code}{detail}")
        except Exception as e:
            print(f"  [{label.ljust(12)}] Error: {e}")
