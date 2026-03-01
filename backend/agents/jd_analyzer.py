"""Job Description Analyzer Agent - Agentic RAG"""
import json
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from models.llm_client import LLMClient
from models.schemas import JDAnalysisResponse

logger = logging.getLogger(__name__)


def _parse_json(text: str, default: Any = None) -> Any:
    """
    Robustly extract JSON from LLM output.
    Handles markdown code fences (```json ... ```) and leading prose.
    """
    if not text:
        return default
    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fenced:
        text = fenced.group(1)
    # Find first { or [
    obj_start = text.find('{')
    arr_start = text.find('[')
    if obj_start == -1 and arr_start == -1:
        return default
    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        start = arr_start
    else:
        start = obj_start
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        # Try to find a closed JSON substring
        for end in range(len(text), start, -1):
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
    return default


class JDAnalyzerAgent:
    """
    Analyzes job descriptions to extract structured requirements
    Part of Agentic RAG system
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize JD Analyzer
        
        Args:
            llm_client: LLMClient instance for calling local LLM
        """
        self.llm_client = llm_client
    
    async def analyze(self, job_id: str, job_description: str, job_title: Optional[str] = None) -> JDAnalysisResponse:
        """
        Analyze job description to extract requirements
        
        This is the first step in Agentic RAG - decomposing the JD into
        structured requirements that will be used to match resumes
        
        Args:
            job_id: Unique job ID
            job_description: Full job description text
            job_title: Job title (optional)
            
        Returns:
            Structured job analysis
        """
        logger.info(f"Starting JD analysis for job {job_id}")
        
        try:
            # Step 1: Extract basic requirements using LLM
            basic_requirements = await self._extract_basic_requirements(job_description)
            
            # Step 2: Analyze technical requirements
            technical_requirements = await self._extract_technical_skills(job_description)
            
            # Step 3: Identify must-have vs nice-to-have
            categorized = await self._categorize_requirements(
                job_description,
                basic_requirements,
                technical_requirements
            )
            
            # Step 4: Extract certifications if any
            certifications = await self._extract_certifications(job_description)
            
            # Step 5: Determine experience level
            experience_years = self._extract_experience_years(job_description)
            
            logger.info(f"JD analysis completed for {job_id}")
            
            return JDAnalysisResponse(
                job_id=job_id,
                title=job_title,
                required_skills=technical_requirements.get('required_skills', []),
                nice_to_have_skills=technical_requirements.get('nice_to_have', []),
                experience_years=experience_years,
                certifications_required=certifications,
                must_have_requirements=categorized.get('must_have', []),
                created_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error analyzing JD {job_id}: {str(e)}")
            raise
    
    async def _extract_basic_requirements(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract basic requirements from JD
        
        Uses LLM to understand key requirements
        """
        prompt = f"""Analyze this job description and extract key requirements.
        
Job Description:
{jd_text}

Please identify and list:
1. Main job responsibilities (top 3)
2. Key qualifications required
3. Preferred qualifications
4. Any specific measurements or achievements mentioned

Format as JSON with keys: main_responsibilities, key_qualifications, preferred_qualifications, achievements"""
        
        try:
            response = await self.llm_client.chat(
                message=prompt,
                system_prompt="You are an HR expert analyzing job descriptions. Extract structured information."
            )
            
            parsed = _parse_json(response, default={})
            return parsed if parsed else {"raw_response": response}
        except Exception as e:
            logger.error(f"Error extracting basic requirements: {e}")
            return {}
    
    async def _extract_technical_skills(self, jd_text: str) -> Dict[str, List[str]]:
        """
        Extract technical skills from JD
        """
        prompt = f"""From this job description, extract ALL technical skills mentioned:

Job Description:
{jd_text}

List skills separately as:
REQUIRED SKILLS:
- skill 1
- skill 2
...

NICE-TO-HAVE SKILLS:
- skill 1
- skill 2
...

Format your response as JSON with keys: required_skills, nice_to_have (both as lists)"""
        
        try:
            response = await self.llm_client.chat(
                message=prompt,
                system_prompt="You are a technical recruiter. Identify all programming languages, frameworks, tools, and platforms mentioned."
            )
            
            # Parse JSON (handles markdown fences)
            parsed = _parse_json(response)
            if parsed:
                return parsed
            # Fallback: extract skills using simple parsing
            return self._parse_skills_from_text(response)
        except Exception as e:
            logger.error(f"Error extracting technical skills: {e}")
            return {"required_skills": [], "nice_to_have": []}
    
    async def _categorize_requirements(
        self,
        jd_text: str,
        basic_reqs: Dict,
        tech_skills: Dict
    ) -> Dict[str, List[str]]:
        """
        Categorize requirements as must-have vs nice-to-have
        """
        must_have_keywords = ['must', 'required', 'essential', 'mandatory', 'critical']
        nice_to_have_keywords = ['prefer', 'nice to have', 'ideal', 'beneficial', 'bonus']
        
        prompt = f"""Categorize these requirements as MUST-HAVE (non-negotiable) vs NICE-TO-HAVE:

Job Description:
{jd_text}

Required Skills: {', '.join(tech_skills.get('required_skills', []))}
Nice-to-Have Skills: {', '.join(tech_skills.get('nice_to_have', []))}

Return JSON with keys: must_have (list), nice_to_have (list)
Only include critical requirements in must_have."""
        
        try:
            response = await self.llm_client.chat(
                message=prompt,
                system_prompt="You are an HR recruiting expert. Identify absolute requirements vs preferred qualifications."
            )
            
            parsed = _parse_json(response, default={})
            return parsed if parsed else {"must_have": [], "nice_to_have": []}
        except Exception as e:
            logger.error(f"Error categorizing requirements: {e}")
            return {"must_have": [], "nice_to_have": []}
    
    async def _extract_certifications(self, jd_text: str) -> List[str]:
        """
        Extract required certifications
        """
        prompt = f"""From this job description, extract all certifications, licenses, or qualifications mentioned:

Job Description:
{jd_text}

Return as JSON array: ["cert1", "cert2", ...]
Only return certifications explicitly mentioned, not implied technologies."""
        
        try:
            response = await self.llm_client.chat(
                message=prompt,
                system_prompt="You are a certification specialist. Identify formal certifications and licenses."
            )
            
            result = _parse_json(response, default=[])
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error extracting certifications: {e}")
            return []
    
    def _extract_experience_years(self, jd_text: str) -> Optional[int]:
        """
        Extract years of experience requirement
        """
        import re
        
        # Look for patterns like "5+ years", "5-10 years", "minimum 5 years"
        patterns = [
            r'(\d+)\+\s*years',
            r'(\d+)\s*-\s*(\d+)\s*years',
            r'at least \d+ years',
            r'minimum\s+(\d+)\s*years',
        ]
        
        text_lower = jd_text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                if isinstance(matches[0], tuple):
                    return int(matches[0][0]) if matches[0][0] else None
                else:
                    return int(matches[0])
        
        return None
    
    def _parse_skills_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Fallback: parse skills from text response
        """
        required = []
        nice_to_have = []
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'required' in line.lower():
                current_section = 'required'
            elif 'nice' in line.lower() or 'prefer' in line.lower():
                current_section = 'nice_to_have'
            elif line.startswith('-') or line.startswith('•'):
                skill = line.lstrip('-•').strip()
                if skill:
                    if current_section == 'required':
                        required.append(skill)
                    else:
                        nice_to_have.append(skill)
        
        return {
            "required_skills": required or next(iter(text.split(',')[:5]), []),
            "nice_to_have": nice_to_have
        }
