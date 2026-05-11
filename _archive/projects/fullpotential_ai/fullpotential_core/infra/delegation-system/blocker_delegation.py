#!/usr/bin/env python3
"""
Blocker Delegation System
Automatically delegates blocker tasks to VAs and manages credentials
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from credential_vault import CredentialVault


class BlockerDelegation:
    """Manages delegation of blocker tasks to VAs"""

    def __init__(self):
        self.vault = CredentialVault()
        self.base_dir = Path("/root/delegation-system")
        self.tasks_dir = self.base_dir / "blocker-tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_blocker_task(self, blocker_name: str, task_template: str) -> Dict:
        """Create a new blocker task for VA delegation"""

        task = {
            "id": f"blocker_{blocker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "blocker": blocker_name,
            "status": "pending",
            "template": task_template,
            "created_at": datetime.now().isoformat(),
            "assigned_to": None,
            "completed_at": None,
            "credentials_stored": False
        }

        task_file = self.tasks_dir / f"{task['id']}.json"
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)

        print(f"✅ Blocker task created: {task['id']}")
        return task

    def get_pending_blockers(self) -> List[Dict]:
        """Get all pending blocker tasks"""
        blockers = []
        for task_file in self.tasks_dir.glob("blocker_*.json"):
            with open(task_file) as f:
                task = json.load(f)
                if task['status'] == 'pending':
                    blockers.append(task)
        return sorted(blockers, key=lambda x: x['created_at'])

    def mark_blocker_complete(self, task_id: str, credentials: Dict):
        """Mark blocker as complete and store credentials"""

        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            print(f"❌ Task {task_id} not found")
            return

        with open(task_file) as f:
            task = json.load(f)

        # Store credentials in vault
        blocker_name = task['blocker']
        tier = "tier2_monitored"  # Most API credentials go to tier 2

        self.vault.add_credential(
            tier=tier,
            service=blocker_name,
            credential_data=credentials,
            requester="blocker_delegation_system"
        )

        # Update task
        task['status'] = 'completed'
        task['completed_at'] = datetime.now().isoformat()
        task['credentials_stored'] = True

        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)

        print(f"✅ Blocker {blocker_name} completed!")
        print(f"✅ Credentials stored in {tier}")

        return task


# Blocker task templates
BLOCKER_TEMPLATES = {
    "stripe": """
# TASK: Set up Stripe Payment Processing

## Objective
Create a Stripe account and set up payment processing for White Rock Ministry Premium Membership.

## Steps

1. **Create Stripe Account**
   - Go to: https://stripe.com
   - Click "Sign Up"
   - Use credentials:
     - Email: ops@fullpotential.ai (from credential vault)
     - Create strong password
     - Complete business verification

2. **Set Up Product**
   - Navigate to: Products → Add Product
   - Product name: "White Rock Ministry - Premium Membership"
   - Description: "One-time Premium Membership with full access to trust formation guidance and treasury optimization"
   - Price: $7,500 (one-time payment)
   - Click "Create"

