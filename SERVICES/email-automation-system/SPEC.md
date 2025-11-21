# 📧 Email Automation System - Technical Specification

**Service Name:** `email-automation`
**Purpose:** Autonomous email drip campaigns triggered by customer lifecycle events
**Priority:** Week 1 Build (Highest ROI)
**Infinite Scale:** Yes - every customer triggers sequences automatically

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Email Automation System                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │  I MATCH DB  │───────▶│ Event Stream │                  │
│  │  (Postgres)  │        │   (Redis)    │                  │
│  └──────────────┘        └──────┬───────┘                  │
│                                  │                           │
│                                  ▼                           │
│                         ┌─────────────────┐                 │
│                         │  Celery Worker  │                 │
│                         │  (Task Queue)   │                 │
│                         └────────┬────────┘                 │
│                                  │                           │
│                    ┌─────────────┼─────────────┐            │
│                    ▼             ▼             ▼            │
│            ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│            │ Template │  │ Sequence │  │  Send    │        │
│            │ Renderer │  │  Engine  │  │  Engine  │        │
│            └──────────┘  └──────────┘  └────┬─────┘        │
│                                              │              │
│                                              ▼              │
│                                    ┌──────────────────┐    │
│                                    │   SendGrid API   │    │
│                                    └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Email Sequences

### Sequence 1: New Customer Journey
**Trigger:** Customer created in I MATCH database

```
Email 1: Confirmation (Immediate)
  Subject: "🎯 We're finding your perfect match, {name}!"
  Content: Thank you, what happens next, 24-hour timeline
  CTA: None (just confirmation)

Email 2: Match Sent (When matches found - usually <24hr)
  Subject: "✨ Your perfect matches are here!"
  Content: 3 matched providers, why they're great, next steps
  CTA: Book consultation with providers

Email 3: Check-in (3 days after match sent, if no booking)
  Subject: "Quick question about your matches"
  Content: Did matches look good? Need different ones? How can we help?
  CTA: Reply or book consultation

Email 4: Re-engagement (7 days, if still no action)
  Subject: "Still looking for {service_type}?"
  Content: Matches expire in 3 days, can refresh, or provide feedback
  CTA: Book or request new matches

Email 5: Win-back (14 days, if no action)
  Subject: "We'd love your feedback"
  Content: What didn't work? Survey link. Offer to help differently.
  CTA: Feedback form
```

### Sequence 2: Consultation Booked
**Trigger:** Customer books consultation with provider

```
Email 1: Booking Confirmation (Immediate)
  Subject: "✅ Consultation confirmed with {provider_name}"
  Content: Date/time, what to prepare, provider bio
  CTA: Add to calendar

Email 2: Pre-consultation (24 hours before)
  Subject: "Tomorrow: Consultation with {provider_name}"
  Content: Reminder, what to ask, meeting link
  CTA: Prepare questions

Email 3: Post-consultation (24 hours after)
  Subject: "How was your consultation?"
  Content: Request feedback, ask if moving forward, offer help
  CTA: Feedback + next steps
```

### Sequence 3: Engagement Confirmed
**Trigger:** Customer confirms engagement with provider

```
Email 1: Engagement Confirmation (Immediate)
  Subject: "🎉 Congratulations on your match!"
  Content: What happens next, support available, project timeline
  CTA: None (celebration)

Email 2: Mid-project Check-in (30 days)
  Subject: "How's your {service_type} project going?"
  Content: See if everything is going well, offer support
  CTA: Contact us if issues

Email 3: Project Complete Request (60 days)
  Subject: "Would you share your success story?"
  Content: Request testimonial, offer to feature them
  CTA: Submit testimonial

Email 4: Referral Request (7 days after testimonial)
  Subject: "Know anyone who needs what you found?"
  Content: Referral incentive, unique link, easy sharing
  CTA: Share referral link
```

---

## 🔧 Technical Implementation

