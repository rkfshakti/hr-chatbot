# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

- [ ] Python 3.10+ (`python --version`)
- [ ] Node.js 18+ (`node --version`)
- [ ] UV installed (`uv --version` or `pip install uv`)
- [ ] Local LLM running on `localhost:1234`
- [ ] Tesseract OCR installed (`tesseract --version`)

## Step 1: Setup Backend

### 1.1 Navigate to backend
```bash
cd hr-chatbot/backend
```

### 1.2 Copy environment file
```bash
cp .env.example .env
```

### 1.3 Edit .env (optional)
```bash
# Only change if your LLM is on a different URL
LLM_API_URL=http://localhost:1234/api/v1/chat
LLM_MODEL=lfm2.5-1.2b-instruct
```

### 1.4 Install dependencies with UV
```bash
uv pip install -e .
```

If you get errors about missing packages:
```bash
uv pip install langchain langgraph fastapi uvicorn pydantic httpx python-docx pypdf pdf2image pytesseract python-pptx
```

### 1.5 Create data directories
```bash
mkdir -p data/pageindex data/uploads
```

### 1.6 Run backend server
```bash
uv run python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

✅ **Backend is ready!** Open http://localhost:8000/docs for API docs.

---

## Step 2: Setup Frontend

### 2.1 In a NEW terminal, navigate to frontend
```bash
cd hr-chatbot/frontend
```

### 2.2 Copy environment file
```bash
cp .env.example .env
```

### 2.3 Install dependencies
```bash
npm install
```

This may take 2-3 minutes.

### 2.4 Start dev server
```bash
npm start
```

Expected output:
```
webpack compiled successfully
Compiled successfully!

You can now view hr-chatbot-frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

✅ **Frontend is ready!** Browser should auto-open at http://localhost:3000

---

## Step 3: Test the System

### 3.1 Create an account
1. Go to http://localhost:3000
2. Click "Sign Up"
3. Enter:
   - Email: `hr@example.com`
   - Password: `test123456` (minimum 8 chars)
   - Role: `HR` or `Talent Acquisition`
   - Full Name: `Test User`
4. Click "Sign Up"

### 3.2 Test with a sample job
In the Chat tab:
1. Click the "📄" button (Add Job Description)
2. Paste this job description:
   ```
   Senior Python Developer
   
   We're looking for an experienced Python developer with 5+ years of professional experience.
   
   Required Skills:
   - Python (5+ years)
   - FastAPI or Django
   - AWS (EC2, S3, Lambda)
   - PostgreSQL
   
   Nice to Have:
   - Kubernetes
   - Docker
   - GraphQL
   - TypeScript
   
   Must Have:
   - AWS Solutions Architect certification
   - Experience with microservices
   
   Compensation: $150k-$180k
   ```
3. Click "Send"

Expected: Job analysis appears with extracted skills, requirements, experience level.

### 3.3 Test resume parsing
1. Prepare a test resume (PDF, DOCX, or image)
2. In frontend, there should be a resume upload option
3. Upload the file
4. System parses and indexes it

### 3.4 Test matching
1. After uploading resume, click "Match Resumes" button
2. System runs agentic matching
3. Top 3 candidates appear with reasoning

---

## Troubleshooting

### Backend issues

**Error: "Failed to connect to LLM at localhost:1234"**
```bash
# Check if LLM is running
curl http://localhost:1234/api/v1/chat

# If not running, you may need to:
# 1. Start your local LLM service
# 2. Or modify LLM_API_URL in .env to match your setup
```

**Error: "ModuleNotFoundError: No module named 'langchain'"**
```bash
# Reinstall dependencies with UV
uv pip install -e .
```

**Error: Port 8000 already in use**
```bash
# Run on different port
uv run python -m uvicorn app:app --reload --port 8001
# Then update frontend .env REACT_APP_API_URL=http://localhost:8001
```

### Frontend issues

**Error: "Could not find a required file"**
```bash
# Make sure you're in frontend directory
cd hr-chatbot/frontend
# Clear cache
rm -rf node_modules package-lock.json
npm install
```

**Error: "Cannot find module '@heroicons/react'"**
```bash
# Install missing dependency
npm install @heroicons/react
```

**Frontend shows "API connection failed"**
1. Check backend is running on port 8000
2. Check REACT_APP_API_URL in frontend/.env
3. Verify backend .env has CORS_ORIGINS=["http://localhost:3000"]

---

## Verify Everything Works

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-01T10:30:00",
  "components_ready": {
    "llm_client": true,
    "index_manager": true,
    "agents": true
  }
}
```

### 2. API Testing
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "role": "hr"
  }'

# Get token from response, then use it:
TOKEN="<access_token_from_response>"

# Analyze job
curl -X POST http://localhost:8000/analyze-jd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Looking for Python developer with 5+ years AWS experience"
  }'
```

---

## Common Workflows

### Workflow 1: Complete Hiring Flow
```
1. Register/Login
2. Upload resumes (one or multiple)
3. Paste job description
4. System analyzes and extracts requirements
5. System finds matching resumes
6. Review top 3 candidates with reasoning
7. Select candidates and send interview invites
```

### Workflow 2: Quick Job Analysis
```
1. Login
2. Just paste job description (don't upload resume)
3. See requirement breakdown
4. Use this for internal discussions
```

### Workflow 3: Resume Exploration
```
1. Login
2. Upload multiple resumes
3. Just browse without specific job
4. System indexes all of them
```

---

## Development Tips

### View logs
- Backend logs appear in terminal where you ran `uv run python -m uvicorn...`
- Frontend logs in browser console (F12 → Console tab)

### Database (SQLite)
Location: `backend/data/hr_chatbot.db`

To reset (delete all data):
```bash
rm backend/data/hr_chatbot.db
```

### PageIndex storage
Location: `backend/data/pageindex/`

To clear indexed resumes:
```bash
rm -rf backend/data/pageindex/
```

### Disable resume parsing debug
In `backend/parsers/resume_parser.py`, set logs to WARNING:
```python
logging.basicConfig(level=logging.WARNING)
```

---

## Next Steps

1. **Test with real resumes**: Upload actual resumes from your system
2. **Try different jobs**: Test with varied job descriptions
3. **Customize**: Update system prompts in `agents/`
4. **Scale**: Add more resumes to test performance
5. **Deploy**: See deployment guide (coming soon)

---

## Need Help?

1. Check the logs (backend terminal or browser console)
2. Review error messages - they often tell you exactly what's wrong
3. Check if services are running:
   - Backend: `curl http://localhost:8000/health`
   - Frontend: Open http://localhost:3000
   - LLM: `curl http://localhost:1234/api/v1/chat`
4. Read the main README.md for detailed documentation

Good luck! 🚀
