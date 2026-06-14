# 🎯 MISSION M019: Service: Ops - Operational tooling and monitoring infrastructure

**Status:** 🟡 OPEN  
**Created:** 2025-11-23  
**Estimated Time:** TBD (see spec below)  
**Difficulty:** TBD (see spec below)

---

## 🚀 QUICK START FOR BUILDERS

**This is a ready-to-code mission.** Everything you need is in this file.

### 📦 STARTER KIT

Before you start coding, set up your foundation:

1. **Create a New Repository**
   ```bash
   mkdir mission-m019
   cd mission-m019
   git init
   ```

2. **Copy Foundation Files**
   
   You'll need these files from the Full Potential AI codebase:
   
   - `TECH_STACK.md` - Technology standards to follow
   - `UDC_COMPLIANCE.md` - Required endpoints (if building a service)
   - `.env.example` - Environment variable template
   
   Copy them from: `https://github.com/fullpotentialai/fpai-cockpit/tree/main/docs/architecture/foundation`

3. **Set Up Your Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Build According to Spec**
   
   Follow the detailed specification below. It includes:
   - Complete architecture
   - API endpoints
   - Database schemas
   - Testing requirements
   - Everything you need!

5. **Test Locally**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Start the service (if applicable)
   uvicorn app.main:app --reload
   
   # Test the endpoints
   curl http://localhost:8000/health
   ```

6. **Submit Your Work**
   
   When complete:
   - Push your code to GitHub (or your preferred platform)
   - Test that all requirements are met
   - Submit your repo URL: https://fullpotential.ai/feedback
   - Include: Your name, Mission ID (M019), and any notes

---

## 📝 TECHNICAL SPECIFICATION

# Ops - Operational Tooling and Monitoring Infrastructure

- **Priority:** P1
- **Constitution Principle:** **Autonomy over Dependency**
- **Regenerative Impact:** By implementing comprehensive operational tooling and monitoring, this service reduces the manual oversight required by operators, allowing them to focus on strategic improvements rather than routine maintenance tasks. This leads to more efficient operations and better resource utilization in the long run.

---

## 📋 OVERVIEW

The Ops service provides a robust framework for operational tooling and monitoring across all Full Potential AI services. It includes health checks, metrics collection, alerting, and logging capabilities that ensure high availability and performance of services.

### Business Value and User Impact
- **Automation of Monitoring Tasks:** Reduces manual monitoring efforts, freeing operators to focus on value-adding activities.
- **Improved System Reliability:** Early detection and resolution of issues lead to higher uptime and user satisfaction.
- **Scalable Infrastructure:** Supports scaling without additional operational overhead.

### Expected Timeline and Complexity Estimate
- **Timeline:** 8-10 weeks
- **Complexity:** Medium

---

## 🎯 REQUIREMENTS

### Functional Requirements
- Implement UDC-compliant endpoints for health, capabilities, state, dependencies, and messaging.
- Collect and store operational metrics (CPU usage, memory usage, request rates).
- Provide alerting mechanisms for critical thresholds.
- Enable structured logging across all services.

### Non-functional Requirements
- **Performance:** Must handle up to 10,000 requests per minute.
- **Security:** JWT authentication for all endpoints except health.
- **Reliability:** 99.9% uptime for all monitoring services.

### Success Criteria
- All UDC endpoints are compliant and tested.
- Metrics and logs are accessible and actionable.
- Alerts are triggered and resolved within defined SLAs.

---

## 🏗️ ARCHITECTURE

### System Components
- **FastAPI Application:** Main service handling requests and metrics collection.
- **PostgreSQL Database:** Stores metrics and logs.
- **Redis:** Used for caching operational data.
- **Prometheus:** For metrics scraping and storage.
- **Grafana:** Visualization of metrics and logs.

### Data Flow
1. **Metrics Collection:** FastAPI collects metrics and stores them in PostgreSQL.
2. **Monitoring and Alerting:** Prometheus scrapes metrics and triggers alerts via Alertmanager.
3. **Visualization:** Grafana queries data from Prometheus and PostgreSQL for dashboards.

### Integration Points
- **Existing Services:** Integrates with the Orchestrator for task assignments and state updates.
- **External APIs:** Uses Prometheus and Grafana APIs for metrics and visualization.

### Database Schema
- **Metrics Table:** Stores timestamp, service, metric name, and value.
- **Logs Table:** Stores timestamp, service, log level, and message.

---

## 🔌 API SPECIFICATION

### Endpoints
1. **GET /health**
   - **Response:** 
     ```json
     {
       "status": "healthy",
       "timestamp": "2025-11-15T12:00:00Z",
       "uptime_seconds": 86400,
       "version": "1.0.0"
     }
     ```
2. **GET /capabilities**
   - **Response:** 
     ```json
     {
       "service_name": "ops",
       "droplet_id": 101,
       "capabilities": ["monitoring", "alerting"],
       "supported_operations": ["collect_metrics", "generate_alerts"],
       "integration_endpoints": [{"path": "/metrics", "method": "GET", "description": "Fetch metrics"}]
     }
     ```
3. **GET /state**
   - **Response:** 
     ```json
     {
       "status": "active",
       "mode": "production",
       "metrics": {
         "requests_per_minute": 400,
         "average_response_time_ms": 20
       }
     }
     ```
4. **GET /dependencies**
   - **Response:** 
     ```json
     {
       "required_services": [{"name": "postgres", "type": "database", "status": "connected"}],
       "optional_services": [{"name": "redis", "type": "cache", "status": "connected"}]
     }
     ```
5. **POST /message**
   - **Request:**
     ```json
     {
       "from_service": "orchestrator",
       "message_type": "status_update",
       "payload": {"status": "updated"},
       "reply_to": "http://orchestrator:8001/callback"
     }
     ```
   - **Response:**
     ```json
     {
       "received": true,
       "message_id": "msg-789",
       "status": "processing"
     }
     ```

### Authentication Requirements
- JWT authentication required for all endpoints except `/health`.

### Error Handling
- Standardized error responses with codes and messages as per UDC guidelines.

---

## 💾 DATABASE DESIGN

### Table Schemas

#### Metrics
- **id:** Serial, Primary Key
- **timestamp:** Timestamp, Not Null
- **service_name:** Varchar(255), Not Null
- **metric_name:** Varchar(255), Not Null
- **value:** Float, Not Null

#### Logs
- **id:** Serial, Primary Key
- **timestamp:** Timestamp, Not Null
- **service_name:** Varchar(255), Not Null
- **log_level:** Varchar(50), Not Null
- **message:** Text, Not Null

### Indexes
- **Metrics:** Index on `service_name`, `timestamp`
- **Logs:** Index on `service_name`, `log_level`

---

## 🎨 UI/UX REQUIREMENTS

(Not applicable as this is a backend service)

---

## 🔐 SECURITY CONSIDERATIONS

### Authentication/Authorization
- Implement JWT-based authentication for all endpoints except `/health`.

### Data Validation
- Use Pydantic for request validation and serialization.

### Sensitive Data Handling
- Ensure logs and metrics do not contain sensitive information.

### Rate Limiting
- Implement rate limiting to prevent abuse, especially on endpoints that modify state.

---

## ✅ TESTING STRATEGY

### Unit Test Requirements
- Cover all service components with unit tests using `pytest`.

### Integration Test Scenarios
- Test integration with PostgreSQL and Redis.
- Verify Prometheus metrics scraping and alerting.

### End-to-end Test Cases
- Simulate full service operation from metrics collection to alert generation.

### Performance Benchmarks
- Test for 10,000 requests per minute load and validate system behavior.

---

## 📦 DEPLOYMENT PLAN

### Environment Variables
```bash
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001
SERVICE_NAME=ops
SERVICE_PORT=8010
DROPLET_ID=101
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Docker Configuration
- Use `python:3.11-slim` as base image.
- Include health check and expose port 8010.

