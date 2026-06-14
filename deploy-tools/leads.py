#!/usr/bin/env python3
"""Lead Generation Pipeline — Find prospects and contacts without asking Sunheart.

Sources:
  1. Apollo.io free tier — find people/emails by title, company, industry
  2. Hunter.io free tier — find emails from domain names
  3. Google Custom Search — find businesses in target verticals
  4. LinkedIn public profiles — basic info scraping (no login)
  5. Facebook Ad Leads — webhook receiver for lead form submissions

Usage:
  leads.py search <query>              — search for leads matching query
  leads.py find-email <name> <company> — find someone's email
  leads.py domain <domain.com>         — find emails at a domain
  leads.py enrich <email>              — enrich a contact with available data
  leads.py list                        — show all leads in database
  leads.py export                      — export leads as CSV
  leads.py stats                       — lead pipeline stats
"""

import json
import os
import sys
import time
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = "/opt/fpai/leads/leads.db"
LOG_PATH = "/opt/fpai/leads/leads.log"

Path("/opt/fpai/leads").mkdir(parents=True, exist_ok=True)


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        company TEXT,
        title TEXT,
        domain TEXT,
        source TEXT,
        industry TEXT,
        location TEXT,
        linkedin_url TEXT,
        phone TEXT,
        score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'new',
        notes TEXT,
        raw_data TEXT,
        created_at TEXT,
        updated_at TEXT,
        UNIQUE(email)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        type TEXT,
        content TEXT,
        created_at TEXT,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )""")
    db.commit()
    return db


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)


def upsert_lead(db, data):
    """Insert or update a lead, return the id."""
    email = data.get("email", "").lower().strip()
    if not email:
        return None

    now = datetime.now(timezone.utc).isoformat()
    existing = db.execute("SELECT id FROM leads WHERE email = ?", (email,)).fetchone()

    if existing:
        updates = []
        values = []
        for field in ["name", "company", "title", "domain", "source", "industry",
                      "location", "linkedin_url", "phone", "notes"]:
            if data.get(field):
                updates.append(f"{field} = ?")
                values.append(data[field])
        if updates:
            updates.append("updated_at = ?")
            values.append(now)
            values.append(existing["id"])
            db.execute(f"UPDATE leads SET {', '.join(updates)} WHERE id = ?", values)
            db.commit()
        return existing["id"]
    else:
        db.execute(
            """INSERT INTO leads (name, email, company, title, domain, source,
               industry, location, linkedin_url, phone, score, status, notes, raw_data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("name", ""),
                email,
                data.get("company", ""),
                data.get("title", ""),
                data.get("domain", ""),
                data.get("source", "unknown"),
                data.get("industry", ""),
                data.get("location", ""),
                data.get("linkedin_url", ""),
                data.get("phone", ""),
                data.get("score", 0),
                "new",
                data.get("notes", ""),
                json.dumps(data.get("raw_data", {})),
                now,
                now,
            ),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


# --- Apollo.io (free tier: 10K records/mo) ---

def apollo_search(query, title_filter=None, limit=25):
    """Search Apollo.io for people matching a query."""
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    params = {
        "q_organization_name": query,
        "page": 1,
        "per_page": min(limit, 25),
    }
    if title_filter:
        params["person_titles"] = [title_filter]

    try:
        resp = requests.post(url, json=params, timeout=30,
                             headers={"Content-Type": "application/json",
                                      "Cache-Control": "no-cache"})
        if resp.status_code == 200:
            data = resp.json()
            return data.get("people", [])
        else:
            log(f"Apollo search failed: {resp.status_code}")
            return []
    except Exception as e:
        log(f"Apollo error: {e}")
        return []


def apollo_enrich_email(email):
    """Enrich a person by email via Apollo."""
    url = "https://api.apollo.io/api/v1/people/match"
    try:
        resp = requests.post(url, json={"email": email}, timeout=15,
                             headers={"Content-Type": "application/json"})
        if resp.status_code == 200:
            return resp.json().get("person", {})
    except Exception as e:
        log(f"Apollo enrich error: {e}")
    return {}


# --- Hunter.io (free: 25 searches/mo) ---

HUNTER_KEY = os.environ.get("HUNTER_API_KEY", "")

def hunter_domain_search(domain):
    """Find emails associated with a domain."""
    if not HUNTER_KEY:
        return []
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_KEY}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("emails", [])
    except Exception as e:
        log(f"Hunter error: {e}")
    return []


def hunter_find_email(first_name, last_name, domain):
    """Find a specific person's email."""
    if not HUNTER_KEY:
        return None
    url = (f"https://api.hunter.io/v2/email-finder?"
           f"domain={domain}&first_name={first_name}&last_name={last_name}&api_key={HUNTER_KEY}")
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("email")
    except Exception as e:
        log(f"Hunter find error: {e}")
    return None