### Stack
```python
# Core
FastAPI==0.104.1
Celery==5.3.4
Redis==5.0.1
SQLAlchemy==2.0.23

# Email
sendgrid==6.10.0
jinja2==3.1.2  # Template rendering

# Database
psycopg2-binary==2.9.9  # Postgres

# Monitoring
sentry-sdk==1.38.0
prometheus-client==0.19.0
```

### Directory Structure
```
email-automation/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── celery_app.py        # Celery configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── email_event.py   # Event tracking
│   │   └── email_log.py     # Send log
│   ├── sequences/
│   │   ├── __init__.py
│   │   ├── new_customer.py
│   │   ├── consultation.py
│   │   └── engagement.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── send_email.py
│   │   └── process_event.py
│   ├── templates/
│   │   ├── email_base.html  # Base template
│   │   ├── new_customer/
│   │   ├── consultation/
│   │   └── engagement/
│   └── utils/
│       ├── __init__.py
│       ├── sendgrid.py
│       └── template_renderer.py
├── tests/
├── docker-compose.yml
└── requirements.txt
```

### Database Schema
```sql
-- Email events tracking
CREATE TABLE email_events (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,  -- 'customer_created', 'match_sent', etc.
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Email send log
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    sequence_name VARCHAR(100) NOT NULL,
    email_number INTEGER NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    sendgrid_message_id VARCHAR(255),
    status VARCHAR(50),  -- 'sent', 'delivered', 'opened', 'clicked', 'bounced'
    UNIQUE(customer_id, sequence_name, email_number)
);

-- Email sequence state
CREATE TABLE email_sequence_state (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    sequence_name VARCHAR(100) NOT NULL,
    current_step INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    paused BOOLEAN DEFAULT FALSE,
    UNIQUE(customer_id, sequence_name)
);

-- Indexes for performance
CREATE INDEX idx_email_events_customer ON email_events(customer_id);
CREATE INDEX idx_email_events_type ON email_events(event_type);
CREATE INDEX idx_email_logs_customer ON email_logs(customer_id);
CREATE INDEX idx_sequence_state_customer ON email_sequence_state(customer_id);
```

---

## 🔌 Integration Points

### 1. I MATCH Database Integration
**Listen for events using Postgres NOTIFY/LISTEN**

```python
# In I MATCH service, after customer created:
def create_customer(customer_data):
    customer = Customer(**customer_data)
    db.add(customer)
    db.commit()

    # Trigger email automation
    db.execute(
        "NOTIFY email_events, :payload",
        {"payload": json.dumps({
            "event": "customer_created",
            "customer_id": customer.id,
            "data": {...}
        })}
    )
```

### 2. Event Stream Processing
**Celery worker listens for events**

```python
@celery.task
def process_event(event_data):
    """Process email trigger event"""
    event_type = event_data['event']
    customer_id = event_data['customer_id']

    # Route to appropriate sequence
    if event_type == 'customer_created':
        start_new_customer_sequence.delay(customer_id)
    elif event_type == 'match_sent':
        send_match_notification.delay(customer_id, event_data)
    elif event_type == 'consultation_booked':
        start_consultation_sequence.delay(customer_id, event_data)
    # ... etc
```

### 3. SendGrid Integration
**Send emails via API**

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content, template_data):
    """Send email via SendGrid"""
    message = Mail(
        from_email='hello@fullpotential.com',
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    # Add tracking
    message.tracking_settings = TrackingSettings(
        click_tracking=ClickTracking(enable=True),
        open_tracking=OpenTracking(enable=True)
    )

    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)

    return response
```

---

## 📧 Email Template System

### Base Template (Jinja2)
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; background: white; }
        .cta-button { background: #667eea; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 6px; display: inline-block; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ header_title }}</h1>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        <div class="footer">
            <p>{{ footer_text }}</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Example Specific Template
```html
{% extends "email_base.html" %}

{% block content %}
<p>Hi {{ first_name }},</p>

<p>Great news! We found <strong>{{ matches_count }} perfect matches</strong> for your {{ service_type }} needs.</p>

