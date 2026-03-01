"""
Main FastAPI application for HR Chatbot
Agentic RAG-based resume matching system
"""
import json
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.schemas import (
    UserRegister, UserLogin, TokenResponse, ChatRequest, ChatMessage,
    JDAnalysisResponse, JDAnalysisRequest, MatchResponse, InterviewInvite, ResumeMatchResult
)
from models.llm_client import LLMClient, LLMSettings
from parsers.resume_parser import ResumeParser
from page_index.index_manager import PageIndexManager
from agents.jd_analyzer import JDAnalyzerAgent
from agents.resume_matcher import ResumeMatcher, rank_and_format_results
from auth.auth import create_access_token, decode_token, get_password_hash, TokenData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
llm_client: Optional[LLMClient] = None
index_manager: Optional[PageIndexManager] = None
jd_analyzer: Optional[JDAnalyzerAgent] = None
resume_matcher: Optional[ResumeMatcher] = None

# In-memory storage (replace with DB in production)
users_db = {}  # {email: {password_hash, role, user_id}}
jobs_db = {}   # {job_id: JDAnalysisResponse}  — backed by disk
chat_history = {}  # {user_id: [ChatMessage]}

# ------------------------------------------------------------------
# Persistent jobs store helpers
# ------------------------------------------------------------------
_JOBS_STORE_PATH = "./data/jobs_store.json"


def _load_jobs_db():
    """Load persisted jobs from disk into jobs_db."""
    global jobs_db
    if os.path.exists(_JOBS_STORE_PATH):
        try:
            with open(_JOBS_STORE_PATH, "r") as f:
                raw = json.load(f)
            jobs_db = {
                jid: JDAnalysisResponse(**data)
                for jid, data in raw.items()
            }
            logger.info(f"Loaded {len(jobs_db)} jobs from disk.")
        except Exception as e:
            logger.warning(f"Could not load jobs store: {e}")
            jobs_db = {}


def _save_jobs_db():
    """Persist current jobs_db to disk."""
    try:
        os.makedirs("./data", exist_ok=True)
        payload = {
            jid: json.loads(jd.model_dump_json())
            for jid, jd in jobs_db.items()
        }
        with open(_JOBS_STORE_PATH, "w") as f:
            json.dump(payload, f)
    except Exception as e:
        logger.error(f"Could not save jobs store: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting HR Chatbot...")
    
    global llm_client, index_manager, jd_analyzer, resume_matcher
    
    try:
        # Initialize LLM client
        llm_settings = LLMSettings()
        llm_client = LLMClient(llm_settings)
        logger.info(f"LLM Client initialized: {llm_settings.llm_api_url}")
        
        # Initialize PageIndex
        index_manager = PageIndexManager(db_path="./data/pageindex")
        logger.info("PageIndex initialized")

        # Load persisted jobs
        _load_jobs_db()

        # Initialize agents
        jd_analyzer = JDAnalyzerAgent(llm_client)
        resume_matcher = ResumeMatcher(llm_client, index_manager)
        logger.info("Agents initialized")
        
        logger.info("HR Chatbot started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down HR Chatbot...")


