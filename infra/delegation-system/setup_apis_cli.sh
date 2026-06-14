#!/bin/bash
# One-time API setup - Run everything through CLI/this interface

echo "🔧 API SETUP - Command-Line Driven"
echo "===================================="
echo ""
echo "This script will set up all APIs so you can manage everything"
echo "through this interface (no web UIs needed after setup)."
echo ""

# Check if running on server or local
if [ -f "/root/delegation-system" ]; then
    BASE="/root/delegation-system"
else
    BASE="/Users/jamessunheart/Development/delegation-system"
fi

CRED_DIR="$BASE/api-credentials"
mkdir -p "$CRED_DIR"
chmod 700 "$CRED_DIR"

echo "📁 Credentials will be stored in: $CRED_DIR"
echo ""

# ============================================================================
# 1. STRIPE API (Payment Processing)
# ============================================================================
echo "1️⃣  STRIPE API SETUP"
echo "--------------------"
echo ""
echo "Stripe CLI allows command-line payment management."
echo ""
echo "Steps:"
echo "  a) Install Stripe CLI:"
echo "     brew install stripe/stripe-cli/stripe"
echo ""
echo "  b) Login (opens browser ONCE for OAuth):"
echo "     stripe login"
echo ""
echo "  c) Get API keys:"
echo "     stripe listen --print-secret"
echo ""
echo "After setup, you can:"
echo "  - Create products: stripe products create --name='Premium' --default-price-data.currency=usd --default-price-data.unit-amount=750000"
echo "  - Create payment links: stripe payment_links create --line-items[0][price]=price_xxx"
echo "  - View payments: stripe charges list"
echo ""
read -p "Press Enter when Stripe CLI is set up..."

# ============================================================================
# 2. VERCEL CLI (Landing Page Hosting)
# ============================================================================
echo ""
echo "2️⃣  VERCEL CLI SETUP"
echo "--------------------"
echo ""
echo "Vercel CLI allows command-line deployments."
echo ""
echo "Steps:"
echo "  a) Install Vercel CLI:"
echo "     npm install -g vercel"
echo ""
echo "  b) Login (opens browser ONCE for OAuth):"
echo "     vercel login"
echo ""
echo "After setup, you can:"
echo "  - Deploy: cd landing-page && vercel --prod"
echo "  - Check status: vercel ls"
echo ""
read -p "Press Enter when Vercel CLI is set up..."

# ============================================================================
# 3. FACEBOOK ADS API
# ============================================================================
echo ""
echo "3️⃣  FACEBOOK ADS API SETUP"
echo "--------------------"
echo ""
echo "Facebook Marketing API allows programmatic ad creation."
echo ""
echo "⚠️  Requirements:"
echo "   - Facebook Business Manager account"
echo "   - Business verification (1-3 days)"
echo "   - Developer app created"
echo ""
echo "Steps:"
echo "  a) Create Business Manager: business.facebook.com"
echo "  b) Create app: developers.facebook.com/apps"
echo "  c) Get access token (I'll provide script)"
echo ""
echo "For now, I'll create the automation script."
echo "You can run it after verification completes."
echo ""
echo "Creating Facebook Ads automation script..."

cat > "$BASE/create_facebook_ad.py" << 'EOFPYTHON'
#!/usr/bin/env python3
"""
Create Facebook Ad via API - Run from command line
Usage: ./create_facebook_ad.py --budget 100 --copy "ad_copy.json"
"""
import os
import sys
import json
import argparse
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative

