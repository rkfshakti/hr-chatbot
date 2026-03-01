"""Data models for HR Chatbot"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system"""
    HR = "hr"
    TA = "ta"


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole


class ResumeMetadata(BaseModel):
    """Resume metadata stored in PageIndex"""
    candidate_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source_file: str
    uploaded_date: datetime
    uploaded_by: str
    skills: List[str] = []
    years_of_experience: Optional[int] = None
    education_level: Optional[str] = None
    current_role: Optional[str] = None


class JobDescription(BaseModel):
    """Job description analysis"""
    job_id: str
    title: str
    description: str
    required_skills: List[str] = []
    nice_to_have_skills: List[str] = []
    experience_years: Optional[int] = None
    must_have: List[str] = []
    certifications_required: List[str] = []
    created_at: datetime


class ResumeMatchResult(BaseModel):
    """Resume matching result"""
    candidate_name: str
    resume_id: str
    rank: int
    alignment_score: float
    required_skills_met: List[str] = []
    required_skills_missing: List[str] = []
    reasoning: str
    confidence: str          # "High" | "Medium" | "Low"
    source_file: str


class MatchResponse(BaseModel):
    """Response for resume matching"""
    job_id: str
    top_3_candidates: List[ResumeMatchResult]
    analysis_timestamp: datetime


class ChatMessage(BaseModel):
    """Chat message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ChatRequest(BaseModel):
    """Chat request"""
    job_description: Optional[str] = None
    message: str
    resume_file_ids: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class JDAnalysisResponse(BaseModel):
    """Job description analysis response"""
    job_id: str
    title: Optional[str] = None
    required_skills: List[str]
    nice_to_have_skills: List[str]
    experience_years: Optional[int] = None
    certifications_required: List[str]
    must_have_requirements: List[str]
    created_at: datetime


class JDAnalysisRequest(BaseModel):
    """Job description analysis request"""
    job_description: str
    job_title: Optional[str] = None


class InterviewInvite(BaseModel):
    """Interview invitation"""
    candidate_emails: List[EmailStr]
    google_meet_link: str
    job_id: str
    scheduled_time: Optional[datetime] = None
    message: Optional[str] = None
