# Installation & Deployment Guide

## Local Development Setup

This guide covers setting up the HR Chatbot on your local machine.

### System Requirements

- **OS**: macOS, Linux, or WSL2 on Windows
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher
- **RAM**: 8GB minimum
- **Disk**: 5GB for dependencies + PageIndex storage

### Prerequisites Installation

#### macOS
```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10+
brew install python@3.10

# Install UV
brew install uv
# Or: pip install uv

# Install Node.js
brew install node

# Install Tesseract OCR (for image resume parsing)
brew install tesseract
```

#### Linux (Ubuntu/Debian)
```bash
# Update package manager
sudo apt update

# Install Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip

# Install UV
pip install uv
# Or: curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Tesseract OCR
sudo apt install tesseract-ocr
```

#### Windows (WSL2)
```bash
# In WSL2 terminal, follow Linux instructions above
```

### Verify Installations
```bash
python --version        # Should be 3.10+
uv --version           # Should show version
node --version         # Should be 18+
npm --version          # Should be 8+
tesseract --version    # Should show version
```

---

## Local Development Workflow

### 1. Clone/Setup Project Structure

```bash
cd /path/to/your/projects
mkdir -p hr-chatbot
cd hr-chatbot

# Copy the backend and frontend folders
# (You already have these from the implementation)

ls -la
# Should show: backend/ frontend/ README.md QUICKSTART.md
```

### 2. Backend Setup

```bash
cd backend

# Create .env file
cp .env.example .env

# Edit .env with your settings (optional)
# nano .env

# Install dependencies with UV
uv pip install -e .

# Create data directories
mkdir -p data/pageindex data/uploads

# Run server
uv run python -m uvicorn app:app --reload
```

Server runs on: http://localhost:8000

### 3. Frontend Setup (in new terminal)

```bash
cd frontend

# Install dependencies
npm install

# Create .env if needed
cp .env.example .env

# Start dev server
npm start
```

App opens at: http://localhost:3000

---

## Production Deployment

### Option 1: Docker Containers

