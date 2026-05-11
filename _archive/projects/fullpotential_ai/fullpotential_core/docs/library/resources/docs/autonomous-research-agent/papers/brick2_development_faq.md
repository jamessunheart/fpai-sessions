# BRICK 2 Marketing Automation Platform - Development FAQ

## Project Overview Questions

### Q: Is the 21-hour timeline realistic for this scope of work?
**A**: The 21-hour estimate assumes aggressive use of AI development tools (Cursor Composer, Claude Projects, v0.dev, GitHub Copilot) for code generation rather than manual development. Developers experienced with AI-assisted development should find this timeline achievable. Traditional manual coding approaches will require significantly more time.

### Q: What level of AI tool proficiency is expected?
**A**: High proficiency expected with:
- **Cursor Composer**: Backend generation (80%+ of FastAPI code)
- **Claude Projects**: Complex API integration logic
- **v0.dev**: React component generation from descriptions
- **GitHub Copilot**: Boilerplate and DevOps automation
- **No-code platforms**: Clay.com, Make.com, Zapier for workflow automation

### Q: Why milestone-based payments instead of hourly?
**A**: Milestone structure allows quality validation at each stage and provides natural decision points for project continuation. Each milestone has specific success criteria that must be met before payment. This protects both parties and ensures deliverable quality.

## Technical Architecture Questions

### Q: Should campaign orchestration use real-time streaming or batch processing?
**A**: Real-time streaming required. System must respond to BRICK 1 strategic guidance within 30 seconds and provide performance reports every 15 minutes. Use Redis Streams with priority queues rather than Kafka for our scale requirements.

### Q: What message transport layer should be used?
**A**: Redis Streams with priority queues (Emergency <1 second, High <30 seconds, Normal <5 minutes, Low <15 minutes). Kafka adds unnecessary complexity for our current scale while Redis provides the required sub-second emergency response capability.

### Q: How should feature flags be implemented?
**A**: Database-stored with dynamic updates in PostgreSQL with Redis caching. BRICK 1 integration requires runtime capability negotiation - config-based flags would require deployment cycles that break real-time orchestration.

### Q: Should dual-mode operation be stateful or stateless?
**A**: Stateful session manager tracking campaign ownership. When switching between human and AI control, the system must track which campaigns are under which management type, especially for emergency overrides and mode transitions.

### Q: How should real-time reporting handle API rate limits?
**A**: Hybrid approach - cache recent data in database/Redis for regular 15-minute reports, supplement with direct API calls for critical real-time alerts (budget overages, performance anomalies). Balances API efficiency with data freshness.

## BRICK 1 Integration Questions

### Q: What is BRICK 1 and why is this integration complex?
**A**: BRICK 1 is a strategic AI orchestration system being developed in parallel. BRICK 2 must implement UBIC v1.5 compliance with specific message types, priority handling, and feature flag negotiation. This represents the future AI orchestration capability while maintaining standalone functionality.

### Q: What message types must be supported?
**A**: 
**Incoming**: `strategic_guidance`, `optimization_directive`, `resource_allocation`, `emergency_pause`
**Outgoing**: `performance_report`, `lead_intelligence`, `optimization_recommendation`, `resource_utilization`, `anomaly_alert`

### Q: What are the UBIC v1.5 requirements?
**A**: Standard endpoints (`/health`, `/capabilities`, `/state`, `/dependencies`, `/message`, `/send`, `/reload-config`, `/shutdown`, `/emergency-stop`), JWT authentication with `brick_capabilities`, Prometheus metrics, and proper message formatting with idempotency keys and trace IDs.

### Q: Can the system function without BRICK 1?
**A**: Yes, BRICK 2 must be fully functional as a standalone system with human operators. BRICK 1 integration provides AI orchestration capabilities but is not required for core marketing automation functionality.

## Business Requirements Questions

### Q: What level of testing coverage is required?
**A**: 80%+ automated test coverage for each milestone with comprehensive integration testing. Production-ready quality from Milestone 1 - this is not an MVP approach.

### Q: What are the performance requirements?
**A**: 
- API response times <500ms for campaign operations
- Dashboard load times <2 seconds
- Campaign deployment <1 minute from creation to live
- 99.5% uptime during business hours
- Emergency response <1 second for critical alerts

