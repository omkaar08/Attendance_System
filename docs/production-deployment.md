# Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the VisionAttend AI Face Recognition Attendance System to production (Railway/Vercel).

## Architecture

```
┌──────────────────────────┐
│   Vercel (Frontend)      │  React + Vite + TypeScript
│   visionattend.vercel.app    │
└──────────────┬───────────┘
               │ HTTPS
┌──────────────▼───────────┐
│  Railway (Backend API)   │  FastAPI + Python 3.11
│  api.visionattend.railway.io │
└──────────────┬───────────┘
               │ PostgreSQL Driver
┌──────────────▼───────────┐
│ Supabase PostgreSQL+Auth │  pgvector, Storage, JWT
│  (Managed Service)       │
└──────────────────────────┘
```

## Prerequisites

- Supabase project created and configured
- Railway account with linking to GitHub
- Vercel account with GitHub integration
- GitHub repository with clean history
- Domain names (optional but recommended)

## Phase 1: Backend Deployment (Railway)

### Step 1: Prepare Backend for Production

#### 1.1 Update Python Version

```bash
# Railway requires Python 3.11 for InsightFace compatibility
# Update backend/pyproject.toml
[project]
requires-python = ">=3.11,<3.12"
```

#### 1.2 Verify Production Dependencies

```bash
cd backend
pip install -e .
pip install gunicorn  # Production WSGI server
```

#### 1.3 Create Procfile

```text
# backend/Procfile
release: python -m alembic upgrade head
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} app.main:app
```

#### 1.4 Environment Configuration

Create `backend/.env.production`:

```bash
# Railway will inject these from environment
APP_NAME=visionattend-backend
APP_ENV=production

# Supabase
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
DATABASE_URL=${DATABASE_URL}

# CORS for production
BACKEND_CORS_ORIGINS=["https://visionattend.vercel.app","https://yourdomain.com"]

# Face Recognition
FACE_MODEL_WARMUP=true
FACE_MODEL_NAME=buffalo_sc
FACE_RECOGNITION_THRESHOLD=0.50
FACE_MIN_QUALITY_SCORE=0.60

# Attendance
ATTENDANCE_CONFIDENCE_THRESHOLD=0.80

# Rate Limiting
SLOWAPI_ENABLED=true
```

### Step 2: Set Up Railway Project

#### 2.1 Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your GitHub repository
4. Choose `backend` directory as root

#### 2.2 Configure Environment Variables

