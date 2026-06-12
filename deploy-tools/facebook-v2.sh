#!/bin/bash
# Facebook/Meta Advertising Tool v2 for Adam OpenClaw
# Full ads pipeline: Campaign → Ad Set → Ad → Monitoring → Optimization

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"
[ -f "/opt/fpai/cora-loop/.env" ] && source "/opt/fpai/cora-loop/.env"

META_TOKEN="${META_TOKEN:-EAARD6gE7ftIBQpXI0m9sqoVgXNWLRvozSsKNfWzQfQvTZAWGK42yjNI3VgzPvdGaxlFCZBzoAepWz7LuWq4Dre9F8NNaUQZBljZBLo8SllgoVlxvIXwe7X48fBHPyWYtBCanmTvbeYXZBqJq2n0mFxJwN1mEYtWwly5dGPHR11AF8pouOymYloKXnMp36O0xw0QZDZD}"
GRAPH_API="https://graph.facebook.com/v19.0"
ACTIVITY_LOG="/opt/fpai/logs/openclaw_activity.log"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

log_activity() {
    mkdir -p "$(dirname "$ACTIVITY_LOG")"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [FACEBOOK] $1" >> "$ACTIVITY_LOG"
}

tg_notify() {
    [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ] && return 0
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$msg" \
        -d parse_mode="Markdown" > /dev/null 2>&1 || true
}

meta_api() {
    local method="${1:-GET}"
    local endpoint="$2"
    shift 2
    local url="${GRAPH_API}${endpoint}"
    if [[ "$url" == *"?"* ]]; then
        url="${url}&access_token=${META_TOKEN}"
    else
        url="${url}?access_token=${META_TOKEN}"
    fi

    if [ "$method" = "GET" ]; then
        curl -s "$url" "$@"
    else
        curl -s -X "$method" "$url" "$@"
    fi
}

parse_json() {
    python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print('Error: Invalid JSON response')
    sys.exit(1)
$1
"
}

show_help() {
    cat << 'HELP'
Facebook/Meta Advertising Tool v2

Usage: facebook.sh <command> [args...]

ACCOUNT & SETUP:
  me                              - Account info and permissions
  accounts                        - List ad accounts
  pages                           - List managed pages

CAMPAIGNS:
  campaigns <ad_account_id>       - List all campaigns
  create-campaign <ad_account_id> <name> <objective> <daily_budget_usd>
  pause-campaign <campaign_id>    - Pause a campaign
  resume-campaign <campaign_id>   - Resume a campaign

AD SETS:
  adsets <ad_account_id>          - List all ad sets
  create-adset <campaign_id> <ad_account_id> <name> <daily_budget_usd> [targeting_preset]
  pause-adset <adset_id>          - Pause an ad set
  resume-adset <adset_id>         - Resume an ad set

ADS:
  ads <ad_account_id>             - List all ads
  create-ad <adset_id> <ad_account_id> <page_id> <headline> <body> <link_url> [image_url]

FULL PIPELINE:
  launch <ad_account_id> <page_id> <daily_budget_usd>
                                  - Create complete campaign + ad set + ad in one shot
                                    Targets entrepreneurs/creators, links to /score

ANALYTICS & MONITORING:
  insights <ad_account_id> [days] - Detailed performance metrics (default: 7 days)
  campaign-insights <campaign_id> [days] - Per-campaign breakdown
  budget <ad_account_id>          - Budget status and spend rate
  cpl <ad_account_id> [days]      - Cost per lead analysis

OPTIMIZATION:
  optimize <ad_account_id>        - Auto-pause underperformers, flag winners

ORGANIC:
  post <page_id> <message>        - Post to a page
  post-link <page_id> <msg> <url> - Post with a link

IMAGES:
  upload-image <ad_account_id> <image_path> - Upload image, returns hash for create-ad

Targeting presets: entrepreneurs, creators, highperformers, spiritual, broad
  Edit /opt/fpai/ad-monitor/targeting-config.json to adjust without code changes.
  Config also controls: ad creatives, budget alert thresholds, optimization rules.

Objectives: OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_ENGAGEMENT, OUTCOME_LEADS
HELP
}

TARGETING_CONFIG="/opt/fpai/ad-monitor/targeting-config.json"

