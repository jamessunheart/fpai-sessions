# SPEC - Church Guidance Ministry (Droplet #13)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 13
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The Church Guidance Ministry provides automated guidance for forming and managing 508(c)(1)(a) organizations. It handles document generation, compliance checks, and educational funneling.

### 1.2 Position in Ecosystem
- **Upstream:** Receives leads from Storefront/Magnet.
- **Downstream:** Pushes users to Payment/Treasury for formation packages.
- **Role:** Legal & Spiritual Structure Specialist.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Storefront (Droplet #4) - Lead source

**External Dependencies:**
- PDF Generation Library (ReportLab/WeasyPrint)
- Stripe (for product linkage)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Document Generation** - Create Articles of Association, Bylaws, etc.
2. **Compliance Quiz** - Assess eligibility for 508c1a status.
3. **Guidance Funnel** - Educational email sequences.

### 2.2 Supported Operations
- `generate_formation_docs` - Create full PDF package.
- `assess_eligibility` - Score user questionnaire.

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints (Required)

#### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "church-guidance-ministry",
  "droplet_id": 13,
  "capabilities": ["document_generation", "legal_guidance"],
  "integration_endpoints": [
    {
      "path": "/api/v1/generate",
      "method": "POST",
      "description": "Generate formation docs"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Generate Docs
```
POST /api/v1/generate
```
**Request:**
```json
{
  "church_name": "Temple of Light",
  "trustees": ["Alice", "Bob"],
  "creed": "To serve..."
}
```
**Response:**
```json
{
  "download_url": "https://.../docs/temple-of-light-package.pdf"
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Ministries
```sql
CREATE TABLE ministries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    founder_email VARCHAR(255),
    status VARCHAR(50), -- 'inquiry', 'formed', 'active'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=church-guidance-ministry
SERVICE_PORT=8013
DROPLET_ID=13
REGISTRY_URL=http://registry:8000
STORAGE_PATH=/opt/fpai/data/docs
```

---

## 6. DEPLOYMENT

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8013
LABEL droplet.id="13"
LABEL droplet.name="church-guidance-ministry"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