Create `backend/Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr

# Copy project
COPY . .

# Install with UV
RUN pip install uv
RUN uv pip install -e .

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `frontend/Dockerfile`:
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - LLM_API_URL=http://llm:1234/api/v1/chat
      - DATABASE_URL=postgresql://hrbot:password@db:5432/hrbot
    depends_on:
      - db
    volumes:
      - ./backend/data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://backend:8000

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=hrbot
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=hrbot
    volumes:
      - postgres_data:/var/lib/postgresql/data

  llm:
    image: your-local-llm-image:latest
    ports:
      - "1234:1234"

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

### Option 2: Cloud Deployment (AWS/GCP/Azure)

#### AWS Deployment Steps:

1. **Prepare Backend for AWS**:
   - Move to PostgreSQL (not SQLite)
   - Update `DATABASE_URL` in `backend/.env`
   - Move resume storage to S3
   - Update `.env` with S3 credentials

2. **Deploy with Elastic Beanstalk**:
   ```bash
   eb init -p python-3.10 hr-chatbot-backend
   eb create hr-chatbot-prod
   eb deploy
   ```

3. **Deploy Frontend to S3 + CloudFront**:
   ```bash
   npm run build
   aws s3 sync build/ s3://your-bucket-name/
   ```

4. **Setup RDS for PostgreSQL**
5. **Configure LLM access** (if self-hosted or via API)

#### Google Cloud Deployment:

1. **Prepare Backend**:
   - Use Cloud SQL for PostgreSQL
   - Use Cloud Storage for file uploads
   - Use Secret Manager for API keys

2. **Deploy to Cloud Run**:
   ```bash
   # Backend
   gcloud run deploy hr-chatbot-backend \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated

   # Frontend
   npm run build
   gsutil -m cp -r build/* gs://your-bucket/
   ```

### Option 3: On-Premises / VPS

Using DigitalOcean, Linode, or similar:

1. **SSH into server**:
   ```bash
   ssh root@your-server-ip
   ```

2. **Install dependencies**:
   ```bash
   apt update && apt install -y python3.10 nodejs postgresql-15 tesseract-ocr nginx
   ```

3. **Clone repository and setup**:
   ```bash
   git clone https://github.com/your-org/hr-chatbot.git
   cd hr-chatbot/backend
   pip install uv
   uv pip install -e .
   ```

4. **Configure systemd service**:
   ```ini
   # /etc/systemd/system/hr-chatbot-backend.service
   [Unit]
   Description=HR Chatbot Backend
   After=network.target

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/home/hr-chatbot/backend
   ExecStart=/usr/local/bin/uv run python -m uvicorn app:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

5. **Configure Nginx reverse proxy**:
   ```nginx
   server {
       listen 80;
       server_name hr-chatbot.your-domain.com;
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location / {
           proxy_pass http://localhost:3000;
       }
   }
   ```

---

## Database Migration

### Local Development: SQLite → Production: PostgreSQL

1. **Export data from SQLite**:
   ```python
   # Script to export
   import sqlite3
   conn = sqlite3.connect('data/hr_chatbot.db')
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM users")
   users = cursor.fetchall()
   # Export to JSON/CSV
   ```

2. **Import to PostgreSQL**:
   ```python
   import psycopg2
   conn = psycopg2.connect("postgresql://user:pwd@host/dbname")
   cursor = conn.cursor()
   # Insert data
   ```

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

---

## Environment Variables

### Backend (.env)
```env
# LLM Configuration
LLM_API_URL=http://localhost:1234/api/v1/chat
LLM_MODEL=lfm2.5-1.2b-instruct
LLM_TIMEOUT=30

# Security (change in production!)
SECRET_KEY=your-very-secure-key-here-1234567890

# Database
DATABASE_URL=sqlite:///./data/hr_chatbot.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/hrbot

# File Storage
UPLOAD_DIR=./data/uploads
PAGEINDEX_PATH=./data/pageindex

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Logging
DEBUG=True
LOG_LEVEL=INFO
```

### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENV=development
```

---

## SSL/TLS Setup

For production (HTTPS):

### Option 1: Let's Encrypt with Certbot
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d hr-chatbot.your-domain.com
```

### Option 2: AWS Certificate Manager
- Create certificate
- Attach to CloudFront/ALB

### Option 3: Self-signed (for testing)
```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

---

## Monitoring & Logging

### Backend Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info("User registered: email@example.com")
logger.warning("LLM timeout")
logger.error("Database connection failed", exc_info=True)
```

### Application Monitoring
- Use **Sentry** for error tracking
- Use **DataDog** or **New Relic** for APM
- Use **Prometheus** for metrics

### Log Aggregation
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **CloudWatch** (AWS)

---

## Backup & Disaster Recovery

### Database Backups
```bash
# PostgreSQL backup
pg_dump -h localhost -U user -d hrbot > backup.sql

# Restore
psql -h localhost -U user -d hrbot < backup.sql
```

### File Storage Backups
```bash
# AWS S3
aws s3 sync ./data/uploads s3://backup-bucket/

# Local backup
tar -czf backup-$(date +%Y%m%d).tar.gz ./data/
```

---

## Performance Optimization

### Backend Optimization
- Enable Redis caching
- Use connection pooling
- Optimize PageIndex queries
- Use CDN for static files

### Frontend Optimization
- Code splitting
- Image optimization
- Lazy loading
- Service workers

---

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use strong database passwords
- [ ] Enable HTTPS/SSL
- [ ] Set up CORS properly
- [ ] Rate limiting on API endpoints
- [ ] Regular security updates
- [ ] Audit logs for sensitive operations
- [ ] Change default credentials

---

## Troubleshooting Deployment

### Backend won't start
```bash
# Check logs
journalctl -u hr-chatbot-backend -f

# Test connection
curl http://localhost:8000/health
```

### High memory usage
- Check PageIndex size
- Reduce BATCH_SIZE for resume processing
- Enable pagination on API endpoints

### Slow resume matching
- Add database indexes
- Use caching
- Optimize PageIndex queries
- Consider queuing for large batches

---

## Support & Maintenance

- Regular dependency updates: `uv pip list --outdated`
- Database maintenance: Index optimization, vacuum
- Log rotation: Implement log rolling
- Monitoring: Set up alerts for failures