get_targeting() {
    local preset="${1:-entrepreneurs}"

    if [ -f "$TARGETING_CONFIG" ]; then
        local result
        result=$(python3 -c "
import json, sys
with open('$TARGETING_CONFIG') as f:
    cfg = json.load(f)
presets = cfg.get('presets', {})
p = presets.get('$preset')
if p:
    print(json.dumps(p))
else:
    print('NOT_FOUND')
" 2>/dev/null)
        if [ -n "$result" ] && [ "$result" != "NOT_FOUND" ]; then
            echo "$result"
            return 0
        fi
    fi

    case "$preset" in
        entrepreneurs)
            cat << 'JSON'
{"geo_locations":{"countries":["US","CA","GB","AU"]},"age_min":25,"age_max":55,"genders":[0],"flexible_spec":[{"interests":[{"id":"6003139266461","name":"Entrepreneurship"},{"id":"6003384248805","name":"Small business"},{"id":"6003271228498","name":"Personal development"},{"id":"6003020834693","name":"Leadership"},{"id":"6003349442552","name":"High performance"}]}],"publisher_platforms":["facebook","instagram"],"facebook_positions":["feed","video_feeds"],"instagram_positions":["stream","explore"]}
JSON
            ;;
        creators)
            cat << 'JSON'
{"geo_locations":{"countries":["US","CA","GB","AU"]},"age_min":22,"age_max":50,"genders":[0],"flexible_spec":[{"interests":[{"id":"6003397425735","name":"Content creation"},{"id":"6003107902433","name":"Creativity"},{"id":"6003249471195","name":"Social media marketing"},{"id":"6003139266461","name":"Entrepreneurship"},{"id":"6003020834693","name":"Self-improvement"}]}],"publisher_platforms":["facebook","instagram"],"facebook_positions":["feed","video_feeds"],"instagram_positions":["stream","explore"]}
JSON
            ;;
        highperformers)
            cat << 'JSON'
{"geo_locations":{"countries":["US","CA","GB","AU"]},"age_min":28,"age_max":55,"genders":[0],"flexible_spec":[{"interests":[{"id":"6003020834693","name":"Self-improvement"},{"id":"6003384248805","name":"Coaching"},{"id":"6003139266461","name":"Entrepreneurship"},{"id":"6003020834693","name":"Leadership"},{"id":"6003349442552","name":"Mindfulness"}]}],"publisher_platforms":["facebook","instagram"],"facebook_positions":["feed","video_feeds"],"instagram_positions":["stream","explore"]}
JSON
            ;;
        spiritual)
            cat << 'JSON'
{"geo_locations":{"countries":["US","CA","GB","AU"]},"age_min":25,"age_max":60,"genders":[0],"flexible_spec":[{"interests":[{"id":"6003349442552","name":"Mindfulness"},{"id":"6003017718045","name":"Meditation"},{"id":"6003020834693","name":"Spirituality"},{"id":"6003020834693","name":"Self-improvement"},{"id":"6003384248805","name":"Coaching"}]}],"publisher_platforms":["facebook","instagram"],"facebook_positions":["feed","video_feeds"],"instagram_positions":["stream","explore"]}
JSON
            ;;
        broad)
            cat << 'JSON'
{"geo_locations":{"countries":["US","CA","GB","AU"]},"age_min":25,"age_max":55,"genders":[0],"flexible_spec":[{"interests":[{"id":"6003020834693","name":"Self-improvement"},{"id":"6003139266461","name":"Entrepreneurship"},{"id":"6003384248805","name":"Coaching"},{"id":"6003397425735","name":"Motivation"}]}],"publisher_platforms":["facebook"],facebook_positions":["feed"],"instagram_positions":["stream"]}
JSON
            ;;
        *)
            echo "Unknown preset: $preset. Edit $TARGETING_CONFIG to add custom presets." >&2
            return 1
            ;;
    esac
}

get_creative() {
    local variant="${1:-ad3}"
    if [ -f "$TARGETING_CONFIG" ]; then
        python3 -c "
import json
with open('$TARGETING_CONFIG') as f:
    cfg = json.load(f)
v = cfg.get('ad_creatives', {}).get('variants', {}).get('$variant')
if v:
    print(v.get('headline', ''))
    print(v.get('body', ''))
    print(v.get('link', 'https://fullpotential.ai/score'))
    print(v.get('cta', 'LEARN_MORE'))
" 2>/dev/null
        return 0
    fi
    echo "Something's still missing."
    echo "High performer. Objectively successful. Still feels like something's missing. Take this 2-minute assessment and discover what's beneath the surface."
    echo "https://fullpotential.ai/score"
    echo "LEARN_MORE"
}

case "${1:-}" in
    "me")
        echo "FACEBOOK ACCOUNT INFO"
        echo "====================="
        meta_api GET "/me?fields=id,name,email" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
