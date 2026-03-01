"""LLM Client for interacting with local LLM service (OpenAI-compatible API)"""
import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Base URL shared by both LLM and embedding clients
_LLM_BASE = "http://192.168.68.113:1234"


class LLMSettings(BaseSettings):
    """LLM Configuration — reads from .env"""
    llm_api_url: str = f"{_LLM_BASE}/v1/chat/completions"
    llm_model: str = "google/gemma-3-4b"
    llm_timeout: int = 60
    embedding_api_url: str = f"{_LLM_BASE}/v1/embeddings"
    embedding_model: str = "text-embedding-mxbai-embed-large-v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


class LLMClient:
    """
    Client for local LLM using OpenAI-compatible /v1/chat/completions endpoint.
    Server: http://192.168.68.113:1234 (LM Studio / compatible runtime)
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or LLMSettings()
        self.base_url = self.settings.llm_api_url
        self.model = self.settings.llm_model
        self.timeout = self.settings.llm_timeout

    def _build_messages(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        return messages

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a chat message to the local LLM via OpenAI-compatible API.

        Args:
            message: User message text
            system_prompt: Optional system-level instruction
            context: Ignored (kept for backward-compatibility)

        Returns:
            LLM response text
        """
        messages = self._build_messages(message, system_prompt)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code != 200:
                logger.error(
                    f"LLM API error: {response.status_code} — {response.text[:300]}"
                )
                raise Exception(f"LLM API returned {response.status_code}")

            result = response.json()
            # OpenAI format: choices[0].message.content
            try:
                content = result["choices"][0]["message"]["content"]
                return content.strip()
            except (KeyError, IndexError, TypeError) as parse_err:
                logger.warning(
                    f"Unexpected LLM response shape ({parse_err}): {json.dumps(result)[:300]}"
                )
                return json.dumps(result)

        except httpx.ConnectError:
            host = self.base_url
            logger.error(f"Failed to connect to LLM at {host}")
            raise Exception(
                f"LLM service unavailable. Ensure it's running at {host}"
            )
        except Exception as e:
            logger.error(f"LLM chat error: {str(e)}")
            raise

    async def analyze_jd(self, job_description: str) -> str:
        """Analyze job description to extract requirements (JSON)."""
        system_prompt = (
            "You are an expert HR recruiter. "
            "Analyze the job description and extract key information. "
            "Reply ONLY with valid JSON — no markdown fences, no prose. "
            "JSON keys: required_skills (list), experience_years (int or null), "
            "must_have (list), nice_to_have (list)."
        )
        return await self.chat(
            message=f"Analyze this job description:\n\n{job_description}",
            system_prompt=system_prompt,
        )

    async def match_resume_to_jd(self, resume_text: str, jd_analysis: str) -> str:
        """Match resume against JD and return JSON scoring."""
        system_prompt = (
            "You are an expert HR recruiter evaluating candidates. "
            "Compare the resume against the job requirements. "
            "Reply ONLY with valid JSON — no markdown fences, no prose. "
            "JSON keys: score (int 0-100), skills_met (list), "
            "skills_missing (list), confidence (High/Medium/Low), reasoning (string)."
        )
        prompt = (
            f"Resume:\n{resume_text}\n\n"
            f"Job Requirements:\n{jd_analysis}\n\n"
            "Evaluate this candidate's fit."
        )
        return await self.chat(message=prompt, system_prompt=system_prompt)


class EmbeddingClient:
    """
    Client for generating text embeddings via OpenAI-compatible /v1/embeddings.
    Model: text-embedding-mxbai-embed-large-v1 (512-dim)
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        s = settings or LLMSettings()
        self.base_url = s.embedding_api_url
        self.model = s.embedding_model
        self.timeout = s.llm_timeout

    async def embed(self, text: str) -> List[float]:
        """
        Embed a single text string.

        Args:
            text: Input text (will be truncated to 512 tokens by the model)

        Returns:
            Embedding vector as list of floats
        """
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts in one API call.

        Args:
            texts: List of input strings

        Returns:
            List of embedding vectors
        """
        payload = {"model": self.model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            if response.status_code != 200:
                raise Exception(
                    f"Embedding API returned {response.status_code}: {response.text[:300]}"
                )
            result = response.json()
            # OpenAI format: data[i].embedding
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings
        except httpx.ConnectError:
            raise Exception(
                f"Embedding service unavailable at {self.base_url}"
            )
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            raise
