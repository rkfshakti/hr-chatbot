"""Debug script: trace _retrieve_candidates and _evaluate_candidate"""
import asyncio
import sys
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

sys.path.insert(0, '.')
from models.llm_client import LLMClient
from page_index.index_manager import PageIndexManager
from models.schemas import JDAnalysisResponse
from agents.resume_matcher import ResumeMatcher


async def test():
    llm = LLMClient()
    mgr = PageIndexManager()
    matcher = ResumeMatcher(llm, mgr)

    jd = JDAnalysisResponse(
        job_id='test-001',
        title='Senior Python Engineer',
        required_skills=['Python', 'FastAPI', 'PostgreSQL', 'Docker'],
        nice_to_have_skills=['Kubernetes', 'Redis'],
        experience_years=5,
        certifications_required=[],
        must_have_requirements=['Python advanced', 'FastAPI experience'],
        created_at=__import__('datetime').datetime.now(),
    )

    print(f"\n=== Step 1: Retrieve candidates ===")
    candidates = await matcher._retrieve_candidates(jd, limit=5)
    print(f"Retrieved {len(candidates)} candidates")
    for c in candidates[:3]:
        name = c.get("metadata", {}).get("candidate_name", "?")
        cid = c.get("id", "?")[:10]
        print(f"  {name!r} id={cid}")

    if not candidates:
        print("ERROR: No candidates returned from vector store!")
        return

    print(f"\n=== Step 2: Evaluate first candidate ===")
    candidate = candidates[0]
    name = candidate.get("metadata", {}).get("candidate_name", "?")
    print(f"Evaluating: {name}")

    result = await matcher._evaluate_candidate(candidate, jd)
    if result:
        print(f"  Score: {result.alignment_score}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Skills met: {result.required_skills_met}")
        print(f"  Reasoning: {result.reasoning[:80]}")
    else:
        print("  EVALUATION RETURNED NONE!")

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(test())