else:
    print('Name:', data.get('name', 'N/A'))
    print('ID:', data.get('id', 'N/A'))
    print('Email:', data.get('email', 'N/A'))
"
        echo ""
        echo "PERMISSIONS (ads-related)"
        meta_api GET "/me/permissions" | parse_json "
if 'data' in data:
    ads_perms = [p['permission'] for p in data['data'] if p.get('status') == 'granted' and ('ads' in p['permission'] or 'business' in p['permission'] or 'page' in p['permission'])]
    print('Granted:', ', '.join(ads_perms))
"
        ;;

    "accounts")
        echo "AD ACCOUNTS"
        echo "==========="
        meta_api GET "/me/adaccounts?fields=id,name,account_status,currency,balance,amount_spent,spend_cap" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for acc in data['data']:
        status = {1: 'Active', 2: 'Disabled', 3: 'Unsettled', 7: 'Pending Review', 9: 'In Grace Period', 100: 'Pending Closure', 101: 'Closed'}.get(acc.get('account_status'), 'Unknown')
        spent = float(acc.get('amount_spent', 0)) / 100
        balance = float(acc.get('balance', 0)) / 100
        print()
        print('Account:', acc.get('name', 'Unnamed'))
        print('  ID:', acc.get('id'))
        print('  Status:', status)
        print('  Currency:', acc.get('currency', 'USD'))
        print('  Balance: \$%.2f' % balance)
        print('  Total Spent: \$%.2f' % spent)
        cap = acc.get('spend_cap')
        if cap:
            print('  Spend Cap: \$%.2f' % (float(cap)/100))
else:
    print('No ad accounts found.')
    print('')
    print('The system user needs to be assigned to an ad account.')
    print('Go to Business Manager > Settings > System Users > assign ad account.')
"
        ;;

    "pages")
        echo "MANAGED PAGES"
        echo "============="
        meta_api GET "/me/accounts?fields=id,name,category,fan_count" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for page in data['data']:
        print()
        print('Page:', page.get('name'))
        print('  ID:', page.get('id'))
        print('  Category:', page.get('category', 'N/A'))
        print('  Followers:', page.get('fan_count', 0))
else:
    print('No pages found.')
    print('')
    print('The system user needs page access.')
    print('Go to Business Manager > Settings > System Users > assign pages.')
"
        ;;

    "campaigns")
        AD_ACCOUNT="${2:?Usage: facebook.sh campaigns <ad_account_id>}"
        echo "CAMPAIGNS FOR $AD_ACCOUNT"
        echo "========================="
        meta_api GET "/${AD_ACCOUNT}/campaigns?fields=id,name,status,objective,daily_budget,lifetime_budget,created_time" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for c in data['data']:
        print()
        print('Campaign:', c.get('name'))
        print('  ID:', c.get('id'))
        print('  Status:', c.get('status'))
        print('  Objective:', c.get('objective', 'N/A'))
        db = c.get('daily_budget')
        if db: print('  Daily Budget: \$%.2f' % (float(db)/100))
        lb = c.get('lifetime_budget')
        if lb: print('  Lifetime Budget: \$%.2f' % (float(lb)/100))
        print('  Created:', c.get('created_time', 'N/A'))
else:
    print('No campaigns found')
"
        ;;

    "create-campaign")
        AD_ACCOUNT="${2:?Usage: facebook.sh create-campaign <ad_account_id> <name> <objective> <daily_budget_usd>}"
        NAME="${3:?Missing campaign name}"
        OBJECTIVE="${4:?Missing objective (OUTCOME_TRAFFIC, OUTCOME_LEADS, etc.)}"
        BUDGET="${5:?Missing daily budget in USD}"
        BUDGET_CENTS=$((BUDGET * 100))
        log_activity "Creating campaign: $NAME (\$$BUDGET/day)"
        meta_api POST "/${AD_ACCOUNT}/campaigns" \
            -d "name=$NAME" \
            -d "objective=$OBJECTIVE" \
            -d "status=PAUSED" \
            -d "special_ad_categories=[]" \
            -d "daily_budget=$BUDGET_CENTS" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
else:
    cid = data.get('id')
    print('Campaign created!')
    print('ID:', cid)
    print('Status: PAUSED (use resume-campaign to activate)')
"
        ;;

    "pause-campaign")
        CID="${2:?Usage: facebook.sh pause-campaign <campaign_id>}"
        log_activity "Pausing campaign: $CID"
        meta_api POST "/${CID}" -d "status=PAUSED" | parse_json "