In Railway Dashboard → Variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=[your anon key]
SUPABASE_SERVICE_ROLE_KEY=[your service role key]
DATABASE_URL=postgresql+asyncpg://user:password@host/postgres
BACKEND_CORS_ORIGINS=[\"https://visionattend.vercel.app\"]
```

#### 2.3 Database Migrations

```bash
# Railway will run on deployment:
# 1. migrations/0001_initial_schema.sql
# 2. migrations/0002_auth_sync_and_rls.sql
# 3. migrations/0003_face_embedding_index.sql
```

#### 2.4 Deploy

Push to GitHub:

```bash
git add .
git commit -m "Production deployment"
git push origin main
```

Railway will automatically deploy. Verify:

```bash
curl https://api-your-project.railway.app/v1/health
# Should return: {"status": "healthy", ...}
```

## Phase 2: Frontend Deployment (Vercel)

### Step 1: Prepare Frontend

#### 1.1 Update Environment Variables

Create `frontend/.env.production`:

```
VITE_API_BASE_URL=https://api-your-project.railway.app
```

#### 1.2 Build Test

```bash
cd frontend
npm run build
# Should complete in ~30s with no errors
```

#### 1.3 Update package.json

```json
{
  "scripts": {
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }
}
```

### Step 2: Deploy to Vercel

#### 2.1 Connect Repository

1. Go to [vercel.com](https://vercel.com)
2. Import repository
3. Select `frontend` as root directory
4. Configure environment variables

#### 2.2 Vercel Settings

```
Framework Preset: Vite
Build Command: npm run build
Output Directory: dist
Install Command: npm ci
```

#### 2.3 Deploy

Click "Deploy" - Vercel will build and deploy automatically.

## Phase 3: Post-Deployment Configuration

### Step 1: Verify All Services

```bash
# Backend health
curl https://api.visionattend.com/v1/health

# Frontend accessibility
curl https://visionattend.vercel.app

# Database connectivity
# Check Supabase dashboard
```

### Step 2: Run Initial Setup

```bash
# Provision test users
curl -X POST https://api.visionattend.com/v1/admin/provision-test-users \
  -H "Authorization: Bearer $TOKEN"

# Verify face recognition pipeline
curl -X POST https://api.visionattend.com/v1/recognition/statistics
```

### Step 3: Configure Custom Domain (Optional)

#### For Backend (Railway):

1. Railway Dashboard → Networking
2. Add custom domain: `api.visionattend.com`
3. Configure DNS CNAME

#### For Frontend (Vercel):

1. Vercel Dashboard → Domains
2. Add domain: `visionattend.com`
3. Configure nameservers or CNAME

### Step 4: Set Up SSL/TLS

- Railway: Automatically provisioned
- Vercel: Automatically managed
- Database: Use SSL connection:

```
postgresql+asyncpg://user:password@host/postgres?ssl=require
```

## Best Practices

### 1. Database Optimization

```sql
-- Create indexes on frequently queried fields
CREATE INDEX idx_students_department_semester 
  ON students(department_id, semester);

CREATE INDEX idx_attendance_subject_date 
  ON attendance(subject_id, class_date);

-- pgvector index for similarity search
CREATE INDEX ON face_embeddings 
  USING ivfflat (embedding_vector vector_cosine_ops) 
  WITH (lists = 100);
```

### 2. Backup Strategy

- Enable automated backups in Supabase Dashboard
- Backup frequency: Daily
- Retention: 30 days
- Test restore quarterly

### 3. Monitoring & Logging

#### Application Logs

```bash
# Railway: Logs → View deployment logs
# Check for errors: startup, API failures, DB timeouts

# Monitor metrics:
- Response time (avg < 200ms)
- Error rate (< 0.1%)
- Requests/sec capacity
```

#### Database Monitoring

```sql
-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM attendance 
WHERE subject_id = $1 AND class_date = $2;

-- Monitor active connections
SELECT count(*) FROM pg_stat_activity;
```

### 4. Rate Limiting Configuration

```python
# backend/app/core/limiter.py
RATE_LIMITS = {
    "default": "100/minute",           # General API rate limit
    "/recognition/identify": "10/minute",  # Face recognition (expensive)
    "/auth/login": "5/minute",          # Prevent brute force
}
```

### 5. Error Handling & Alerts

```bash
# Set up email alerts for:
- Deployment failures (Railway)
- Build failures (Vercel)
- Database connection errors
- High error rates (>5%)
```

## Performance Optimization

### 1. Image Optimization

```python
# backend/app/services/face_onnx.py
_MAX_IMAGE_DIM = 1280      # Resize if larger
_JPEG_QUALITY = 85         # Compression
```

### 2. Caching Strategy

```python
# Cache embeddings statistics for 1 hour
@lru_cache(maxsize=1)
async def get_embedding_statistics():
    # Returns cached result for 3600 seconds
    pass
```

### 3. Database Query Optimization

```python
# Use DISTINCT ON for efficient queries
query = select(distinct(Student.id)).where(...)

# Batch operations
session.add_all(students_list)  # Add all before commit
await session.commit()
```

## Troubleshooting

### 1. InsightFace Installation Fails

**Problem:** `ModuleNotFoundError: No module named 'insightface'`

**Solution:**
```bash
# Railway uses Python 3.11 which has InsightFace wheels
# Ensure pyproject.toml specifies >=3.11

# If still fails:
pip install insightface --upgrade
# Or use ONNX-based fallback (app/services/face_onnx.py)
```

### 2. Database Connection Timeout

**Problem:** `asyncpg.exceptions.CannotConnectNowError`

**Solution:**
```bash
# Check DATABASE_URL is correct
# Enable SSL: ?ssl=require
# Increase pool size in app/db/session.py
```

### 3. High API Response Times

**Problem:** Requests taking > 500ms

**Solution:**
```python
# Profile with:
import cProfile
cProfile.run('recognize_faces()')

# Optimize:
- Use pgvector <=> operator (much faster than Python cosine)
- Batch image processing
- Cache model in memory
```

### 4. Out of Memory Errors

**Problem:** Process crashes after running for hours

**Solution:**
```python
# Fix in face_onnx.py:
- Release model after inference
- Use generator for batch processing
- Clear embedding cache periodically
```

## Scaling Considerations

### Growth Targets

- **100 students:** Current setup sufficient
- **1,000 students:** Add read replicas for reports
- **10,000 students:** Partitioning by semester/department
- **100,000+ students:** Distributed recognition service

### Horizontal Scaling

```bash
# Railway: Increase dynos
# Vercel: Automatic (serverless)

# Backend replicas handle:
- API requests (stateless)
- Face recognition (CPU-bound)
- Attendance marking (DB-bound)
```

### Database Scaling

```sql
-- For 10,000+ students:
-- Partition attendance by month
CREATE TABLE attendance_2026_03 PARTITION OF attendance
  FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Replicate read-heavy analytics to separate DB
```

## Security Checklist

- [ ] HTTPS enabled (SSL certificates active)
- [ ] Database passwords strong & rotated
- [ ] API keys in environment variables (never in code)
- [ ] CORS configured for exact domains only
- [ ] Rate limiting enabled on login/recognition
- [ ] Audit logging enabled
- [ ] Backups tested and restorable
- [ ] Environment parity (dev ≈ prod)
- [ ] No secrets in Git history
- [ ] JWT token expiration set (3600s)

## Maintenance Schedule

### Daily
- Monitor error rates
- Check database connections

### Weekly
- Review audit logs
- Test recovery procedures

### Monthly
- Performance analysis
- Security updates for dependencies
- Database optimization

### Quarterly
- Full disaster recovery test
- Load testing
- Security audit

## Support & Escalation

**Contact the core team for:**
1. Database schema changes
2. Model updates (InsightFace)
3. High-traffic events
4. Security incidents

---

**Last Updated:** March 17, 2026
**Maintainer:** Platform Engineering