3. **Create Payment Link**
   - Click on the product you just created
   - Click "Create payment link"
   - Settings:
     - Collect customer name: Yes
     - Collect customer email: Yes
     - Collect billing address: Yes
   - Click "Create link"
   - Copy the payment link (looks like: https://buy.stripe.com/xxx)

4. **Get API Keys**
   - Navigate to: Developers → API keys
   - Copy:
     - Publishable key (starts with pk_live_ or pk_test_)
     - Secret key (starts with sk_live_ or sk_test_)

5. **Set Up Webhooks** (Optional for now)
   - Navigate to: Developers → Webhooks
   - Click "Add endpoint"
   - Endpoint URL: https://dashboard.fullpotential.com/webhook/stripe
   - Events to send: Select "payment_intent.succeeded"

## Deliverables

Save these to the credentials system:
```json
{
  "account_email": "ops@fullpotential.ai",
  "account_password": "[password you created]",
  "payment_link": "https://buy.stripe.com/xxx",
  "publishable_key": "pk_live_xxx or pk_test_xxx",
  "secret_key": "sk_live_xxx or sk_test_xxx",
  "webhook_secret": "whsec_xxx (if you set up webhook)"
}
```

## Security Notes
- Use operations credit card from credential vault (tier 2)
- Enable 2FA on Stripe account
- Store all credentials in tier 2 (monitored shared)

## Time Estimate
15-20 minutes

## Questions?
Check Stripe docs: https://stripe.com/docs
""",

    "calendly": """
# TASK: Set up Calendly Booking System

## Objective
Create a Calendly account and set up consultation booking for White Rock Ministry.

## Steps

1. **Create Calendly Account**
   - Go to: https://calendly.com
   - Click "Sign Up"
   - Use credentials:
     - Email: ops@fullpotential.ai
     - Create strong password

2. **Create Event Type**
   - Click "Create Event"
   - Event name: "Free Consultation - White Rock Ministry"
   - Duration: 30 minutes
   - Location: Zoom (or Google Meet)
   - Description: "Discuss your financial sovereignty goals and how White Rock Ministry can help protect and optimize your wealth."

3. **Set Availability**
   - Set your preferred hours (or use default business hours)
   - Add buffer time: 15 minutes between meetings
   - Max bookings per day: 4

4. **Get Booking Link**
   - Click on the event you created
   - Copy the booking link (looks like: https://calendly.com/your-name/consultation)

5. **Get API Key** (Optional)
   - Go to: Integrations & Apps → API & Webhooks
   - Generate Personal Access Token
   - Copy the token

## Deliverables

Save these to the credentials system:
```json
{
  "account_email": "ops@fullpotential.ai",
  "account_password": "[password you created]",
  "booking_link": "https://calendly.com/your-name/consultation",
  "api_token": "[if you generated one]"
}
```

## Security Notes
- Enable 2FA on Calendly account
- Store credentials in tier 2 (monitored shared)

## Time Estimate
10-15 minutes

## Questions?
Check Calendly help: https://help.calendly.com
""",

    "facebook_oauth": """
# TASK: Set up Facebook Ads API Access

## Objective
Create Facebook Business Manager, get OAuth tokens for programmatic ad creation.

## Steps

1. **Create Facebook Business Manager**
   - Go to: https://business.facebook.com
   - Click "Create Account"
   - Business name: "Full Potential AI"
   - Use credentials:
     - Email: ops@fullpotential.ai
     - Create strong password

2. **Add Payment Method**
   - Go to: Business Settings → Payments
   - Add payment method
   - Use operations credit card from credential vault (tier 2)

3. **Create Ad Account**
   - Go to: Business Settings → Ad Accounts
   - Click "Add" → "Create a new ad account"
   - Name: "White Rock Ministry Ads"
   - Time zone: Pacific
   - Currency: USD

4. **Create Facebook App** (For API Access)
   - Go to: https://developers.facebook.com/apps
   - Click "Create App"
   - App type: "Business"
   - App name: "Full Potential AI Marketing"
   - Contact email: ops@fullpotential.ai

5. **Get OAuth Token**
   - In your app, go to: Marketing API → Tools
   - Click "Get Token"
   - Select permissions:
     - ads_management
     - ads_read
     - business_management
   - Copy Access Token (very long string)

6. **Get Account IDs**
   - Business Manager ID: Found in Business Settings → Business Info
   - Ad Account ID: Found in Business Settings → Ad Accounts
   - Page ID: Create a Facebook Page for White Rock Ministry, get ID

## Deliverables

Save these to the credentials system:
```json
{
  "account_email": "ops@fullpotential.ai",
  "account_password": "[password you created]",
  "business_manager_id": "123456789",
  "ad_account_id": "act_123456789",
  "page_id": "123456789",
  "app_id": "123456789",
  "app_secret": "[from app settings]",
  "access_token": "[long OAuth token]"
}
```

## Security Notes
- Enable 2FA on Facebook account
- Token expires - may need to regenerate monthly
- Store in tier 2 (monitored shared)

## Time Estimate
30-45 minutes (includes business verification wait time)

## Questions?
Check docs: https://developers.facebook.com/docs/marketing-apis
""",

    "google_oauth": """
# TASK: Set up Google Ads API Access

## Objective
Create Google Ads account and get OAuth tokens for programmatic ad creation.

## Steps

1. **Create Google Ads Account**
   - Go to: https://ads.google.com
   - Click "Start Now"
   - Use email: ops@fullpotential.ai
   - Follow setup wizard
   - Add payment method (operations card from vault)

2. **Spend $50** (Requirement for API Access)
   - Create a simple test campaign
   - Budget: $50 total
   - Run for a few days
   - This is required before Google grants API access

3. **Apply for API Access**
   - Go to: https://developers.google.com/google-ads/api/docs/first-call/overview
   - Fill out application form
   - Wait for approval (usually 1-2 days)

4. **Create OAuth Credentials**
   - Go to: https://console.cloud.google.com
   - Create new project: "Full Potential AI Marketing"
   - Enable Google Ads API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: http://localhost:8080

5. **Get Tokens**
   - Use OAuth playground or run auth script
   - Get refresh token (doesn't expire)
   - Get client ID and client secret

6. **Get Customer ID**
   - In Google Ads, click top right (your account)
   - Copy Customer ID (10 digits, no dashes)

## Deliverables

Save these to the credentials system:
```json
{
  "account_email": "ops@fullpotential.ai",
  "account_password": "[password you created]",
  "customer_id": "1234567890",
  "client_id": "[from OAuth credentials]",
  "client_secret": "[from OAuth credentials]",
  "refresh_token": "[from OAuth flow]",
  "developer_token": "[from API access approval]"
}
```

## Security Notes
- Enable 2FA on Google account
- Refresh token doesn't expire - keep secure
- Store in tier 2 (monitored shared)

## Time Estimate
60-90 minutes (includes $50 spend requirement and API approval wait)

## Questions?
Check docs: https://developers.google.com/google-ads/api/docs/start
"""
}


def main():
    """Demo: Create blocker delegation tasks"""

    delegation = BlockerDelegation()

    print("\n🚧 BLOCKER DELEGATION SYSTEM")
    print("=" * 70)
    print()

    # Create tasks for each blocker
    blockers = ["stripe", "calendly", "facebook_oauth", "google_oauth"]

    print("Creating delegation tasks for blockers...\n")

    for blocker in blockers:
        task = delegation.create_blocker_task(
            blocker_name=blocker,
            task_template=BLOCKER_TEMPLATES[blocker]
        )

        # Save template to file for VA to view
        template_file = delegation.tasks_dir / f"{task['id']}_instructions.md"
        template_file.write_text(BLOCKER_TEMPLATES[blocker])
        print(f"   Instructions saved: {template_file}")
        print()

    # Show pending blockers
    pending = delegation.get_pending_blockers()

    print(f"\n📋 {len(pending)} BLOCKER TASKS PENDING")
    print("-" * 70)

    for task in pending:
        print(f"  • {task['blocker']}: {task['id']}")

    print()
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review task files in:", delegation.tasks_dir)
    print("  2. Assign to VAs (or do manually)")
    print("  3. When complete, run:")
    print(f"     python3 -c 'from blocker_delegation import BlockerDelegation; ")
    print(f"     d = BlockerDelegation(); ")
    print(f"     d.mark_blocker_complete(\"task_id\", {{credentials}})'")
    print()


if __name__ == "__main__":
    main()
