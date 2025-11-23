# 🎯 MISSION M012: Spec for Church Guidance Ministry

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
   mkdir mission-m012
   cd mission-m012
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
   - Include: Your name, Mission ID (M012), and any notes

---

## 📝 TECHNICAL SPECIFICATION

# Church Guidance Ministry

- **Priority:** P1 (High/Core)
- **Constitution Principle:** **Optimization over Extraction**
- **Regenerative Impact:** Provides a streamlined, low-friction pathway for communities to establish legal and spiritual sovereignty, optimizing the formation process and reducing dependency on expensive external legal systems.

## 1. 📋 OVERVIEW
The Church Guidance Ministry service (`church-guidance-ministry`) automates the process of establishing a 508(c)(1)(a) faith-based organization. It guides users through a questionnaire, generates necessary legal documents (Articles of Association, Bylaws), and facilitates the donation/payment process via Stripe.

- **Business Value:** Direct revenue generation ($97-$297 per formation) and onboarding of values-aligned communities.
- **User Impact:** Users can form a church in minutes rather than weeks, with guaranteed compliance.
- **Timeline:** 3-4 days.
- **Complexity:** Medium (Document generation and Payment integration).

## 2. 🎯 REQUIREMENTS
- **Functional:**
  - Intake form API to capture church details (Name, Trustees, Mission).
  - Document Generation Engine (Jinja2 templates -> Markdown -> PDF).
  - Stripe Checkout integration for product purchase.
  - Email delivery of formation packages (via `email-automation-system`).
  - Webhook handler for Stripe events (payment_succeeded).
- **Non-Functional:**
  - UDC Compliant.
  - Data Privacy: Encrypt sensitive trustee PII.
  - Reliability: Ensure documents are generated and sent even if email service is temporarily down (queueing).

## 3. 🏗️ ARCHITECTURE
- **Components:**
  - **Intake API:** REST endpoints for form data.
  - **Doc Generator:** Python logic to fill templates.
  - **Payment Handler:** Stripe interaction.
  - **Ministry Manager:** Orchestrates the flow.
- **Data Flow:**
  1. User submits form -> `Intake API`.
  2. Data saved to DB (Status: PENDING_PAYMENT).
  3. User redirected to Stripe Checkout.
  4. Stripe Webhook -> `Payment Handler` -> Update DB (Status: PAID).
  5. `Ministry Manager` triggers `Doc Generator`.
  6. Documents generated -> Saved to storage.
  7. `Ministry Manager` requests email delivery via `email-automation-system`.
- **Integration:**
  - Stripe API.
  - `email-automation-system`.
  - `registry`.

## 4. 🔌 API SPECIFICATION
Base URL: `/api/v1`

- `POST /intake`: Submit church details. Returns `intake_id` and `checkout_url`.
- `GET /intake/{id}`: Check status.
- `POST /webhooks/stripe`: Handle payment events.
- `GET /products`: List available formation packages.

**UDC Endpoints:**
- `GET /health`
- `GET /capabilities`
- `GET /state`
- `GET /dependencies`
- `POST /message`

## 5. 💾 DATABASE DESIGN
**Tables (PostgreSQL):**

- **intakes**
  - `id` (UUID, PK)
  - `church_name` (String)
  - `trustee_data` (JSONB) - Encrypted
  - `address_data` (JSONB)
  - `status` (Enum: PENDING, PAID, GENERATING, COMPLETED, FAILED)
  - `payment_id` (String) - Stripe Session ID
  - `created_at` (Timestamp)
  - `updated_at` (Timestamp)

- **documents**
  - `id` (UUID, PK)
  - `intake_id` (UUID, FK)
  - `type` (String) - e.g., "bylaws", "articles"
  - `file_path` (String) - Internal storage path
  - `generated_at` (Timestamp)

## 6. 🎨 UI/UX REQUIREMENTS
- **Landing Page:** Clean, trustworthy design explaining the 508c1a benefits.
- **Questionnaire:** Multi-step form with progress bar.
- **Checkout:** Seamless transition to Stripe.
- **Success Page:** "Your documents are being prepared" message.

## 7. 🔐 SECURITY CONSIDERATIONS
- **PII Protection:** Trustee SSNs/Addresses must be encrypted at rest (Fernet/AES).
- **Payment Security:** Never store raw credit card info; rely on Stripe Checkout.
- **Webhook Verification:** Verify Stripe signatures to prevent spoofing.

## 8. ✅ TESTING STRATEGY
- **Unit Tests:**
  - Test template rendering with various inputs.
  - Test PII encryption/decryption logic.
- **Integration Tests:**
  - Mock Stripe API for successful/failed payments.
  - Verify email trigger workflow.
- **E2E:**
  - Full flow from Form Submit -> Webhook -> Document Generation.

## 9. 📦 DEPLOYMENT PLAN
- **Docker:** Standard Python 3.11 slim image.
- **Env Vars:**
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `ENCRYPTION_KEY`
  - `DATABASE_URL`
  - `EMAIL_SERVICE_URL`

## 10. 🛠️ BUILDER INSTRUCTIONS
1. Clone repo and `cd church-guidance-ministry`.
2. `python3 -m venv venv && source venv/bin/activate`.
3. `pip install -r requirements.txt`.
4. Set up local Stripe CLI for webhook forwarding (`stripe listen`).
5. `uvicorn app.main:app --reload`.
6. Test intake flow with Postman or provided HTML frontend.

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
- [ ] UDC endpoints implemented
- [ ] README.md with setup instructions
- [ ] Environment variables documented
- [ ] Local testing successful
- [ ] Code committed to repository

---

## 🎓 WHAT YOU'LL LEARN
By completing this mission:
- Building fintech integrations (Stripe).
- Automating legal document assembly.
- Handling sensitive PII securely.
- Event-driven architecture (webhooks).

---

**Original Idea:** "Spec for Church Guidance Ministry"  
**Mission ID:** M012  
**Generated:** 2025-11-23

🚀 **Let's build something awesome!**

