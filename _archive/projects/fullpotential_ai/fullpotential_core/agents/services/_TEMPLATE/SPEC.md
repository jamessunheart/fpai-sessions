# [Service Name] - Technical Specification

**Version**: 1.0
**Author**: Session #N
**Date**: YYYY-MM-DD
**Status**: Draft | Review | Approved

---

## Purpose

**Problem Statement**:
[What problem does this service solve?]

**Solution**:
[How does this service solve it?]

**Value Proposition**:
[What value does it provide to users/system?]

---

## Architecture

### High-Level Overview

```
[Draw or describe the architecture]

Example:
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ↓
┌─────────────┐     ┌──────────────┐
│  FastAPI    │────▶│   Database   │
│  Service    │     │  PostgreSQL  │
└─────────────┘     └──────────────┘
       │
       ↓
┌─────────────┐
│  External   │
│  API (e.g.  │
│  Claude)    │
└─────────────┘
```

### Components

1. **Component 1**: [Description]
2. **Component 2**: [Description]
3. **Component 3**: [Description]

### Technology Stack

- **Backend**: Python 3.9+, FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis (if applicable)
- **External APIs**: [List any external services]
- **Deployment**: Docker, Systemd

---

## Data Models

### Model 1: [Name]

```python
class ModelName(BaseModel):
    id: str
    field1: str
    field2: int
    created_at: datetime
    updated_at: datetime
```

**Description**: [What this model represents]

### Model 2: [Name]

```python
class AnotherModel(BaseModel):
    id: str
    reference_id: str  # Foreign key to Model1
    data: dict
    status: str
```

**Description**: [What this model represents]

---

## API Endpoints

### Core Endpoints

#### GET /health
- **Description**: Health check endpoint
- **Parameters**: None
- **Returns**:
  ```json
  {
    "status": "healthy",
    "service": "[service-name]",
    "version": "1.0.0"
  }
  ```

#### POST /api/[resource]
- **Description**: [What this endpoint does]
- **Parameters**:
  ```json
  {
    "field1": "string",
    "field2": 123
  }
  ```
- **Returns**:
  ```json
  {
    "id": "uuid",
    "status": "created"
  }
  ```
- **Errors**:
  - 400: Invalid input
  - 500: Server error

#### GET /api/[resource]/{id}
- **Description**: Get a specific resource
- **Parameters**:
  - Path: `id` (string)
- **Returns**: Resource object
- **Errors**:
  - 404: Not found

[Add more endpoints as needed]

---

## Business Logic

### Core Workflows

#### Workflow 1: [Name]
1. Step 1: [Description]
2. Step 2: [Description]
3. Step 3: [Description]

**Example**:
```
User submits data →
Validate input →
Process with AI →
Store result →
Return response
```

#### Workflow 2: [Name]
[Describe the workflow]

---

## Dependencies

### Internal Dependencies
- **Service 1**: [Why needed]
- **Service 2**: [Why needed]

### External Dependencies
- **Claude API**: For AI processing
- **SendGrid**: For email sending
- **Stripe**: For payments (if applicable)

### Database Schema

```sql
CREATE TABLE table_name (
    id UUID PRIMARY KEY,
    field1 VARCHAR(255),
    field2 INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_field1 ON table_name(field1);
```

---

## Performance Requirements

### Expected Load
- **Requests per second**: X
- **Concurrent users**: Y
- **Data volume**: Z GB

### Response Time Targets
- **API endpoints**: <200ms (p95)
- **Database queries**: <50ms
- **External API calls**: <1s

### Scalability
- **Horizontal scaling**: Yes/No
- **Caching strategy**: [Describe]
- **Database sharding**: Yes/No (if applicable)

---

## Security Considerations

### Authentication
- **Method**: JWT, API Key, OAuth2
- **Token expiration**: X hours/days
- **Refresh token**: Yes/No

### Authorization
- **Role-based access control**: Yes/No
- **Roles**: [List roles]
- **Permissions**: [Describe]

### Data Protection
- **Encryption at rest**: Yes/No
- **Encryption in transit**: HTTPS/TLS
- **PII handling**: [How personally identifiable information is handled]
- **Credential management**: Vault, environment variables

### Input Validation
- **All inputs validated**: Yes
- **SQL injection protection**: Parameterized queries
- **XSS protection**: Input sanitization
- **Rate limiting**: X requests/minute per IP

---

## Monitoring & Observability

### Health Checks
- `/health` endpoint
- Database connectivity check
- External service connectivity check

### Metrics
- Request count
- Response time (p50, p95, p99)
- Error rate
- Active connections

### Logging
- **Log level**: INFO in production, DEBUG in development
- **Log format**: JSON structured logs
- **Log rotation**: Daily
- **Retention**: 30 days

### Alerts
- **Service down**: Immediate
- **Error rate >1%**: Within 5 minutes
- **Response time >500ms**: Within 10 minutes

---

## Testing Strategy

### Unit Tests
- **Coverage target**: 80%+
- **Key areas**: Business logic, data validation

### Integration Tests
- **Database integration**: Yes
- **External API mocks**: Yes
- **End-to-end workflows**: Critical paths

### Load Tests
- **Target**: X requests/second
- **Duration**: Y minutes
- **Success criteria**: <500ms response time, <0.1% error rate

---

## Deployment

### Environments
- **Development**: Local
- **Staging**: http://staging.fullpotential.com/[service]
- **Production**: https://fullpotential.com/[service]

### Deployment Process
1. Run tests
2. Build Docker image (if applicable)
3. Deploy to staging
4. Smoke tests
5. Deploy to production
6. Monitor metrics

### Rollback Plan
- **Trigger**: Error rate >5% or service down
- **Process**: Revert to previous version
- **Time**: <5 minutes

---

## Future Enhancements

### Phase 2 (Optional)
- [ ] Feature 1
- [ ] Feature 2
- [ ] Performance optimization

### Phase 3 (Optional)
- [ ] Advanced feature 1
- [ ] Integration with service X
- [ ] Machine learning enhancement

---

## Questions & Decisions

### Open Questions
1. [Question 1]
2. [Question 2]

### Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| [Decision 1] | [Why] | YYYY-MM-DD |
| [Decision 2] | [Why] | YYYY-MM-DD |

---

## References

- [Related Service 1 SPEC]
- [External API Documentation]
- [Design Document]

---

**This specification provides the technical blueprint for building [Service Name].**

**Next Steps**:
1. Review and approve this spec
2. Update PROGRESS.md with Phase 1 tasks
3. Begin implementation following ASSEMBLY_LINE_SOP.md
