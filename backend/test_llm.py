"""
LLM + Embedding Reachability Test
Run from backend/ directory:
    python test_llm.py
"""
import asyncio
import json
import time
import httpx

BASE = "http://192.168.68.113:1234"
CHAT_URL = f"{BASE}/v1/chat/completions"
EMBED_URL = f"{BASE}/v1/embeddings"
MODELS_URL = f"{BASE}/api/v1/models"

CHAT_MODEL = "google/gemma-3-4b"
EMBED_MODEL = "text-embedding-mxbai-embed-large-v1"


def _ok(label: str, duration: float, detail: str = ""):
    tag = detail[:80] if detail else ""
    print(f"  ✅  {label:<30} ({duration:.2f}s)  {tag}")


def _fail(label: str, err: str):
    print(f"  ❌  {label:<30} ERROR: {err[:120]}")


async def test_models():
    """List loaded models."""
    t = time.time()
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(MODELS_URL)
        r.raise_for_status()
        data = r.json()
        loaded = [m["id"] for m in data.get("models", []) if m.get("state") == "loaded"]
        _ok("GET /api/v1/models", time.time() - t, f"loaded={loaded}")
        return True
    except Exception as e:
        _fail("GET /api/v1/models", str(e))
        return False


async def test_chat():
    """Send a short chat completion request."""
    t = time.time()
    payload = {
        "model": CHAT_MODEL,
        "messages": [{"role": "user", "content": "Reply with exactly one word: ready"}],
        "max_tokens": 10,
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(CHAT_URL, json=payload, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        _ok("POST /v1/chat/completions", time.time() - t, f"response='{content}'")
        return True
    except Exception as e:
        _fail("POST /v1/chat/completions", str(e))
        return False


async def test_embeddings():
    """Get embedding vector for a short text."""
    t = time.time()
    payload = {
        "model": EMBED_MODEL,
        "input": "Python developer with FastAPI experience",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(EMBED_URL, json=payload, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        vec = r.json()["data"][0]["embedding"]
        _ok("POST /v1/embeddings", time.time() - t, f"dim={len(vec)} first={vec[0]:.4f}")
        return True
    except Exception as e:
        _fail("POST /v1/embeddings", str(e))
        return False


async def test_jd_extraction():
    """Test LLM JSON extraction for a mock JD."""
    t = time.time()
    system = (
        "You are an expert HR recruiter. "
        "Extract key info from the job description. "
        "Reply ONLY with valid JSON, no markdown. "
        "Keys: required_skills (list), experience_years (int or null), "
        "must_have (list), nice_to_have (list)."
    )
    jd = (
        "We are hiring a Senior Python Engineer with 5+ years experience. "
        "Must know: FastAPI, PostgreSQL, Docker, AWS. "
        "Nice to have: Kubernetes, Apache Kafka. "
        "Must have prior experience at a startup."
    )
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Analyze this JD:\n{jd}"},
        ],
        "max_tokens": 512,
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(CHAT_URL, json=payload, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw)
        skills = parsed.get("required_skills", [])
        _ok("JD extraction (JSON parse)", time.time() - t, f"required_skills={skills[:3]}")
        return True
    except json.JSONDecodeError as e:
        _fail("JD extraction (JSON parse)", f"JSON error — raw: {raw[:120]}")
        return False
    except Exception as e:
        _fail("JD extraction", str(e))
        return False


async def main():
    print(f"\n{'='*60}")
    print(f"  HR Chatbot — LLM Reachability Test")
    print(f"  Target: {BASE}")
    print(f"{'='*60}\n")

    results = await asyncio.gather(
        test_models(),
        test_chat(),
        test_embeddings(),
        test_jd_extraction(),
    )

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Result: {passed}/{total} tests passed")
    if passed == total:
        print("  🎉  All systems go!")
    else:
        print("  ⚠️   Some services need attention.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
