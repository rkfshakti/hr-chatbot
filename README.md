# HR Chatbot - Agentic RAG Resume Matching System

## Overview

A full-stack HR recruitment solution using **Agentic RAG** to match resumes against job descriptions with explicit reasoning. This system uses:

- **Agentic RAG**: Multi-step reasoning agents that decompose job requirements and evaluate candidates with explanations
- **PageIndex**: Vector-less semantic indexing (no embeddings overhead)
- **Local LLM**: Self-hosted on `localhost:1234` for privacy and cost-efficiency
- **FastAPI**: Modern async Python backend
- **React**: Interactive frontend UI

## Key Features

✅ **Agentic Job Analysis** - Breaks down job descriptions into structured requirements
✅ **Smart Resume Matching** - Multi-step evaluation with explicit reasoning for each candidate
✅ **Multi-Format Parsing** - Handles PDF, DOCX, PPTX, and images (with OCR)
✅ **Vector-Less Indexing** - PageIndex stores resumes without embedding overhead
✅ **HR/TA Roles** - Separate authentication for HR and Talent Acquisition teams
✅ **Interview Invitations** - Send Google Meet links to top 3 candidates
✅ **Chat Interface** - Interactive dialog for job analysis and resume exploration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (3000)                    │
│  • Chat UI | Job Description Input | Results Display        │
└─────────────┬───────────────────────────────────────────────┘
              │ HTTP/WebSocket
┌─────────────▼───────────────────────────────────────────────┐
│                  FastAPI Backend (8000)                      │
│  • Auth (JWT) | Resume Parser | PageIndex Integration      │
└─────────────┬───────────────────────────────────────────────┘
              │
    ┌─────────┴──────────┬────────────────────┐
    ▼                    ▼                    ▼
┌─────────┐    ┌──────────────────┐   ┌─────────────┐
│PageIndex│    │  Local LLM       │   │SQLite Auth  │
│(Resumes)│    │localhost:1234    │   │Database     │
└─────────┘    └──────────────────┘   └─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- UV (Python package manager)
- Local LLM running on `localhost:1234` (model: `lfm2.5-1.2b-instruct`)
- Tesseract-OCR (for image resume parsing)

### Backend Setup

1. **Navigate to backend**:
   ```bash
   cd hr-chatbot/backend
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (LLM URL, etc.)
   ```

3. **Install dependencies with UV**:
   ```bash
   uv pip install -e .
   # Or for development:
   uv pip install -e "."
   ```

4. **Run FastAPI server**:
   ```bash
   uv run python -m uvicorn app:app --reload
   # Server runs on http://localhost:8000
   ```

### Frontend Setup

1. **Navigate to frontend**:
   ```bash
   cd hr-chatbot/frontend
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit if needed (API_URL should match backend)
   ```

3. **Install dependencies**:
   ```bash
   npm install
   ```

4. **Start dev server**:
   ```bash
   npm start
   # App opens at http://localhost:3000
   ```

## Verification & Testing

### Health Check

```bash
# Backend health check
curl http://localhost:8000/health
```

### Example API Calls

**1. Register User**:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "hr@company.com",
    "password": "secure123",
    "role": "hr",
    "full_name": "Jane Doe"
  }'
```

**2. Login**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "hr@company.com",
    "password": "secure123"
  }'
```

**3. Analyze Job Description**:
```bash
TOKEN="your_jwt_token_here"

curl -X POST http://localhost:8000/analyze-jd \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "job_description": "Looking for 5+ years Python developer with AWS expertise. Required: Python, AWS, Docker. Nice: Kubernetes, Terraform.",
    "job_title": "Senior Python Engineer"
  }'
```

**4. Match Resumes**:
```bash
curl -X POST http://localhost:8000/match-resumes \
  -H "Authorization: Bearer $TOKEN" \
  -d 'job_id=<job_id_from_previous_response>'
```

## Workflow

### User Journey

1. **Login**: HR/TA user logs in with email/password (JWT auth)
2. **Upload Resumes**: 
   - Drag & drop or click to upload resumes (.pdf, .docx, .pptx, images)
   - System parses and indexes in PageIndex
3. **Analyze Job Description**:
   - Paste or type job description
   - Agents decompose into skills, experience, certifications
4. **Match Resumes**:
   - System searches PageIndex with multi-step queries
   - Evaluates each candidate with explicit reasoning
   - Returns top 3 with scores and explanations
