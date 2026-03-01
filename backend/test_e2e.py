"""End-to-end integration test for HR Chatbot"""
import asyncio
import json
import time
import httpx

BASE = "http://localhost:8000"
TOKEN_CACHE = {}


async def login(email: str = "sarah@hrteam.com", password: str = "password123"):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        # Try register first
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{BASE}/auth/register", json={
                "email": email, "password": password,
                "full_name": "Sarah HR", "role": "hr"
            })
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    data = r.json()
    return data["access_token"]


async def upload_resume(token: str, file_path: str):
    with open(file_path, "rb") as f:
        content = f.read()
    filename = file_path.split("/")[-1]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{BASE}/upload-resume",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, content, "text/plain")},
        )
    return r.json()


async def analyze_jd(token: str, jd_text: str, title: str = "Senior Python Engineer"):
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(
            f"{BASE}/analyze-jd",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "job_description": jd_text,
                "job_title": title
            },
        )
    return r.json()


async def match_resumes(token: str, job_id: str):
    async with httpx.AsyncClient(timeout=360) as c:
        r = await c.post(
            f"{BASE}/match-resumes",
            headers={"Authorization": f"Bearer {token}"},
            params={"job_id": job_id},
        )
    return r.json()


SAMPLE_JD = """
We are looking for a Senior Python Engineer with 5+ years of experience.

Must have:
- Python (advanced)
- FastAPI or Django (REST API development)
- PostgreSQL (database design, query optimization)
- Docker and Kubernetes
- AWS (EC2, S3, RDS)

Nice to have:
- Kafka or Redis
- CI/CD experience
- Team lead / mentorship experience

This is a backend-focused role building high-throughput microservices.
"""

RESUME_FILES = [
    "/tmp/resume_alice.txt",
    "/tmp/resume_bob.txt",
    "/tmp/resume_carol.txt",
]


async def main():
    print(f"\n{'='*60}")
    print("  HR Chatbot — End-to-End Integration Test")
    print(f"{'='*60}\n")

    # Step 1: Login
    print("Step 1: Authenticating...")
    t = time.time()
    token = await login()
    print(f"  ✅  Login OK ({time.time()-t:.2f}s)\n")

    # Step 2: Upload resumes
    print("Step 2: Uploading & indexing resumes...")
    for path in RESUME_FILES:
        t = time.time()
        result = await upload_resume(token, path)
        if "resume_id" in result:
            name = result.get("candidate_name", "?")
            skills = result.get("metadata", {}).get("skills", [])[:3]
            print(f"  ✅  {path.split('/')[-1]:<22} → {name:<15} skills={skills} ({time.time()-t:.2f}s)")
        else:
            print(f"  ❌  {path.split('/')[-1]}: {result}")
    print()

    # Step 3: Analyze JD
    print("Step 3: Analyzing job description...")
    t = time.time()
    jd_result = await analyze_jd(token, SAMPLE_JD)
    if "job_id" in jd_result:
        job_id = jd_result["job_id"]
        skills = jd_result.get("required_skills", [])
        must = jd_result.get("must_have_requirements", [])
        print(f"  ✅  JD analyzed — job_id={job_id[:8]}... ({time.time()-t:.2f}s)")
        print(f"      required_skills: {skills[:5]}")
        print(f"      must_have:        {must[:3]}")
    else:
        print(f"  ❌  JD analysis failed: {json.dumps(jd_result)[:200]}")
        return
    print()

    # Step 4: Match resumes
    print("Step 4: Matching resumes to JD (agentic RAG)...")
    t = time.time()
    match_result = await match_resumes(token, job_id)
    elapsed = time.time() - t

    # Normalise: list, dict["matches"], or dict["top_3_candidates"]
    matches = None
    if isinstance(match_result, list):
        matches = match_result
    elif isinstance(match_result, dict):
        matches = (match_result.get("matches")
                   or match_result.get("top_3_candidates")
                   or match_result.get("candidates"))

    if matches:
        print(f"  ✅  Got {len(matches)} matches ({elapsed:.2f}s)\n")
        for i, m in enumerate(matches, 1):
            name  = m.get("candidate_name") or m.get("name") or "?"
            score = m.get("alignment_score") or m.get("score", 0)
            reasoning = m.get("reasoning", "")[:80]
            print(f"  #{i}: {name:<20} score={score}  reason='{reasoning}...'")
    else:
        print(f"  ⚠️  Unexpected match result: {json.dumps(match_result)[:400]}")

    print(f"\n{'='*60}")
    print("  End-to-end test complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
