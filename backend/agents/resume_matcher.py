"""Resume Matcher Agent - Agentic RAG with Explicit Reasoning"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.llm_client import LLMClient
from models.schemas import ResumeMatchResult, MatchResponse, JDAnalysisResponse
from page_index.index_manager import PageIndexManager

logger = logging.getLogger(__name__)


class ResumeMatcher:
    """
    Multi-step agentic RAG for matching resumes to job descriptions
    
    Instead of simple similarity search, this agent:
    1. Breaks down JD into specific search queries
    2. Retrieves candidates for each requirement
    3. Evaluates each candidate with explicit reasoning
    4. Assigns confidence scores based on requirement matching
    5. Returns ranked list with explanations
    """
    
    def __init__(self, llm_client: LLMClient, index_manager: PageIndexManager):
        """
        Initialize Resume Matcher
        
        Args:
            llm_client: LLM client for reasoning
            index_manager: PageIndex manager for resume search
        """
        self.llm_client = llm_client
        self.index_manager = index_manager
    
    async def match_resumes(
        self,
        job_id: str,
        jd_analysis: JDAnalysisResponse,
        limit: int = 20
    ) -> List[ResumeMatchResult]:
        """
        Match resumes against job description using agentic reasoning
        
        Args:
            job_id: Job ID
            jd_analysis: Analyzed job description
            limit: Maximum resumes to retrieve and evaluate
            
        Returns:
            Ranked list of matching resumes with reasoning
        """
        logger.info(f"Starting agentic resume matching for job {job_id}")
        
        try:
            # Step 1: Search PageIndex with multiple queries
            candidates = await self._retrieve_candidates(jd_analysis, limit)
            
            if not candidates:
                logger.warning(f"No candidates found for job {job_id}")
                return []
            
            # Step 2: Evaluate each candidate with explicit reasoning
            evaluated = []
            for candidate in candidates:
                result = await self._evaluate_candidate(candidate, jd_analysis)
                if result:
                    evaluated.append(result)
            
            # Step 3: Rank based on alignment score
            ranked = sorted(evaluated, key=lambda x: x.alignment_score, reverse=True)
            
            # Add ranking
            for rank, result in enumerate(ranked, 1):
                result.rank = rank
            
            logger.info(f"Matching completed: {len(ranked)} candidates evaluated for {job_id}")
            return ranked
        except Exception as e:
            logger.error(f"Error matching resumes: {str(e)}")
            raise
    
    async def _retrieve_candidates(
        self,
        jd_analysis: JDAnalysisResponse,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidates from PageIndex using multiple search queries
        
        Strategy: Search for each skill separately, then combine results
        """
        all_candidates = {}
        
        # Search 1: Required skills
        logger.info(f"Searching for resumes with skills: {jd_analysis.required_skills}")
        for skill in jd_analysis.required_skills[:5]:  # Limit to top 5
            results = await self.index_manager.search_by_skills([skill], top_k=10)
            for result in results:
                resume_id = result.get('id')
                if resume_id not in all_candidates:
                    all_candidates[resume_id] = result
        
        # Search 2: Experience level
        if jd_analysis.experience_years:
            logger.info(f"Searching for candidates with {jd_analysis.experience_years}+ years experience")
            results = await self.index_manager.search_by_experience(
                min_years=jd_analysis.experience_years,
                top_k=10
            )
            for result in results:
                resume_id = result.get('id')
                if resume_id not in all_candidates:
                    all_candidates[resume_id] = result
        
        # Search 3: Nice-to-have skills
        if jd_analysis.nice_to_have_skills:
            logger.info(f"Searching for nice-to-have skills: {jd_analysis.nice_to_have_skills[:3]}")
            results = await self.index_manager.search_by_skills(
                jd_analysis.nice_to_have_skills[:3],
                top_k=5
            )
            for result in results:
                resume_id = result.get('id')
                if resume_id not in all_candidates:
                    all_candidates[resume_id] = result
        
        # Deduplicate by candidate name (keep highest-scored entry per name)
        seen_names: Dict[str, Dict[str, Any]] = {}
        for entry in all_candidates.values():
            name = entry.get('metadata', {}).get('candidate_name', '') or entry.get('id', '')
            existing = seen_names.get(name)
            if existing is None or entry.get('score', 0) > existing.get('score', 0):
                seen_names[name] = entry

        # Limit total results
        candidates = list(seen_names.values())[:limit]
        logger.info(f"Retrieved {len(candidates)} unique candidate resumes for evaluation")
        return candidates
    
    async def _evaluate_candidate(
        self,
        candidate: Dict[str, Any],
        jd_analysis: JDAnalysisResponse
    ) -> Optional[ResumeMatchResult]:
        """
        Evaluate a single candidate with explicit reasoning
        
        This is where Agentic RAG shines - LLM explains WHY a candidate
        matches or doesn't match requirements
        """
        resume_id = candidate.get('id')
        resume_text = candidate.get('content', '')
        metadata = candidate.get('metadata', {})
        candidate_name = metadata.get('candidate_name', 'Unknown')
        
        try:
            # Build evaluation prompt
            prompt = self._build_evaluation_prompt(resume_text, jd_analysis)
            
            # Get LLM evaluation with reasoning
            evaluation = await self.llm_client.chat(
                message=prompt,
                system_prompt="""You are an expert HR recruiter. Evaluate the candidate against job requirements.
For each requirement, state:
1. If candidate meets it (Yes/No/Partial)
2. Your confidence level (High/Medium/Low)
3. Brief reasoning

Format response as JSON with keys:
{
  "required_skills_met": ["skill1", "skill2"],
  "required_skills_missing": ["skill3"],
  "score": 85,
  "confidence": "High",
  "reasoning": "Candidate has X, missing Y, but..."
}"""
            )
            
            # Parse evaluation
            eval_data = self._parse_evaluation(evaluation)
            
            # Create result
            result = ResumeMatchResult(
                candidate_name=candidate_name,
                resume_id=resume_id,
                rank=0,  # Will be set after ranking
                alignment_score=eval_data.get('score', 0),
                required_skills_met=eval_data.get('required_skills_met', []),
                required_skills_missing=eval_data.get('required_skills_missing', []),
                reasoning=eval_data.get('reasoning', ''),
                confidence=eval_data.get('confidence', 'Low'),
                source_file=metadata.get('source_file', 'unknown')
            )
            
            logger.info(f"Evaluated {candidate_name}: score={result.alignment_score}, confidence={result.confidence}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating candidate {resume_id}: {str(e)}")
            return None
    
    def _build_evaluation_prompt(
        self,
        resume_text: str,
        jd_analysis: JDAnalysisResponse
    ) -> str:
        """Build the evaluation prompt for the LLM"""
        
        prompt = f"""Evaluate this candidate's fit for the following job requirements:

RESUME:
{resume_text[:2000]}  # Limit to first 2000 chars to avoid token explosion

JOB REQUIREMENTS:
Required Skills: {', '.join(jd_analysis.required_skills)}
Nice-to-Have Skills: {', '.join(jd_analysis.nice_to_have_skills)}
Experience Required: {jd_analysis.experience_years or 'Any'} years
Must-Have: {', '.join(jd_analysis.must_have_requirements)}
Certifications Required: {', '.join(jd_analysis.certifications_required)}

Please evaluate:
1. Which required skills are clearly mentioned in the resume?
2. Which required skills are missing?
3. Does candidate meet the experience requirement?
4. Are any certifications present?
5. Overall alignment score (0-100)
6. Your confidence in this evaluation

Provide reasoning for your assessment."""
        
        return prompt
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """Parse LLM evaluation response — handles markdown fences, type coercion."""
        import re

        # Strip markdown code fences
        fenced = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", evaluation_text)
        if fenced:
            evaluation_text = fenced.group(1)

        parsed = None
        json_start = evaluation_text.find('{')
        if json_start != -1:
            json_end = evaluation_text.rfind('}')
            if json_end != -1:
                try:
                    parsed = json.loads(evaluation_text[json_start:json_end+1])
                except json.JSONDecodeError:
                    pass

        if parsed:
            # Ensure score is numeric (LLM sometimes writes "High" in score field)
            raw_score = parsed.get('score', 0)
            if isinstance(raw_score, str):
                m = re.search(r'\d+', raw_score)
                raw_score = int(m.group()) if m else 50
            try:
                parsed['score'] = int(raw_score)
            except (ValueError, TypeError):
                parsed['score'] = 50
            return parsed

        return self._parse_evaluation_fallback(evaluation_text)
    
    def _parse_evaluation_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback evaluation parsing from free text"""
        import re
        
        result = {
            'required_skills_met': [],
            'required_skills_missing': [],
            'score': 50,
            'confidence': 'Medium',
            'reasoning': text[:500]
        }
        
        # Try to extract score
        score_match = re.search(r'(\d+)\s*(?:\/100|%|score)', text, re.IGNORECASE)
        if score_match:
            result['score'] = int(score_match.group(1))
        
        # Try to extract confidence
        if 'high' in text.lower():
            result['confidence'] = 'High'
        elif 'low' in text.lower():
            result['confidence'] = 'Low'
        
        return result


async def rank_and_format_results(
    matches: List[ResumeMatchResult],
    job_id: str
) -> MatchResponse:
    """
    Format matching results for API response
    
    Args:
        matches: List of match results
        job_id: Job ID
        
    Returns:
        Formatted response with top 3
    """
    # Get top 3
    top_3 = matches[:3]
    
    response = MatchResponse(
        job_id=job_id,
        top_3_candidates=top_3,
        analysis_timestamp=datetime.now()
    )
    
    return response