### Dependencies to Install
- Install dependencies listed in `requirements.txt`.

### Migration Steps
- Run database migrations using Alembic.

---

## 🛠️ BUILDER INSTRUCTIONS

### Step-by-step Setup Guide
1. Clone the repository and navigate to the service directory.
2. Install dependencies with `pip install -r requirements.txt`.
3. Setup the database using Alembic migrations.

### How to Use the Starter Kit
- Use the provided FastAPI template and standard package structure.

### Where to Find Foundation Files
- All foundational files are located in the `app/` directory.

### How to Test Locally
- Run tests using `pytest` and verify coverage with `pytest-cov`.

### Submission Process
- Push changes to the repository and create a pull request for review.

---

## 💬 GETTING HELP

**Stuck?** Don't struggle alone!

- **Ask Questions:** https://fullpotential.ai/feedback
- **Report Issues:** Same form, tell us what's blocking you
- **Suggest Improvements:** If the spec is unclear, let us know

**Your feedback makes the system better for everyone.**

---

## ✅ COMPLETION CHECKLIST

Before submitting, verify:

- [ ] All requirements implemented
- [ ] Tests passing (>80% coverage)
- [ ] Code follows TECH_STACK.md standards
- [ ] UDC endpoints implemented (if applicable)
- [ ] README.md with setup instructions
- [ ] Environment variables documented
- [ ] Local testing successful
- [ ] Code committed to repository

---

## 🎓 WHAT YOU'LL LEARN

By completing this mission:
- Modern Python backend development (FastAPI)
- Database design and ORMs (PostgreSQL + SQLAlchemy)
- API design and documentation
- Testing and quality assurance
- Docker containerization
- Professional development workflows

---

**Original Idea:** "Service: Ops - Operational tooling and monitoring infrastructure"  
**Mission ID:** M019  
**Generated:** 2025-11-23T13:58:22.618058

🚀 **Let's build something awesome!**
