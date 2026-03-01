# Agentic RAG Design Document

## Overview

This document explains the **Agentic RAG** approach used in the HR Chatbot system and how it differs from traditional RAG systems.

## Traditional RAG vs Agentic RAG

### Traditional RAG Flow
```
User Input
    ↓
[Embed Query]
    ↓
[Vector Search]
    ↓
[Retrieve Top-K Documents]
    ↓
[Prompt LLM with Retrieved Docs]
    ↓
[Generate Response]
    ↓
Output (No explanation of reasoning)
```

**Problems**:
- Black-box ranking (why was candidate #1 selected?)
- Cannot enforce strict requirements
- Similarity-based matching can miss explicit skills
- No way to explain decisions to end users

---

### Agentic RAG Flow (Our Implementation)

```
User Input (Job Description)
    ↓
┌─────────────────────────────────┐
│  JD Analyzer Agent (Step 1)     │
│  - Parse job requirements       │
│  - Extract skills (required)    │
│  - Extract skills (nice-to-have)│
│  - Find certifications          │
│  - Determine exp years          │
│  - Identify must-haves          │
└──────────────┬──────────────────┘
               ↓
        [Job Profile Created]
               ↓
┌─────────────────────────────────────────────────────────┐
│  Resume Matcher Agent (Step 2) - Multi-turn Loop        │
│                                                         │
│  For Each Requirement:                                  │
│  1. Query PageIndex (skill-specific)                    │
│  2. Retrieve candidate batch                            │
│  3. LLM evaluates: "Does resume match this skill?"      │
│  4. Store confidence score                              │
│                                                         │
│  For Each Candidate (Retrieved):                        │
│  1. Calculate alignment score                           │
│  2. List met skills with confidence                     │
│  3. List missing skills with explanation                │
│  4. Generate reasoning: "Why rank #1?"                  │
│  5. Confidence: High/Medium/Low                         │
│                                                         │
└──────────────┬────────────────────────────────────────┘
               ↓
        [Ranked Candidates with Explanations]
               ↓
         Output to User
         - Top 3 candidates
         - Each with explicit reasoning
         - Skills met: ✓ Python (95% confident)
         - Skills missing: ✗ Kubernetes (not mentioned)
         - Decision logic visible to HR/TA teams
```

---

## Key Differences

| Aspect | Traditional RAG | Agentic RAG |
|--------|-----------------|------------|
| **Search Strategy** | Single vector search | Multi-step, skill-by-skill queries |
| **Explanation** | None | Explicit reasoning for each decision |
| **Requirement Mix** | All treated equally | Differentiates must-have vs nice-to-have |
| **Requirement Enforcement** | Cannot enforce hard constraints | Can reject candidates missing critical skills |
| **User Transparency** | Black box | Clear "why" for each ranking |
| **End-User Friendly** | Technical (similarity scores) | Business-friendly (readable explanations) |

---

## Implementation Details

### Step 1: JD Analyzer Agent

**Input**: Job Description Text

**Process**:
```python
class JDAnalyzerAgent:
    async def analyze(job_id, job_description):
        1. Use LLM to extract basic requirements
           → Responsibilities, Qualifications
        
        2. Extract technical skills
           → Required: Python, AWS, Docker
           → Nice-to-have: Kubernetes, Terraform
        
        3. Categorize requirements
           → Must-have (non-negotiable)
           → Nice-to-have (bonuses)
        
        4. Extract certifications
           → AWS Solutions Architect, CCNA, etc.
        
        5. Determine experience level
           → Parse "5+ years", "3-5 years"
        
        6. Return structured JDAnalysisResponse
```

**Output**:
```json
{
  "job_id": "uuid",
  "required_skills": ["python", "aws", "docker"],
  "nice_to_have_skills": ["kubernetes", "terraform"],
  "experience_years": 5,
  "must_have_requirements": ["Docker containerization", "AWS deployment"],
  "certifications_required": ["AWS Solutions Architect"],
  "created_at": "2026-03-01T..."
}
```

---

### Step 2: Resume Matcher Agent

**Input**: Analyzed Job Description + Indexed Resumes (in PageIndex)

**Process**:

```python
class ResumeMatcher:
    async def match_resumes(job_id, jd_analysis):
        # PHASE 1: Multi-Query Retrieval
        candidates = {}
        
        # Query 1: Search by skills
        for skill in jd_analysis.required_skills[:5]:
            results = pageindex.search(skill, limit=10)
            candidates.update(results)
        
        # Query 2: Search by experience
        results = pageindex.search_by_experience(
            min_years=jd_analysis.experience_years
        )
        candidates.update(results)
        
        # Query 3: Search nice-to-have skills
        for skill in jd_analysis.nice_to_have_skills[:3]:
            results = pageindex.search(skill, limit=5)
            candidates.update(results)
        
        # PHASE 2: Evaluate Each Candidate
        evaluated = []
        
        for candidate in candidates[:20]:  # Limit to top 20
            evaluation = await _evaluate_candidate(candidate, jd_analysis)
            evaluated.append(evaluation)
        
        # PHASE 3: Rank & Return
        ranked = sorted(evaluated, 
                       key=lambda x: x.alignment_score, 
                       reverse=True)
        
        return ranked[:3]  # Top 3
```

**Evaluation Logic**:
```python
async def _evaluate_candidate(candidate, jd_analysis):
    # Build comprehensive prompt
    prompt = f"""
    Resume: {candidate.content}
    
    Required Skills: {jd_analysis.required_skills}
    Experience Years Needed: {jd_analysis.experience_years}
    Must-Have: {jd_analysis.must_have_requirements}
    
    Evaluate:
    1. Which required skills are present?
    2. Which are missing?
    3. Does candidate meet experience?
    4. Are certifications present?
    5. Overall fit score (0-100)
    6. Your reasoning
    """
    
    # LLM evaluates with reasoning
    llm_response = await llm_client.chat(
        message=prompt,
        system_prompt="You are an expert HR recruiter evaluating candidates..."
    )
    
    # Parse response into structured evaluation
    return ResumeMatchResult(
        candidate_name=candidate.name,
        alignment_score=extracted_score,
        required_skills_met=[...],
        required_skills_missing=[...],
        reasoning=llm_response,
        confidence="High/Medium/Low"
    )
```

---

## Why This is "Agentic"

### Agent Characteristics:

1. **Goal-Oriented**: Agent has clear goal: "Find best resume match"
2. **Reasoning Steps**: Agent breaks problem into steps (analyze → search → evaluate)
3. **Tool Usage**: Agent uses tools:
   - `search_by_skills` - PageIndex semantic search
   - `evaluate_candidate` - LLM reasoning
   - `score_alignment` - Calculation tool
4. **Interactive**: Agent can:
   - Adjust search strategy if no results
   - Re-query with different keywords
   - Refine evaluation based on context
5. **Observable**: Every step is logged and explainable

### Multi-Turn Reasoning:

Unlike simple RAG (single query → retrieve → answer), Agentic RAG:
- **Turn 1**: Analyze job description → Extract requirements
- **Turn 2**: Multi-query search → Retrieve candidates
- **Turn 3**: Evaluate each candidate → Score and reason
- **Turn 4**: Rank and explain → Return top 3 with reasoning

---

## Example: Candidate Evaluation

**Job Description**:
```
Senior Python Engineer - 5+ years
Skills: Python (required), AWS (required), Kubernetes (nice-to-have)
Certifications: AWS Solutions Architect (required)
```

**Candidate Resume** (Parsed):
```
Skills: Python, Docker, AWS, Terraform
Experience: 6 years
Certifications: AWS Developer (not Solutions Architect)
```

**Traditional RAG Output**:
```
Candidate #1: Similarity Score 0.87
[No explanation why]
```

**Agentic RAG Output**:
```
Candidate Name: John Doe
Alignment Score: 78/100
Confidence: Medium

✓ Skills Met (with confidence):
  - Python (95% confident) - "6 years professional experience"
  - AWS (85% confident) - "AWS projects mentioned"

✗ Skills Missing (with explanation):
  - Kubernetes - "Not mentioned in resume. Resume mentions Docker/containerization but no Kubernetes orchestration."

⚠️ Certification Gap:
  - Required: AWS Solutions Architect
  - Has: AWS Developer (different cert, lower qualification level)

📊 Ranking Reason:
"This candidate is strong technically with 6+ years experience in Python and AWS. 
However, missing Kubernetes experience and doesn't have the required AWS Solutions 
Architect certification (has Developer instead). Would recommend interview but may 
need to assess Kubernetes learning curve."

Decision: Rank #2 (Good candidate, but missing critical certification)
```

---

## Confidence Scoring

Agents assign confidence levels based on evidence:

```python
confidence_levels = {
    "High": {
        "score_range": (80, 100),
        "meaning": "Clear evidence of skill/requirement",
        "example": "Resume explicitly states 'AWS certified Solutions Architect'"
    },
    "Medium": {
        "score_range": (60, 79),
        "meaning": "Probable but not explicitly stated",
        "example": "Resume shows Docker/Kubernetes projects but doesn't mention Kubernetes explicitly"
    },
    "Low": {
        "score_range": (0, 59),
        "meaning": "Partial or inferred",
        "example": "Mentions cloud but no specific AWS details"
    }
}
```

---

## PageIndex Integration (Vector-Less)

Traditional RAG uses dense vectors (embeddings):
```
Embedding process: "Python developer" → [0.23, 0.45, -0.12, ...]  (1536 dims)
Cost: Embedding API calls, storage, query latency
```

PageIndex (our solution):
```
Direct semantic indexing: "Python developer" → Direct semantic match
No embeddings needed!
Cost: O(1), Privacy: On-premises
```

**Benefits**:
- No embedding API costs (no token exhaustion)
- Privacy: Resumes stay local (not sent to external APIs)
- Speed: Direct semantic search without embedding round-trip
- Scalability: Can index unlimited resumes

---

## Code Flow Example

### Resume Upload → Index Flow
```python
# 1. User uploads resume.pdf
file = UploadFile(filename="john_doe.pdf")

# 2. Parse resume
parser = ResumeParser()
parsed = parser.parse_file(file)
# Returns: raw_text, metadata (name, skills, experience, etc.)

# 3. Add to PageIndex
index_manager.add_resume(
    resume_id="uuid-123",
    candidate_name="John Doe",
    raw_text="John Doe...[full resume text]",
    metadata={
        "skills": ["python", "aws", "docker"],
        "years_of_experience": 6,
        "current_role": "Senior Engineer"
    }
)
# PageIndex now indexes this resume for semantic search

# 4. When job comes in, agents search for matches
results = index_manager.search_by_skills(["python", "aws"], top_k=10)
# Returns: [John Doe's resume, ...other resumes...]
```

### Job Analysis → Matching Flow
```python
# 1. User provides job description
jd = "Looking for 5+ years Python developer with AWS..."

# 2. JD Analyzer breaks it down
jd_analysis = await jd_analyzer.analyze(
    job_id="job-456",
    job_description=jd
)
# Returns structured requirements

# 3. Resume Matcher evaluates candidates
matches = await resume_matcher.match_resumes(
    job_id="job-456",
    jd_analysis=jd_analysis
)

# 4. Each match has explicit reasoning
for match in matches[:3]:
    print(f"{match.candidate_name}: {match.alignment_score}%")
    print(f"Reasoning: {match.reasoning}")
    print(f"Met: {match.required_skills_met}")
    print(f"Missing: {match.required_skills_missing}")
```

---

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Explainability** | HR teams understand why candidates ranked certain way |
| **Accuracy** | Multi-step reasoning catches nuances |
| **Flexibility** | Can enforce hard constraints (must-have = dealbreaker) |
| **Scalability** | PageIndex handles unlimited resumes without vector limits |
| **Cost** | No embedding API costs, privacy-first design |
| **Trust** | End-users trust decisions they can see and understand |

---

## Future Enhancements

1. **Learning**: Store feedback (hired = good match, rejected = bad match) to fine-tune scoring
2. **Feedback Loop**: Use hiring outcomes to improve JD analyzer
3. **Multi-stage**: Add screening questions, coding challenges as additional agent stages
4. **Parallel Agents**: Run multiple evaluations in parallel for faster processing
5. **Custom Rubrics**: Let HR teams define custom evaluation criteria per company

---

## References

- **LangChain**: Agentic orchestration framework
- **PageIndex**: Vector-less semantic indexing
- **Multi-Agent Systems**: Reasoning, Planning, and Acting