# --- Google Search for prospects ---

def google_search_prospects(query, num=10):
    """Use Google Custom Search to find potential prospects/businesses."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CX", "")

    if not api_key or not cx:
        # Fallback: use DuckDuckGo instant answer API
        try:
            resp = requests.get(
                f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1",
                timeout=10
            )
            data = resp.json()
            results = []
            for r in data.get("RelatedTopics", [])[:num]:
                if isinstance(r, dict) and "Text" in r:
                    results.append({"text": r["Text"], "url": r.get("FirstURL", "")})
            return results
        except:
            return []

    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}&num={num}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("items", [])
    except:
        pass
    return []


# --- LinkedIn Public Scraping (no login, basic) ---

def scrape_linkedin_public(company_name):
    """Scrape basic public LinkedIn company info (no login needed)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    search_url = f"https://www.google.com/search?q=site:linkedin.com/in+{company_name}+CEO+OR+founder+OR+owner"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        # Extract LinkedIn profile URLs from search results
        import re
        urls = re.findall(r'https://www\.linkedin\.com/in/[a-zA-Z0-9-]+', resp.text)
        return list(set(urls))[:10]
    except Exception as e:
        log(f"LinkedIn scrape error: {e}")
        return []


# --- Score leads based on fit ---

def score_lead(lead):
    """Score a lead 0-100 based on fit for Full Potential consulting."""
    score = 20  # Base score for having contact info

    title = (lead.get("title") or "").lower()
    high_value_titles = ["ceo", "founder", "owner", "president", "managing director",
                         "chief", "partner", "principal", "director"]
    if any(t in title for t in high_value_titles):
        score += 30

    industry = (lead.get("industry") or "").lower()
    good_industries = ["consulting", "coaching", "wellness", "health", "retreat",
                       "personal development", "education", "nonprofit", "spiritual",
                       "hospitality", "real estate"]
    if any(i in industry for i in good_industries):
        score += 20

    if lead.get("email"):
        score += 15
    if lead.get("phone"):
        score += 10
    if lead.get("linkedin_url"):
        score += 5

    return min(score, 100)


# --- CLI Commands ---

def cmd_search(query):
    db = get_db()
    print(f"Searching for: {query}")
    print()

    # Apollo search
    people = apollo_search(query)
    if people:
        print(f"Found {len(people)} via Apollo:")
        for p in people:
            email = p.get("email") or ""
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            title = p.get("title", "")
            company = p.get("organization", {}).get("name", "")
            linkedin = p.get("linkedin_url", "")

            lead_data = {
                "name": name, "email": email, "company": company,
                "title": title, "linkedin_url": linkedin,
                "source": "apollo",
                "industry": p.get("organization", {}).get("industry", ""),
                "raw_data": p,
            }
            lead_data["score"] = score_lead(lead_data)

            if email:
                lid = upsert_lead(db, lead_data)
                print(f"  + {name} | {title} @ {company} | {email} | score:{lead_data['score']}")
            else:
                print(f"  - {name} | {title} @ {company} | (no email)")
    else:
        print("No Apollo results.")

    # LinkedIn public search
    print()
    urls = scrape_linkedin_public(query)
    if urls:
        print(f"LinkedIn profiles found: {len(urls)}")
        for u in urls[:5]:
            print(f"  {u}")

    # Google/DDG search for businesses
    print()
    web_results = google_search_prospects(f"{query} CEO founder email contact")
    if web_results:
        print(f"Web results: {len(web_results)}")
        for r in web_results[:5]:
            print(f"  {r.get('text', r.get('title', ''))[:100]}")
            if r.get("url") or r.get("link"):
                print(f"    {r.get('url', r.get('link', ''))}")

    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    print(f"\nTotal leads in database: {total}")
    log(f"Search '{query}' completed")


def cmd_find_email(name, company):
    parts = name.split(None, 1)
    first = parts[0] if parts else name
    last = parts[1] if len(parts) > 1 else ""

    # Try Apollo
    people = apollo_search(company, title_filter=None, limit=10)
    for p in people:
        pname = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip().lower()
        if name.lower() in pname or pname in name.lower():
            email = p.get("email")
            if email:
                print(f"Found: {email} (via Apollo)")
                db = get_db()
                upsert_lead(db, {
                    "name": name, "email": email, "company": company,
                    "title": p.get("title", ""), "source": "apollo",
                    "linkedin_url": p.get("linkedin_url", ""),
                })
                return

    # Try Hunter
    domain = company.lower().replace(" ", "") + ".com"
    email = hunter_find_email(first, last, domain)
    if email:
        print(f"Found: {email} (via Hunter)")
        db = get_db()
        upsert_lead(db, {"name": name, "email": email, "company": company,
                         "domain": domain, "source": "hunter"})
        return

    print(f"Could not find email for {name} at {company}")
    print(f"Try: leads.py domain {domain}")