5. **Send Invites**:
   - Select candidates
   - Paste Google Meet link
   - Send interview invitations

### Agentic RAG Flow

```
Job Description
       ↓
  JD Analyzer Agent
       ↓
  ┌─────────────────────────┐
  │ Required Skills         │
  │ Experience Years        │
  │ Must-Have Requirements  │
  │ Certifications          │
  └─────────────┬───────────┘
                │
                ▼
        Resume Matcher Agent
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
  Query 1    Query 2     Query 3
  (Skills) (Experience) (Certs)
    │           │           │
    └─────┬─────┴─────┬─────┘
          ▼           ▼
     Retrieve    Retrieve
     Resumes     Resumes
          │           │
          └─────┬─────┘
                ▼
        Evaluate Each Candidate
        - Skills Met/Missing
        - Score (0-100)
        - Confidence
        - Reasoning
                │
                ▼
         Rank & Return Top 3
```

## Project Structure

```
hr-chatbot/
├── backend/
│   ├── pyproject.toml       # UV dependencies
│   ├── app.py              # FastAPI main app
│   ├── agents/
│   │   ├── jd_analyzer.py      # Job description analysis
│   │   └── resume_matcher.py   # Resume matching with reasoning
│   ├── parsers/
│   │   └── resume_parser.py    # Multi-format resume parser
│   ├── page_index/
│   │   └── index_manager.py    # PageIndex integration
│   ├── models/
│   │   ├── schemas.py          # Pydantic models
│   │   └── llm_client.py       # LLM client
│   ├── auth/
│   │   └── auth.py             # JWT authentication
│   └── data/
│       ├── pageindex/          # PageIndex storage
│       └── uploads/            # Uploaded resumes
│
├── frontend/
│   ├── package.json        # Node dependencies
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── api.js          # API client
│       ├── store.js        # Zustand state management
│       ├── App.js          # Main app
│       ├── components/
│       │   ├── Login.js       # Login/Register
│       │   ├── Chat.js        # Chat interface
│       │   └── Results.js     # Top 3 candidates display
│       └── pages/
│           └── Dashboard.js   # Main dashboard
│
└── docs/
    └── AGENTIC_RAG_DESIGN.md
```

## Configuration

### Backend (.env)

```env
# LLM Settings
LLM_API_URL=http://localhost:1234/api/v1/chat
LLM_MODEL=lfm2.5-1.2b-instruct
LLM_TIMEOUT=30

# Security
SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=sqlite:///./data/hr_chatbot.db

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (.env)

```env
REACT_APP_API_URL=http://localhost:8000
```

## Troubleshooting

### LLM Connection Failed
- Ensure local LLM is running: `curl http://localhost:1234/api/v1/chat`
- Check verbose mode: Add `DEBUG=True` to backend `.env`

### Resume Parsing Issues
- Install Tesseract: `brew install tesseract` (macOS) or `apt install tesseract-ocr` (Linux)
- Check file permissions in `data/uploads/`

### PageIndex Errors
- Ensure `data/pageindex/` directory is writable
- Check disk space for index storage

### CORS Issues
- Verify `CORS_ORIGINS` in backend `.env`
- Ensure frontend running on correct port (default 3000)

## API Documentation

Once backend is running, access Swagger UI at:
```
http://localhost:8000/docs
```

## Dependencies

### Backend
- **FastAPI**: Web framework
- **LangChain/LangGraph**: Agentic orchestration
- **PageIndex**: Vector-less indexing
- **python-docx, pypdf, pytesseract**: Document parsing
- **SQLAlchemy**: ORM
- **PyJWT**: JWT authentication

### Frontend
- **React 18**: UI framework
- **React Router**: Navigation
- **Axios**: HTTP client
- **Zustand**: State management
- **Tailwind CSS**: Styling

## Future Enhancements

- [ ] Google Calendar API integration for auto-generating meet links
- [ ] Microsoft Graph API for OneDrive auto-sync
- [ ] Email service (SendGrid/AWS SES) for interview invites
- [ ] Database migration from SQLite to PostgreSQL
- [ ] Webbrowser-based PDF preview
- [ ] Bulk resume upload from ZIP files
- [ ] Candidate pipeline tracking
- [ ] Performance analytics dashboard
- [ ] Custom evaluation scoring rubric

## License

Private project for HR recruitment

## Support

For issues or questions, contact the development team.