if data.get('success'): print('Campaign paused')
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    "resume-campaign")
        CID="${2:?Usage: facebook.sh resume-campaign <campaign_id>}"
        log_activity "Resuming campaign: $CID"
        meta_api POST "/${CID}" -d "status=ACTIVE" | parse_json "
if data.get('success'): print('Campaign activated')
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    "adsets")
        AD_ACCOUNT="${2:?Usage: facebook.sh adsets <ad_account_id>}"
        echo "AD SETS FOR $AD_ACCOUNT"
        echo "======================="
        meta_api GET "/${AD_ACCOUNT}/adsets?fields=id,name,status,campaign_id,daily_budget,optimization_goal,billing_event,targeting" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for a in data['data']:
        print()
        print('Ad Set:', a.get('name'))
        print('  ID:', a.get('id'))
        print('  Status:', a.get('status'))
        print('  Campaign:', a.get('campaign_id'))
        db = a.get('daily_budget')
        if db: print('  Daily Budget: \$%.2f' % (float(db)/100))
        print('  Optimization:', a.get('optimization_goal', 'N/A'))
        t = a.get('targeting', {})
        geo = t.get('geo_locations', {}).get('countries', [])
        age = '%s-%s' % (t.get('age_min', '?'), t.get('age_max', '?'))
        print('  Targeting: %s, age %s' % (', '.join(geo), age))
else:
    print('No ad sets found')
"
        ;;

    "create-adset")
        CAMPAIGN_ID="${2:?Usage: facebook.sh create-adset <campaign_id> <ad_account_id> <name> <daily_budget_usd> [targeting_preset]}"
        AD_ACCOUNT="${3:?Missing ad_account_id}"
        NAME="${4:?Missing ad set name}"
        BUDGET="${5:?Missing daily budget in USD}"
        PRESET="${6:-entrepreneurs}"
        BUDGET_CENTS=$((BUDGET * 100))

        TARGETING=$(get_targeting "$PRESET")
        START_TIME=$(date -u -d "+1 hour" +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || date -u -v+1H +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%S%z)

        log_activity "Creating ad set: $NAME (preset: $PRESET, \$$BUDGET/day)"

        RESPONSE=$(meta_api POST "/${AD_ACCOUNT}/adsets" \
            -d "name=$NAME" \
            -d "campaign_id=$CAMPAIGN_ID" \
            -d "daily_budget=$BUDGET_CENTS" \
            -d "billing_event=IMPRESSIONS" \
            -d "optimization_goal=LINK_CLICKS" \
            -d "bid_strategy=LOWEST_COST_WITHOUT_CAP" \
            -d "targeting=$TARGETING" \
            -d "status=PAUSED" \
            -d "start_time=$START_TIME")

        echo "$RESPONSE" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
    em = data['error'].get('error_user_msg', '')
    if em: print('Detail:', em)
else:
    print('Ad Set created!')
    print('ID:', data.get('id'))
    print('Targeting preset:', '$PRESET')
    print('Status: PAUSED')
"
        ;;

    "pause-adset")
        ASID="${2:?Usage: facebook.sh pause-adset <adset_id>}"
        log_activity "Pausing ad set: $ASID"
        meta_api POST "/${ASID}" -d "status=PAUSED" | parse_json "
if data.get('success'): print('Ad set paused')
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    "resume-adset")
        ASID="${2:?Usage: facebook.sh resume-adset <adset_id>}"
        log_activity "Resuming ad set: $ASID"
        meta_api POST "/${ASID}" -d "status=ACTIVE" | parse_json "
if data.get('success'): print('Ad set activated')
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    "ads")
        AD_ACCOUNT="${2:?Usage: facebook.sh ads <ad_account_id>}"
        echo "ADS FOR $AD_ACCOUNT"
        echo "==================="
        meta_api GET "/${AD_ACCOUNT}/ads?fields=id,name,status,adset_id,creative" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for ad in data['data']:
        print()
        print('Ad:', ad.get('name'))
        print('  ID:', ad.get('id'))
        print('  Status:', ad.get('status'))
        print('  Ad Set:', ad.get('adset_id'))
else:
    print('No ads found')