# Create FastAPI app
app = FastAPI(
    title="HR Chatbot - Agentic RAG",
    description="Resume matching with explicit reasoning",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Get current user
async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """Extract and validate JWT token from header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        
        token_data = decode_token(token)
        if token_data is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return token_data
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


# ==================== Authentication Endpoints ====================

@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserRegister):
    """Register new user"""
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(user.password)
    
    users_db[user.email] = {
        "user_id": user_id,
        "password_hash": password_hash,
        "role": user.role,
        "full_name": user.full_name or user.email
    }
    
    access_token = create_access_token(user_id, user.email, user.role.value)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user_id,
        role=user.role
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user"""
    user = users_db.get(credentials.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    from auth.auth import verify_password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        user["user_id"],
        credentials.email,
        user["role"].value if hasattr(user["role"], "value") else user["role"]
    )
    
    return TokenResponse(
        access_token=access_token,
        user_id=user["user_id"],
        role=user["role"]
    )


# ==================== Resume Management ====================

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Upload and parse resume"""
    try:
        # Save uploaded file
        os.makedirs("./data/uploads", exist_ok=True)
        file_path = f"./data/uploads/{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse resume
        parser = ResumeParser()
        parsed_data = parser.parse_file(file_path)
        
        # Add to index (embedding-based vector store)
        resume_id = str(uuid.uuid4())
        await index_manager.add_resume(
            resume_id=resume_id,
            candidate_name=parsed_data['metadata'].get('candidate_name', 'Unknown'),
            raw_text=parsed_data['raw_text'],
            metadata=parsed_data['metadata'],
            source_file=file.filename
        )
        
        return {
            "resume_id": resume_id,
            "candidate_name": parsed_data['metadata'].get('candidate_name'),
            "status": "indexed",
            "metadata": parsed_data['metadata']
        }
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resumes")
async def list_resumes(current_user: TokenData = Depends(get_current_user)):
    """List all indexed resumes"""
    try:
        resumes = index_manager.list_all_resumes()
        return {
            "total": len(resumes),
            "resumes": resumes
        }
    except Exception as e:
        logger.error(f"Error listing resumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Job Analysis & Matching ====================

@app.post("/analyze-jd", response_model=JDAnalysisResponse)
async def analyze_job_description(
    request: JDAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Analyze job description and extract requirements"""
    try:
        job_id = str(uuid.uuid4())
        
        result = await jd_analyzer.analyze(job_id, request.job_description, request.job_title)
        
        # Store for later use (persisted to disk so it survives server reloads)
        jobs_db[job_id] = result
        _save_jobs_db()
        
        return result
    except Exception as e:
        logger.error(f"Error analyzing JD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/match-resumes", response_model=MatchResponse)
async def match_resumes(
    job_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Match resumes against analyzed job description
    Returns top 3 candidates with reasoning
    """
    try:
        if job_id not in jobs_db:
            raise HTTPException(status_code=404, detail="Job not found")
        
        jd_analysis = jobs_db[job_id]
        
        # Perform agentic RAG matching
        matches = await resume_matcher.match_resumes(job_id, jd_analysis, limit=20)
        
        # Format response with top 3
        response = await rank_and_format_results(matches, job_id)
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error matching resumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/top-3-results/{job_id}", response_model=List[ResumeMatchResult])
async def get_top_3_results(
    job_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get top 3 candidate results for a job"""
    try:
        if job_id not in jobs_db:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Re-run matching if needed
        jd_analysis = jobs_db[job_id]
        matches = await resume_matcher.match_resumes(job_id, jd_analysis, limit=20)
        
        return matches[:3]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Interview Management ====================

@app.post("/send-interview-invite")
async def send_interview_invite(
    invite: InterviewInvite,
    current_user: TokenData = Depends(get_current_user)
):
    """Send interview invitation to candidates"""
    try:
        # Log the invitation (email sending would go here)
        logger.info(f"Interview invitation sent: {invite.candidate_emails} - Google Meet: {invite.google_meet_link}")
        
        return {
            "status": "sent",
            "recipients": invite.candidate_emails,
            "google_meet_link": invite.google_meet_link,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending interview invite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat Interface ====================

@app.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Chat interface for HR/TA interaction"""
    try:
        # Initialize chat history for user if needed
        if current_user.user_id not in chat_history:
            chat_history[current_user.user_id] = []
        
        # If job description provided, analyze it
        if request.job_description:
            jd_analysis = await jd_analyzer.analyze(
                str(uuid.uuid4()),
                request.job_description
            )
            
            # Return analysis as response
            response_text = f"""Job Analysis Complete:
            
Required Skills: {', '.join(jd_analysis.required_skills)}
Experience: {jd_analysis.experience_years or 'Any'} years
Certifications: {', '.join(jd_analysis.certifications_required) or 'None'}
Must-Have: {', '.join(jd_analysis.must_have_requirements)}"""
        else:
            # Handle general chat messages
            response_text = await llm_client.chat(
                message=request.message,
                system_prompt="You are an HR assistant helping with recruitment and candidate evaluation."
            )
        
        # Store in history
        chat_history[current_user.user_id].append(
            ChatMessage(role="user", content=request.message, timestamp=datetime.now())
        )
        chat_history[current_user.user_id].append(
            ChatMessage(role="assistant", content=response_text, timestamp=datetime.now())
        )
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "componentsready": {
            "llm_client": llm_client is not None,
            "index_manager": index_manager is not None,
            "agents": jd_analyzer is not None and resume_matcher is not None
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
