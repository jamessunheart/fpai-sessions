#!/usr/bin/env python3
"""
Generate VA tasks for API acquisition
Creates detailed instructions and submission portal
"""

import json
from datetime import datetime
from api_discovery_agent import APIDiscoveryAgent

def create_va_task(api_info: dict, task_id: str, credentials: dict) -> dict:
    """Create a VA task for API signup"""
    
    task = {
        "task_id": task_id,
        "created": datetime.now().isoformat(),
        "status": "pending",
        "priority": "high" if api_info['free_tier'] else "medium",
        "estimated_time": "10-15 minutes",
        "payment": "$20",
        "api_name": api_info['name'],
        "capability": "",  # Will be set by caller
        
        "instructions": f"""
# Task: Sign Up for {api_info['name']} API

## Overview
**Service:** {api_info['name']} by {api_info['provider']}
**Purpose:** {api_info.get('purpose', 'Content generation')}
**Free Tier:** {'Yes' if api_info['free_tier'] else 'No'}
**Pricing:** {api_info['pricing']}
**Estimated Time:** 10-15 minutes
**Payment:** $20 upon completion

---

## Credentials Provided

You will use these credentials to sign up:

**Email:** {credentials.get('email', 'PROVIDED_SEPARATELY')}
**Phone:** {credentials.get('phone', 'PROVIDED_SEPARATELY')}
**Company Name:** {credentials.get('company_name', 'White Rock Ministry')}

---

## Step-by-Step Instructions

### Step 1: Go to Signup Page
Navigate to: **{api_info['signup_url']}**

### Step 2: Create Account
- Click "Sign Up" or "Get Started"
- Use the email provided above
- Create a strong password (save it!)
- Complete any verification (check email, phone, etc.)

### Step 3: Complete Profile
- Company/Organization: {credentials.get('company_name', 'White Rock Ministry')}
- Use Case: Content creation and marketing
- Industry: Financial Services / Education

### Step 4: Navigate to API Section
- Look for "API", "Developer", "API Keys", or "Integrations"
- Usually in Settings or Dashboard

### Step 5: Generate API Key
- Click "Generate API Key" or "Create New Key"
- Copy the FULL API key (starts with something like "sk-" or similar)
- **IMPORTANT:** Save this immediately - some services only show it once!

### Step 6: Submit Results
Go to: **http://198.54.123.234:8020/api-submit**

Enter:
- API Service: {api_info['name']}
- API Key: [paste the full key]
- Your Name: [your name]
- Notes: Any issues or important info

---

## Important Notes

- ✅ Use the credentials provided (email/phone)
- ✅ Keep password secure - save it somewhere safe
- ✅ Copy API key IMMEDIATELY when shown
- ✅ Some services only show API key once
- ⚠️ {'Credit card MAY be required (but not charged for free tier)' if api_info.get('requires_credit_card') else 'No credit card needed'}
- ⚠️ If you encounter CAPTCHA, solve it normally
- ⚠️ If verification email required, check the provided email inbox

---

## Expected Result

You should receive an API key that looks like:
- Format: Usually starts with `sk-`, `api_`, or similar
- Length: Usually 30-60 characters
- Example: `sk-abc123def456...` (yours will be different)

---

## Troubleshooting

**Can't receive verification email?**
- Check spam folder
- Contact us for alternative email

**Account creation fails?**
- Try different username
- Contact us if persistent issues

**Can't find API key section?**
- Look for "Developer", "API", "Integration" in menu
- Contact us with screenshot if stuck

---

## Payment

Once you submit the API key and we verify it works:
- $20 payment via PayPal or Venmo
- Usually verified within 1 hour

---

## Questions?

Contact: [SUPPORT_EMAIL]
Or submit with notes and we'll help!
""",
        
        "deliverables": [
            "API Key (full string)",
            "Account password (encrypted)",
            "Any special instructions or notes"
        ],
        
        "verification": {
            "test_endpoint": api_info.get('test_endpoint'),
            "expected_response": "success"
        }
    }
    
    return task

def main():
    print("🎯 VA TASK GENERATOR - API Acquisition")
    print("=" * 60)
    
    # Get API recommendations
    agent = APIDiscoveryAgent()
    
    capabilities = {
        "image_generation": "Generate professional ad images",
        "video_generation": "Create short-form video ads",
        "voice_generation": "Add voice-overs to videos",
        "music_generation": "Add background music to content"
    }
    
    # Ask for credentials
    print("\n📋 What credentials can you provide to help VAs sign up?")
    print("\nWe need:")
    print("  1. Email address (for account creation)")
    print("  2. Phone number (optional, some services require it)")
    print("  3. Company name (optional)")
    
    credentials = {
        "email": "PROVIDED_BY_USER",
        "phone": "PROVIDED_BY_USER",
        "company_name": "White Rock Ministry"
    }
    
    tasks = []
    task_files = []
    
    for capability, purpose in capabilities.items():
        api = agent.get_recommended_api(capability, prefer_free=True)
        
        if not api:
            continue
        
        api['purpose'] = purpose
        task_id = f"api_{capability}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = create_va_task(api, task_id, credentials)
        task['capability'] = capability
        tasks.append(task)
        
        # Save task to file
        task_file = f"/Users/jamessunheart/Development/agents/services/api-hub/tasks/{task_id}.json"
        task_files.append(task_file)
        
        print(f"\n✅ Created task: {api['name']}")
        print(f"   Capability: {capability}")
        print(f"   Free Tier: {'Yes' if api['free_tier'] else 'No'}")
        print(f"   Signup URL: {api['signup_url']}")
    
    # Save all tasks
    import os
    os.makedirs("/Users/jamessunheart/Development/agents/services/api-hub/tasks", exist_ok=True)
    
    for task, task_file in zip(tasks, task_files):
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)
        
        # Also create a markdown instruction file
        md_file = task_file.replace('.json', '_INSTRUCTIONS.md')
        with open(md_file, 'w') as f:
            f.write(task['instructions'])
    
    # Create summary
    summary = {
        "total_tasks": len(tasks),
        "total_payment": len(tasks) * 20,
        "estimated_time": "30-60 minutes total",
        "tasks": [
            {
                "service": t['api_name'],
                "capability": t['capability'],
                "free_tier": tasks[i]['instructions'].split('**Free Tier:** ')[1].split('\n')[0]
            }
            for i, t in enumerate(tasks)
        ]
    }
    
    with open("/Users/jamessunheart/Development/agents/services/api-hub/tasks/SUMMARY.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"  Total Tasks: {len(tasks)}")
    print(f"  Total Payment: ${len(tasks) * 20}")
    print(f"  Estimated Time: 30-60 minutes")
    print(f"\n  Tasks created in: /Users/jamessunheart/Development/agents/services/api-hub/tasks/")
    
    print("\n📋 Next Steps:")
    print("  1. Provide credentials (email, phone)")
    print("  2. Post tasks to Upwork/Fiverr or send to VAs")
    print("  3. VAs complete signups and submit API keys")
    print("  4. System validates and adds keys to vault")
    print("  5. Content generation pipeline goes live!")

if __name__ == "__main__":
    main()