def cmd_domain(domain):
    db = get_db()
    print(f"Finding emails at {domain}...")

    # Hunter
    emails = hunter_domain_search(domain)
    if emails:
        print(f"Hunter found {len(emails)} emails:")
        for e in emails:
            addr = e.get("value", "")
            name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()
            position = e.get("position", "")
            if addr:
                upsert_lead(db, {
                    "name": name, "email": addr, "domain": domain,
                    "title": position, "source": "hunter",
                })
                print(f"  {addr} — {name} ({position})")
    else:
        print("No Hunter results.")

    # Apollo fallback
    company = domain.split(".")[0]
    people = apollo_search(company, limit=10)
    if people:
        print(f"\nApollo found {len(people)} people:")
        for p in people:
            email = p.get("email", "")
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            if email:
                upsert_lead(db, {
                    "name": name, "email": email, "domain": domain,
                    "company": p.get("organization", {}).get("name", ""),
                    "title": p.get("title", ""), "source": "apollo",
                })
                print(f"  {email} — {name} ({p.get('title', '')})")


def cmd_enrich(email):
    print(f"Enriching {email}...")
    person = apollo_enrich_email(email)
    if person:
        name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
        print(f"  Name: {name}")
        print(f"  Title: {person.get('title', 'unknown')}")
        org = person.get("organization", {})
        print(f"  Company: {org.get('name', 'unknown')}")
        print(f"  Industry: {org.get('industry', 'unknown')}")
        print(f"  LinkedIn: {person.get('linkedin_url', 'unknown')}")
        print(f"  Location: {person.get('city', '')} {person.get('state', '')} {person.get('country', '')}")

        db = get_db()
        upsert_lead(db, {
            "name": name, "email": email,
            "company": org.get("name", ""),
            "title": person.get("title", ""),
            "industry": org.get("industry", ""),
            "linkedin_url": person.get("linkedin_url", ""),
            "location": f"{person.get('city', '')} {person.get('state', '')}",
            "source": "apollo_enrich",
        })
    else:
        print("No enrichment data found.")


def cmd_list():
    db = get_db()
    leads = db.execute(
        "SELECT * FROM leads ORDER BY score DESC, created_at DESC LIMIT 50"
    ).fetchall()
    if not leads:
        print("No leads in database yet.")
        print("Try: leads.py search 'wellness retreat founder'")
        return

    print(f"{'Score':>5} | {'Name':<25} | {'Title':<25} | {'Company':<20} | {'Email':<30} | {'Source'}")
    print("-" * 140)
    for l in leads:
        print(f"{l['score']:>5} | {(l['name'] or ''):<25.25} | {(l['title'] or ''):<25.25} | {(l['company'] or ''):<20.20} | {(l['email'] or ''):<30.30} | {l['source']}")

    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    print(f"\nShowing top 50 of {total} total leads")


def cmd_export():
    db = get_db()
    leads = db.execute("SELECT * FROM leads ORDER BY score DESC").fetchall()
    if not leads:
        print("No leads to export.")
        return

    out = "/opt/fpai/leads/leads_export.csv"
    with open(out, "w") as f:
        f.write("name,email,company,title,industry,location,linkedin,phone,score,source,status\n")
        for l in leads:
            row = [l['name'], l['email'], l['company'], l['title'], l['industry'],
                   l['location'], l['linkedin_url'], l['phone'], str(l['score']),
                   l['source'], l['status']]
            f.write(",".join(f'"{(v or "")}"' for v in row) + "\n")
    print(f"Exported {len(leads)} leads to {out}")


def cmd_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    with_email = db.execute("SELECT COUNT(*) FROM leads WHERE email != ''").fetchone()[0]
    high_score = db.execute("SELECT COUNT(*) FROM leads WHERE score >= 60").fetchone()[0]
    by_source = db.execute("SELECT source, COUNT(*) c FROM leads GROUP BY source ORDER BY c DESC").fetchall()

    print(f"Lead Pipeline Stats")
    print(f"  Total leads:     {total}")
    print(f"  With email:      {with_email}")
    print(f"  High score (60+): {high_score}")
    print(f"\n  By source:")
    for r in by_source:
        print(f"    {r['source']:<20} {r['c']}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "search" and len(sys.argv) > 2:
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "find-email" and len(sys.argv) > 3:
        cmd_find_email(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "domain" and len(sys.argv) > 2:
        cmd_domain(sys.argv[2])
    elif cmd == "enrich" and len(sys.argv) > 2:
        cmd_enrich(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "export":
        cmd_export()
    elif cmd == "stats":
        cmd_stats()
    else:
        print(__doc__)