"
        ;;

    "create-ad")
        ADSET_ID="${2:?Usage: facebook.sh create-ad <adset_id> <ad_account_id> <page_id> <headline> <body> <link_url> [image_hash]}"
        AD_ACCOUNT="${3:?Missing ad_account_id}"
        PAGE_ID="${4:?Missing page_id}"
        HEADLINE="${5:?Missing headline}"
        BODY="${6:?Missing body text}"
        LINK_URL="${7:?Missing link URL}"
        IMAGE_HASH="${8:-}"

        log_activity "Creating ad: $HEADLINE -> $LINK_URL"

        if [ -n "$IMAGE_HASH" ]; then
            CREATIVE_SPEC="{\"object_story_spec\":{\"page_id\":\"${PAGE_ID}\",\"link_data\":{\"message\":\"${BODY}\",\"link\":\"${LINK_URL}\",\"name\":\"${HEADLINE}\",\"call_to_action\":{\"type\":\"LEARN_MORE\"},\"image_hash\":\"${IMAGE_HASH}\"}}}"
        else
            CREATIVE_SPEC="{\"object_story_spec\":{\"page_id\":\"${PAGE_ID}\",\"link_data\":{\"message\":\"${BODY}\",\"link\":\"${LINK_URL}\",\"name\":\"${HEADLINE}\",\"call_to_action\":{\"type\":\"LEARN_MORE\"}}}}"
        fi

        meta_api POST "/${AD_ACCOUNT}/ads" \
            -d "name=FP Score - ${HEADLINE}" \
            -d "adset_id=$ADSET_ID" \
            -d "creative=$CREATIVE_SPEC" \
            -d "status=PAUSED" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
    em = data['error'].get('error_user_msg', '')
    if em: print('Detail:', em)
else:
    print('Ad created!')
    print('ID:', data.get('id'))
    print('Status: PAUSED (activate parent ad set + campaign to go live)')