### Q: Should CRM integration be read-only or bidirectional?
**A**: Lead handoff only initially. System automatically syncs qualified leads to HubSpot/Salesforce but doesn't require updating existing CRM records. Revenue attribution handles reverse data flow for reporting.

### Q: Is multi-tenant support required from the start?
**A**: Single-tenant architecture initially serving our business systems (Church Kit Generator, Global Sky AI, treasury management). Design for future multi-tenant scaling but implement single-tenant first.

## Platform Integration Questions

### Q: Which advertising platforms must be integrated?
**A**: Google Ads, Facebook Ads, and LinkedIn Ads with full campaign CRUD operations, real-time performance tracking, and budget management. Each platform has different rate limits and authentication requirements.

### Q: What no-code platforms should be leveraged?
**A**: 
- **Clay.com**: Email sequence automation
- **PhantomBuster**: LinkedIn outreach automation
- **Make.com**: CRM workflow automation
- **Retool**: Analytics dashboard components
- **Zapier**: System integrations and data flow

### Q: How should lead scoring be implemented?
**A**: Start with rules-based engine for immediate business value, build ML model foundation simultaneously. Rules provide immediate functionality while ML prepares for BRICK 1 AI enhancement capabilities.

## Development Process Questions

### Q: What happens if milestone validation fails?
**A**: No payment until success criteria are met. Developer must address all validation requirements before milestone completion. Project may be terminated with code handoff if quality standards cannot be achieved.

### Q: Can the project be terminated early?
**A**: Yes, after any completed milestone with 24-hour notice. All validated milestone code transfers to client. Developer provides 2-hour handoff session and complete documentation for project transition.

### Q: What documentation is required?
**A**: Each milestone requires:
- Complete API documentation with examples
- Code documentation and commenting
- User guides for functionality delivered
- Integration specifications for BRICK 1 compatibility
- Testing procedures and validation steps

### Q: Are there performance bonuses available?
**A**: Yes, bonuses for:
- Exceptional quality with ahead-of-schedule delivery
- Flawless BRICK 1 integration on first attempt
- Measurable business results within first week of operation
(Amounts negotiated based on final project value)

## Common Misconceptions

### Q: Is this just an advertising automation tool?
**A**: No, BRICK 2 is comprehensive marketing automation including email sequences, social media outreach, lead qualification, CRM integration, revenue attribution, and conversational AI. Advertising is one component of the complete system.

### Q: Can traditional development approaches work for this timeline?
**A**: Traditional manual coding will require 3-4x more time (60-80 hours vs 21 hours). The timeline assumes AI-first development methodology with extensive tool leverage for code generation.

### Q: Is the technical complexity overstated?
**A**: The individual components are well-established, but the integration complexity comes from:
- Multi-platform API coordination with different rate limits
- Real-time performance tracking across all channels
- BRICK 1 integration with UBIC v1.5 compliance
- Dual-mode operation with seamless switching
- Production-grade reliability and error handling

### Q: Why not build this as separate microservices?
**A**: BRICK 2 is designed as a cohesive marketing automation system with tight integration requirements. While it implements UBIC compliance for external integration, internal components need close coordination for real-time performance optimization and unified user experience.

## Selection Criteria

### Q: What makes a developer ideal for this project?
**A**: 
- Extensive experience with AI development tools (Cursor, Claude, GitHub Copilot)
- Marketing automation platform development background
- Multi-platform API integration experience
- Understanding of real-time systems and message queuing
- Experience with production-grade error handling and monitoring
- Comfort with milestone-based validation and quality standards

### Q: How should developers demonstrate their fit?
**A**: Provide:
- Portfolio examples of marketing automation or multi-platform integration work
- Evidence of AI tool usage in development process
- Individual milestone bids with technical approach explanation
- References from similar API integration and dashboard development projects

### Q: What should developers avoid in their proposals?
**A**: 
- Traditional development time estimates without AI tool leverage
- Requests for calls instead of addressing technical questions directly
- Vague proposals without specific technical approach details
- Resistance to milestone-based validation or quality standards
- Lack of understanding of real-time systems or message processing requirements

This FAQ addresses the most common developer questions and concerns. Additional technical details are available in the complete project specification document.
