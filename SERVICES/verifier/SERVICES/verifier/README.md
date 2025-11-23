# Verifier Service (Droplet #8)

**Status:** 🟢 Beta  
**Version:** 1.0.0  
**Port:** 8008  
**UDC Compliant:** ✅ Yes

---

## 📋 Overview

The **Verifier Service** is the automated quality assurance engine of the Full Potential AI ecosystem. It validates services against the Universal Droplet Contract (UDC) and runs security checks.

**Key Capabilities:**
- **UDC Compliance:** Validates `/health` and `/capabilities`.
- **Scoring:** Assigns a compliance score (0-100%) to services.
- **Reporting:** Generates detailed JSON reports of scan results.

---

## 🚀 Quick Start

### Local Development
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run API
uvicorn app.main:app --reload --port 8008
```

### Production (Docker)
```bash
docker build -t fpai-verifier .
docker run -d -p 8008:8008 fpai-verifier
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/verify/{url}` | Trigger scan for a service URL |
| `GET` | `/api/v1/reports` | List past reports |

---

## 🧪 Testing

```bash
pytest
```