"
        ;;

    "launch")
        AD_ACCOUNT="${2:?Usage: facebook.sh launch <ad_account_id> <page_id> <daily_budget_usd>}"
        PAGE_ID="${3:?Missing page_id}"
        BUDGET="${4:?Missing daily budget in USD}"
        BUDGET_CENTS=$((BUDGET * 100))

        echo "========================================"
        echo " FULL POTENTIAL AD PIPELINE LAUNCHER"
        echo "========================================"
        echo ""
        echo "Budget: \$$BUDGET/day"
        echo "Target: Entrepreneurs, creators, high-performers"
        echo "Landing: https://fullpotential.ai/score"
        echo ""

        log_activity "LAUNCH: Full pipeline, \$$BUDGET/day"

        # Step 1: Create Campaign
        echo "Step 1/4: Creating campaign..."
        CAMP_RESPONSE=$(meta_api POST "/${AD_ACCOUNT}/campaigns" \
            -d "name=Full Potential Score - $(date +%Y%m%d)" \
            -d "objective=OUTCOME_TRAFFIC" \
            -d "status=PAUSED" \
            -d "special_ad_categories=[]")

        CAMPAIGN_ID=$(echo "$CAMP_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

        if [ -z "$CAMPAIGN_ID" ]; then
            echo "$CAMP_RESPONSE" | parse_json "print('Error:', data.get('error',{}).get('message','Unknown error creating campaign'))"
            exit 1
        fi
        echo "  Campaign ID: $CAMPAIGN_ID"

        # Step 2: Create Ad Sets (3 targeting presets for A/B testing)
        echo ""
        echo "Step 2/4: Creating ad sets (3 audience segments)..."
        THIRD=$((BUDGET_CENTS / 3))

        ADSET_IDS=()
        for PRESET in entrepreneurs creators highperformers; do
            TARGETING=$(get_targeting "$PRESET")
            AS_RESPONSE=$(meta_api POST "/${AD_ACCOUNT}/adsets" \
                -d "name=FP Score - ${PRESET}" \
                -d "campaign_id=$CAMPAIGN_ID" \
                -d "daily_budget=$THIRD" \
                -d "billing_event=IMPRESSIONS" \
                -d "optimization_goal=LINK_CLICKS" \
                -d "bid_strategy=LOWEST_COST_WITHOUT_CAP" \
                -d "targeting=$TARGETING" \
                -d "status=PAUSED")

            ASID=$(echo "$AS_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
            if [ -n "$ASID" ]; then
                echo "  Ad Set ($PRESET): $ASID"
                ADSET_IDS+=("$ASID:$PRESET")
            else
                echo "  Ad Set ($PRESET): FAILED"
                echo "$AS_RESPONSE" | parse_json "print('    Error:', data.get('error',{}).get('message','?'))"
            fi
        done

        # Step 3: Create Ads (one per ad set, loading creatives from config)
        echo ""
        echo "Step 3/4: Creating ads..."

        # Load creatives from config if available, otherwise use defaults
        # Ad 3 (Kai's primary) is always first
        if [ -f "$TARGETING_CONFIG" ]; then
            mapfile -t AD_VARIANTS < <(python3 -c "
import json
with open('$TARGETING_CONFIG') as f:
    cfg = json.load(f)
variants = cfg.get('ad_creatives', {}).get('variants', {})
order = ['ad3', 'ad1', 'ad2']
for key in order:
    v = variants.get(key, {})
    if v:
        print('%s|%s|%s' % (v.get('headline',''), v.get('body',''), v.get('link','https://fullpotential.ai/score')))
" 2>/dev/null)
        fi

        if [ ${#AD_VARIANTS[@]} -eq 0 ]; then
            AD_VARIANTS=(
                "Something's still missing.|High performer. Objectively successful. Still feels like something's missing. Take this 2-minute assessment and discover what's beneath the surface.|https://fullpotential.ai/score"
                "What's Your Full Potential Score?|Most people operate at 40-60% of their capacity. 9 dimensions. 2 minutes. One score that reveals where you're thriving and where you're leaving potential on the table.|https://fullpotential.ai/score"
                "Are You Living at Full Potential?|Entrepreneurs and creators: this free assessment reveals the architecture beneath your performance. Your Full Potential Score awaits.|https://fullpotential.ai/score"
            )
        fi

        AD_IDX=0
        for ENTRY in "${ADSET_IDS[@]}"; do
            ASID="${ENTRY%%:*}"
            PRESET="${ENTRY##*:}"
            IFS='|' read -r HEADLINE BODY LINK <<< "${AD_VARIANTS[$AD_IDX]}"

            CREATIVE_SPEC="{\"object_story_spec\":{\"page_id\":\"${PAGE_ID}\",\"link_data\":{\"message\":\"${BODY}\",\"link\":\"${LINK}\",\"name\":\"${HEADLINE}\",\"call_to_action\":{\"type\":\"LEARN_MORE\"}}}}"

            AD_RESPONSE=$(meta_api POST "/${AD_ACCOUNT}/ads" \
                -d "name=FP Score - ${PRESET} - v1" \
                -d "adset_id=$ASID" \
                -d "creative=$CREATIVE_SPEC" \
                -d "status=PAUSED")

            AD_ID=$(echo "$AD_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
            if [ -n "$AD_ID" ]; then
                echo "  Ad ($PRESET): $AD_ID"
            else
                echo "  Ad ($PRESET): FAILED"
                echo "$AD_RESPONSE" | parse_json "print('    Error:', data.get('error',{}).get('message','?'))"
            fi
            AD_IDX=$((AD_IDX + 1))
        done

        # Step 4: Summary
        echo ""
        echo "Step 4/4: Pipeline summary"
        echo "=========================="
        echo "Campaign: $CAMPAIGN_ID (PAUSED)"
        echo "Ad Sets: ${#ADSET_IDS[@]} created across 3 audiences"
        echo "Budget: \$$BUDGET/day split across segments"
        echo ""
        echo "To activate: facebook.sh resume-campaign $CAMPAIGN_ID"
        echo "  (this activates the campaign; also resume each ad set)"
        for ENTRY in "${ADSET_IDS[@]}"; do
            ASID="${ENTRY%%:*}"
            PRESET="${ENTRY##*:}"
            echo "  facebook.sh resume-adset $ASID  # $PRESET"
        done
        echo ""
        echo "Monitor: facebook.sh insights $AD_ACCOUNT"

        tg_notify "📊 *Ad Pipeline Created*
Campaign: $CAMPAIGN_ID
Segments: entrepreneurs, creators, highperformers
Budget: \$$BUDGET/day
Status: PAUSED — ready to activate"
        ;;

    "insights")
        AD_ACCOUNT="${2:?Usage: facebook.sh insights <ad_account_id> [days]}"
        DAYS="${3:-7}"
        echo "PERFORMANCE INSIGHTS (Last $DAYS Days)"
        echo "======================================="
        meta_api GET "/${AD_ACCOUNT}/insights?date_preset=last_${DAYS}d&fields=impressions,reach,clicks,ctr,cpc,cpm,spend,actions,cost_per_action_type&level=account" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    d = data['data'][0]
    print('Impressions:', d.get('impressions', 0))
    print('Reach:', d.get('reach', 0))
    print('Clicks:', d.get('clicks', 0))
    ctr = d.get('ctr', '0')
    print('CTR: %s%%' % ctr)
    print('CPC: \$%s' % d.get('cpc', '0'))
    print('CPM: \$%s' % d.get('cpm', '0'))
    print('Spend: \$%s' % d.get('spend', '0'))
    actions = d.get('actions', [])
    if actions:
        print('')
        print('ACTIONS:')
        for a in actions:
            print('  %s: %s' % (a.get('action_type','?'), a.get('value','0')))
    costs = d.get('cost_per_action_type', [])
    if costs:
        print('')
        print('COST PER ACTION:')
        for c in costs:
            print('  %s: \$%s' % (c.get('action_type','?'), c.get('value','0')))
else:
    print('No data for this period')
"
        ;;

    "campaign-insights")
        CID="${2:?Usage: facebook.sh campaign-insights <campaign_id> [days]}"
        DAYS="${3:-7}"
        echo "CAMPAIGN INSIGHTS (Last $DAYS Days)"
        echo "===================================="
        meta_api GET "/${CID}/insights?date_preset=last_${DAYS}d&fields=campaign_name,impressions,reach,clicks,ctr,cpc,spend,actions&level=adset&breakdowns=age,gender" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for d in data['data'][:20]:
        print('%s | %s | imp:%s | clicks:%s | CTR:%s%% | spend:\$%s' % (
            d.get('age','?'), d.get('gender','?'),
            d.get('impressions','0'), d.get('clicks','0'),
            d.get('ctr','0'), d.get('spend','0')))
else:
    print('No data for this period')
"
        ;;

    "budget")
        AD_ACCOUNT="${2:?Usage: facebook.sh budget <ad_account_id>}"
        echo "BUDGET STATUS"
        echo "============="
        meta_api GET "/${AD_ACCOUNT}?fields=name,balance,amount_spent,spend_cap,currency" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
else:
    balance = float(data.get('balance', 0)) / 100
    spent = float(data.get('amount_spent', 0)) / 100
    cap = data.get('spend_cap')
    print('Account:', data.get('name', 'N/A'))
    print('Balance: \$%.2f' % balance)
    print('Total Spent: \$%.2f' % spent)
    if cap:
        cap_f = float(cap) / 100
        remaining = cap_f - spent
        print('Spend Cap: \$%.2f' % cap_f)
        print('Remaining: \$%.2f' % remaining)
"
        # Also check active campaign budgets
        echo ""
        echo "ACTIVE CAMPAIGNS:"
        meta_api GET "/${AD_ACCOUNT}/campaigns?fields=name,daily_budget,status&effective_status=[%22ACTIVE%22]" | parse_json "
if 'data' in data:
    total_daily = 0
    for c in data['data']:
        db = float(c.get('daily_budget', 0)) / 100
        total_daily += db
        print('  %s: \$%.2f/day (%s)' % (c.get('name','?'), db, c.get('status','?')))
    if total_daily > 0:
        print('')
        print('Total daily spend rate: \$%.2f/day' % total_daily)
        print('Projected monthly: \$%.2f' % (total_daily * 30))
"
        ;;

    "cpl")
        AD_ACCOUNT="${2:?Usage: facebook.sh cpl <ad_account_id> [days]}"
        DAYS="${3:-7}"
        echo "COST PER LEAD ANALYSIS (Last $DAYS Days)"
        echo "========================================="
        meta_api GET "/${AD_ACCOUNT}/insights?date_preset=last_${DAYS}d&fields=campaign_name,spend,actions,cost_per_action_type&level=campaign" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    for d in data['data']:
        spend = float(d.get('spend', 0))
        leads = 0
        cpl = 0
        for a in d.get('actions', []):
            if a.get('action_type') in ('lead', 'offsite_conversion.fb_pixel_lead', 'link_click'):
                leads += int(a.get('value', 0))
        if leads > 0 and spend > 0:
            cpl = spend / leads
        print('%s: \$%.2f spent, %d leads, \$%.2f CPL' % (d.get('campaign_name','?'), spend, leads, cpl))
else:
    print('No data for this period')
"
        ;;

    "optimize")
        AD_ACCOUNT="${2:?Usage: facebook.sh optimize <ad_account_id>}"
        echo "AUTO-OPTIMIZATION ANALYSIS (CPL-based)"
        echo "======================================="
        meta_api GET "/${AD_ACCOUNT}/insights?date_preset=last_3d&fields=adset_name,adset_id,impressions,clicks,ctr,spend,actions,cost_per_action_type&level=adset" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
elif 'data' in data and data['data']:
    results = []
    for d in data['data']:
        spend = float(d.get('spend', 0))
        clicks = int(d.get('clicks', 0))
        link_clicks = 0
        leads = 0
        for a in d.get('actions', []):
            if a.get('action_type') == 'link_click':
                link_clicks += int(a.get('value', 0))
            if a.get('action_type') in ('lead', 'offsite_conversion.fb_pixel_lead'):
                leads += int(a.get('value', 0))
        conversions = leads if leads > 0 else link_clicks
        cpl = spend / conversions if conversions > 0 else float('inf')
        results.append({
            'name': d.get('adset_name', '?'),
            'id': d.get('adset_id', '?'),
            'spend': spend,
            'clicks': clicks,
            'link_clicks': link_clicks,
            'leads': leads,
            'conversions': conversions,
            'cpl': cpl,
            'ctr': float(d.get('ctr', 0))
        })

    viable = [r for r in results if r['spend'] >= 5 and r['conversions'] > 0]
    if not viable:
        print('Not enough data yet (need 3+ days and \$5+ spend per ad set)')
        print('')
        for r in results:
            print('  %s: \$%.2f spent, %d clicks, %d conversions' % (r['name'], r['spend'], r['clicks'], r['conversions']))
    else:
        best_cpl = min(r['cpl'] for r in viable)
        print('Best CPL: \$%.2f' % best_cpl)
        print('Pause threshold: \$%.2f (2x best)' % (best_cpl * 2))
        print('')
        for r in sorted(viable, key=lambda x: x['cpl']):
            ratio = r['cpl'] / best_cpl if best_cpl > 0 else 0
            if r['cpl'] >= best_cpl * 2:
                status = 'PAUSE'
                tag = '✗'
            elif r['cpl'] <= best_cpl * 1.2:
                status = 'WINNER'
                tag = '✓'
            else:
                status = 'OK'
                tag = '—'
            print('%s %s %s' % (tag, status, r['name']))
            print('  CPL: \$%.2f (%.1fx best) | Spend: \$%.2f | Clicks: %d | Leads: %d' % (r['cpl'], ratio, r['spend'], r['link_clicks'], r['leads']))
            if status == 'PAUSE':
                print('  → RECOMMENDATION: facebook.sh pause-adset %s' % r['id'])
            print('')
else:
    print('No data — campaigns may not have run yet')
"
        ;;

    "upload-image")
        AD_ACCOUNT="${2:?Usage: facebook.sh upload-image <ad_account_id> <image_path>}"
        IMAGE_PATH="${3:?Missing image file path}"
        if [ ! -f "$IMAGE_PATH" ]; then
            echo "Error: File not found: $IMAGE_PATH"
            exit 1
        fi
        log_activity "Uploading image: $IMAGE_PATH"
        curl -s -X POST "${GRAPH_API}/${AD_ACCOUNT}/adimages" \
            -F "access_token=${META_TOKEN}" \
            -F "filename=@${IMAGE_PATH}" | parse_json "
