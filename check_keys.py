from pathlib import Path
import httpx

lines = Path('backend/.env').read_text(encoding='utf-8').splitlines()
gemini_key = None
openai_key = None

for line in lines:
    clean = line.strip().lstrip('#').strip()
    if clean.startswith('GEMINI_API_KEY='):
        gemini_key = clean.split('=', 1)[1].strip()
    elif clean.startswith('OPENAI_API_KEY='):
        openai_key = clean.split('=', 1)[1].strip()

print(f"Gemini key present in .env file: {gemini_key is not None}")
print(f"OpenAI key present in .env file: {openai_key is not None}")

if openai_key:
    print("Testing OpenAI API credentials...")
    try:
        r = httpx.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {openai_key}"}, timeout=10.0)
        print(f"OpenAI /models endpoint response: HTTP {r.status_code}")
        if r.status_code == 200:
            print("OpenAI authentication: SUCCESS (HTTP 200)")
        else:
            err_json = r.json().get("error", {})
            print(f"OpenAI error category: {err_json.get('type')}, code: {err_json.get('code')}")
            print(f"OpenAI message: {err_json.get('message')}")
    except Exception as exc:
        print(f"OpenAI request exception: {type(exc).__name__}: {exc}")

if gemini_key:
    print("\nTesting Gemini API credentials...")
    try:
        r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}", timeout=10.0)
        print(f"Gemini /models endpoint response: HTTP {r.status_code}")
        if r.status_code == 200:
            print("Gemini authentication: SUCCESS (HTTP 200)")
        else:
            err_json = r.json().get("error", {})
            print(f"Gemini error status: {err_json.get('status')}")
            print(f"Gemini message: {err_json.get('message')}")
    except Exception as exc:
        print(f"Gemini request exception: {type(exc).__name__}: {exc}")
