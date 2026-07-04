import os, json, urllib.request, urllib.parse
TOK=os.environ["META_ACCESS_TOKEN"]; ACT=os.environ["META_AD_ACCOUNT_ID"]
PAGE="332461670707476"  # Full Potential
BASE="https://graph.facebook.com/v18.0"
def post(path, data):
    data["access_token"]=TOK
    req=urllib.request.Request(f"{BASE}/{path}", data=urllib.parse.urlencode(data).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:
        return {"ERROR": json.load(e)}
# 1. Campaign (paused)
c=post(f"{ACT}/campaigns", {"name":"FP Assessment — Savings v1","objective":"OUTCOME_TRAFFIC",
    "status":"PAUSED","special_ad_categories":json.dumps([]),"is_adset_budget_sharing_enabled":"false"})
print("campaign:", json.dumps(c)[:200])
if "id" not in c: raise SystemExit
cid=c["id"]
# 2. Ad Set (paused, $10/day, US business owners, landing-page-view optimized)
targeting={"geo_locations":{"countries":["US"]},"age_min":25,"age_max":64,
  "interests":[{"id":"6003371567474","name":"Small business"}],"targeting_automation":{"advantage_audience":0}}
a=post(f"{ACT}/adsets", {"name":"US business owners","campaign_id":cid,
    "daily_budget":"1000","billing_event":"IMPRESSIONS","optimization_goal":"LANDING_PAGE_VIEWS",
    "bid_strategy":"LOWEST_COST_WITHOUT_CAP","targeting":json.dumps(targeting),"status":"PAUSED"})
print("adset:", json.dumps(a)[:250])
if "id" not in a: raise SystemExit
aid=a["id"]
# 3. Creative (savings frame → /assessment)
story={"page_id":PAGE,"link_data":{
  "message":"Most businesses lose 15-30% of their software budget and hundreds of hours to work AI should be doing. The free Full Potential Assessment finds your three biggest leaks in 48 hours - no pitch, the findings are yours either way.",
  "link":"https://fullpotential.com/assessment?utm_campaign=fp-assess-savings-v1&utm_source=meta",
  "name":"Find the money leaking out of your business",
  "description":"Free Allocation Score + your 3 highest-value opportunities.",
  "call_to_action":{"type":"LEARN_MORE","value":{"link":"https://fullpotential.com/assessment"}}}}
cr=post(f"{ACT}/adcreatives", {"name":"savings-v1","object_story_spec":json.dumps(story)})
print("creative:", json.dumps(cr)[:200])
if "id" not in cr: raise SystemExit
crid=cr["id"]
# 4. Ad (paused)
ad=post(f"{ACT}/ads", {"name":"savings-v1","adset_id":aid,
    "creative":json.dumps({"creative_id":crid}),"status":"PAUSED"})
print("ad:", json.dumps(ad)[:200])
print("DONE_IDS", json.dumps({"campaign":cid,"adset":aid,"creative":crid,"ad":ad.get("id")}))