<h2>Your Top Matches:</h2>

{% for match in top_matches %}
<div style="border-left: 3px solid #667eea; padding-left: 15px; margin: 20px 0;">
    <h3>{{ match.provider_name }}</h3>
    <p><strong>Match Score:</strong> {{ match.score }}%</p>
    <p>{{ match.bio }}</p>
    <a href="{{ match.booking_url }}" class="cta-button">Book Consultation</a>
</div>
{% endfor %}

<p>All consultations are <strong>100% free</strong>. Book with all 3 to find your perfect fit!</p>

<p>Questions? Just reply to this email.</p>

<p>Best,<br>The I MATCH Team</p>
{% endblock %}
```

---

## ⚙️ Configuration & Environment

```bash
# .env
SENDGRID_API_KEY=SG.xxxxx
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/imatch
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
SENTRY_DSN=https://xxx@sentry.io/xxx

# Email Settings
FROM_EMAIL=hello@fullpotential.com
FROM_NAME=I MATCH Team
UNSUBSCRIBE_URL=https://fullpotential.com/unsubscribe

# Sequence Timing (in seconds)
CHECK_IN_DELAY=259200  # 3 days
REENGAGEMENT_DELAY=604800  # 7 days
WINBACK_DELAY=1209600  # 14 days
```

---

## 🚀 Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  email-api:
    build: .
    ports:
      - "8500:8500"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
    depends_on:
      - redis

  celery-worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  celery-beat:
    build: .
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Systemd Service
```ini
[Unit]
Description=Email Automation Service
After=network.target

[Service]
Type=simple
User=fpai
WorkingDirectory=/opt/fpai/email-automation
ExecStart=/usr/local/bin/docker-compose up
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📊 Metrics & Monitoring

### Key Metrics to Track
```python
# Email Performance
- emails_sent_total (counter)
- emails_delivered_total (counter)
- emails_opened_total (counter)
- emails_clicked_total (counter)
- emails_bounced_total (counter)

# Sequence Performance
- sequence_started_total (counter)
- sequence_completed_total (counter)
- sequence_conversion_rate (gauge)

# Timing
- email_send_duration_seconds (histogram)
- sequence_step_delay_seconds (histogram)
```

### Prometheus Endpoint
```python
from prometheus_client import Counter, Histogram, make_asgi_app

emails_sent = Counter('emails_sent_total', 'Total emails sent', ['sequence', 'step'])
email_duration = Histogram('email_send_duration_seconds', 'Time to send email')

@app.get("/metrics")
async def metrics():
    return make_asgi_app()
```

---

## ✅ Success Criteria

### Week 1 (MVP)
- [ ] 3 email sequences implemented
- [ ] SendGrid integration working
- [ ] Events triggering emails automatically
- [ ] Basic tracking (sent, delivered)

### Week 2 (Optimization)
- [ ] A/B testing framework
- [ ] Advanced tracking (opens, clicks)
- [ ] Unsubscribe handling
- [ ] Error recovery

### Month 1 (Scale)
- [ ] 10+ email sequences
- [ ] Auto-optimization based on performance
- [ ] 1000+ emails sent automatically
- [ ] 40%+ open rate, 15%+ click rate

---

## 🎯 Expected Impact

**Conversion Improvement:**
- Current: ~15% form submission → booking
- With automation: ~40% form submission → booking
- **Improvement: +167%**

**Operational Efficiency:**
- Current: Manual follow-up required
- With automation: Zero human effort
- **Time saved: ~10 hours/week**

**Revenue Impact:**
- 25% more conversions = 25% more revenue
- Month 1: +$4,500 additional revenue
- Month 12: +$54,000 additional revenue

---

**BUILD TIME:** 12-16 hours (2 days)
**MAINTENANCE:** <1 hour/month
**INFINITE SCALE:** Yes - handles 10,000+ customers automatically

**Next:** Build this first, then move to next system (Social Auto-Poster)