def create_ad_campaign(budget, ad_copy_file):
    # Load credentials
    with open('/root/delegation-system/api-credentials/facebook.json', 'r') as f:
        creds = json.load(f)

    # Initialize API
    FacebookAdsApi.init(
        app_id=creds['app_id'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    )

    # Load ad copy
    with open(ad_copy_file, 'r') as f:
        ad_copy = json.load(f)

    account = AdAccount(creds['ad_account_id'])

    # Create Campaign
    campaign = account.create_campaign(params={
        'name': f'White Rock Ministry - {ad_copy["tier"]}',
        'objective': 'OUTCOME_LEADS',
        'status': 'PAUSED',  # Start paused for review
    })
    print(f"✅ Campaign created: {campaign['id']}")

    # Create Ad Set
    adset = account.create_ad_set(params={
        'name': f'AdSet - {ad_copy["variation"]}',
        'campaign_id': campaign['id'],
        'daily_budget': int(budget * 100),  # cents
        'billing_event': 'IMPRESSIONS',
        'optimization_goal': 'LEAD_GENERATION',
        'bid_amount': 1000,  # $10 CPM
        'targeting': {
            'age_min': 30,
            'age_max': 65,
            'genders': [1, 2],
            'geo_locations': {'countries': ['US']},
            'interests': [
                {'id': '6003139266461', 'name': 'Entrepreneurship'},
                {'id': '6003195547998', 'name': 'Financial planning'},
            ]
        },
        'status': 'PAUSED',
    })
    print(f"✅ Ad Set created: {adset['id']}")

    # Create Ad Creative
    creative = account.create_ad_creative(params={
        'name': f'Creative - {ad_copy["headline"]}',
        'object_story_spec': {
            'page_id': creds['page_id'],
            'link_data': {
                'link': ad_copy['landing_page_url'],
                'message': ad_copy['body'],
                'name': ad_copy['headline'],
                'call_to_action': {
                    'type': 'LEARN_MORE',
                    'value': {'link': ad_copy['landing_page_url']}
                }
            }
        }
    })
    print(f"✅ Creative created: {creative['id']}")

    # Create Ad
    ad = account.create_ad(params={
        'name': f'Ad - {ad_copy["variation"]}',
        'adset_id': adset['id'],
        'creative': {'creative_id': creative['id']},
        'status': 'PAUSED',
    })
    print(f"✅ Ad created: {ad['id']}")

    print("\n🎉 Facebook ad created successfully!")
    print(f"Campaign ID: {campaign['id']}")
    print(f"\nTo activate, run:")
    print(f"  ./manage_facebook_ads.py --activate {campaign['id']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=float, required=True, help='Daily budget in USD')
    parser.add_argument('--copy', required=True, help='Path to ad copy JSON file')
    args = parser.parse_args()

    create_ad_campaign(args.budget, args.copy)
EOFPYTHON

chmod +x "$BASE/create_facebook_ad.py"
echo "✅ Created: create_facebook_ad.py"

# ============================================================================
# 4. GOOGLE ADS API
# ============================================================================
echo ""
echo "4️⃣  GOOGLE ADS API SETUP"
echo "--------------------"
echo ""
echo "Google Ads API allows programmatic ad creation."
echo ""
echo "⚠️  Requirements:"
echo "   - Google Ads account"
echo "   - $50 spend history (manual ads first)"
echo "   - Developer token (applied via Google)"
echo ""
echo "Creating Google Ads automation script..."

cat > "$BASE/create_google_ad.py" << 'EOFPYTHON'
#!/usr/bin/env python3
"""
Create Google Ad via API - Run from command line
Usage: ./create_google_ad.py --budget 100 --copy "ad_copy.json"
"""
import os
import sys
import json
import argparse
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def create_ad_campaign(budget, ad_copy_file):
    # Load credentials
    client = GoogleAdsClient.load_from_storage('/root/delegation-system/api-credentials/google_ads.yaml')

    # Load ad copy
    with open(ad_copy_file, 'r') as f:
        ad_copy = json.load(f)

    customer_id = os.environ.get('GOOGLE_ADS_CUSTOMER_ID')

    # Create Campaign
    campaign_service = client.get_service('CampaignService')
    campaign_operation = client.get_type('CampaignOperation')
    campaign = campaign_operation.create
    campaign.name = f'White Rock Ministry - {ad_copy["tier"]}'
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.manual_cpc.enhanced_cpc_enabled = True
    campaign.campaign_budget = f'customers/{customer_id}/campaignBudgets/XXX'

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id,
        operations=[campaign_operation]
    )
    print(f"✅ Campaign created: {response.results[0].resource_name}")

    print("\n🎉 Google ad created successfully!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=float, required=True)
    parser.add_argument('--copy', required=True)
    args = parser.parse_args()

    create_ad_campaign(args.budget, args.copy)
EOFPYTHON

chmod +x "$BASE/create_google_ad.py"
echo "✅ Created: create_google_ad.py"

# ============================================================================
# 5. UNIFIED AD LAUNCHER
# ============================================================================
echo ""
echo "5️⃣  CREATING UNIFIED AD LAUNCHER"
echo "--------------------"
echo ""
echo "This script lets you launch ads on ALL platforms with one command."
echo ""

cat > "$BASE/launch_campaign.sh" << 'EOFSH'
#!/bin/bash
# Launch complete ad campaign across all platforms
# Usage: ./launch_campaign.sh --tier premium --budget 100

TIER=""
BUDGET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --tier) TIER="$2"; shift 2 ;;
        --budget) BUDGET="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "$TIER" ] || [ -z "$BUDGET" ]; then
    echo "Usage: ./launch_campaign.sh --tier premium --budget 100"
    exit 1