if 'error' in data:
    print('Error:', data['error'].get('message', 'Unknown'))
else:
    images = data.get('images', {})
    for name, info in images.items():
        print('Image uploaded!')
        print('Hash:', info.get('hash', 'N/A'))
        print('Use this hash with create-ad: facebook.sh create-ad <adset_id> <account_id> <page_id> <headline> <body> <link> %s' % info.get('hash', ''))
"
        ;;

    "post")
        PAGE_ID="${2:?Usage: facebook.sh post <page_id> <message>}"
        MESSAGE="${3:?Missing message}"
        PAGE_TOKEN=$(meta_api GET "/${PAGE_ID}?fields=access_token" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
        if [ -z "$PAGE_TOKEN" ]; then
            echo "Error: Could not get page access token"
            exit 1
        fi
        curl -s -X POST "${GRAPH_API}/${PAGE_ID}/feed" \
            -d "message=$MESSAGE" \
            -d "access_token=$PAGE_TOKEN" | parse_json "
if 'id' in data: print('Posted! ID:', data['id'])
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    "post-link")
        PAGE_ID="${2:?Usage: facebook.sh post-link <page_id> <message> <url>}"
        MESSAGE="${3:?Missing message}"
        LINK="${4:?Missing URL}"
        PAGE_TOKEN=$(meta_api GET "/${PAGE_ID}?fields=access_token" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
        curl -s -X POST "${GRAPH_API}/${PAGE_ID}/feed" \
            -d "message=$MESSAGE" \
            -d "link=$LINK" \
            -d "access_token=$PAGE_TOKEN" | parse_json "
if 'id' in data: print('Posted with link! ID:', data['id'])
else: print('Error:', data.get('error', {}).get('message', 'Unknown'))
"
        ;;

    *)
        show_help
        ;;
esac