fi

echo "🚀 LAUNCHING CAMPAIGN"
echo "====================="
echo "Tier: $TIER"
echo "Budget: \$$BUDGET"
echo ""

# Step 1: Generate ad copy with AI
echo "1️⃣  Generating ad copy with AI..."
python3 << EOPYTHON
from marketing_assembly_line import MarketingAssemblyLine
import json

assembly_line = MarketingAssemblyLine()

# Generate Facebook ad
fb_ad = assembly_line.content_generator.generate_ad_copy(
    objective=f'White Rock Ministry {TIER.title()} Membership',
    platform='facebook',
    variation='A'
)

# Generate Google ad
google_ad = assembly_line.content_generator.generate_ad_copy(
    objective=f'White Rock Ministry {TIER.title()} Membership',
    platform='google',
    variation='A'
)

# Generate landing page
landing = assembly_line.content_generator.generate_landing_page_copy(
    tier='$TIER',
    variation='A'
)

# Save for ad creation
with open('/tmp/fb_ad_copy.json', 'w') as f:
    json.dump(fb_ad, f)

with open('/tmp/google_ad_copy.json', 'w') as f:
    json.dump(google_ad, f)

print("✅ Ad copy generated!")
EOPYTHON

# Step 2: Deploy landing page
echo ""
echo "2️⃣  Deploying landing page..."
cd /root/delegation-system/landing-page 2>/dev/null || echo "⚠️  Landing page not found (create first)"

# Step 3: Create Facebook ad
echo ""
echo "3️⃣  Creating Facebook ad..."
if [ -f "/root/delegation-system/api-credentials/facebook.json" ]; then
    ./create_facebook_ad.py --budget $BUDGET --copy /tmp/fb_ad_copy.json
else
    echo "⚠️  Facebook API not configured yet"
    echo "   Ad copy saved to: /tmp/fb_ad_copy.json"
    echo "   You can create manually or run setup first"
fi

# Step 4: Create Google ad
echo ""
echo "4️⃣  Creating Google ad..."
if [ -f "/root/delegation-system/api-credentials/google_ads.yaml" ]; then
    ./create_google_ad.py --budget $BUDGET --copy /tmp/google_ad_copy.json
else
    echo "⚠️  Google Ads API not configured yet"
    echo "   Ad copy saved to: /tmp/google_ad_copy.json"
fi

echo ""
echo "✅ CAMPAIGN LAUNCH COMPLETE!"
echo ""
echo "Next steps:"
echo "  1. Review ads in Facebook/Google dashboards"
echo "  2. Activate campaigns when ready"
echo "  3. Monitor: ./monitor_campaigns.sh"
EOFSH

chmod +x "$BASE/launch_campaign.sh"
echo "✅ Created: launch_campaign.sh"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ CLI SETUP COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "You can now manage everything through this interface:"
echo ""
echo "📝 Generate content + launch campaign:"
echo "   ./launch_campaign.sh --tier premium --budget 100"
echo ""
echo "💳 Manage payments:"
echo "   stripe products create ..."
echo "   stripe charges list"
echo ""
echo "🚀 Deploy landing page:"
echo "   cd landing-page && vercel --prod"
echo ""
echo "📊 Monitor campaigns:"
echo "   ./monitor_campaigns.sh (coming next)"
echo ""
echo "════════════════════════════════════════════════════════════"
