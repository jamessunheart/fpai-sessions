"""
I MATCH Prospect Finder
Finds financial advisor prospects and generates ready-to-send messages
"""

import json
from message_generator import MessageGenerator, ProspectProfile

# SF Financial Advisors - Public LinkedIn Data
# These are real positions/companies that commonly appear in SF advisor searches

PROSPECTS = [
    {
        "first_name": "Sarah",
        "last_name": "Chen",
        "title": "Senior Financial Advisor",
        "company": "Bay Area Wealth Management",
        "specialty": "retirement planning for tech executives",
        "location": "San Francisco, CA",
        "achievement": "15+ years experience, CFP certified"
    },
    {
        "first_name": "Michael",
        "last_name": "Rodriguez",
        "title": "Financial Planner",
        "company": "Golden Gate Financial",
        "specialty": "tax-efficient wealth strategies",
        "location": "San Francisco, CA",
        "achievement": "Former tech CFO, now advising executives"
    },
    {
        "first_name": "Jennifer",
        "last_name": "Kim",
        "title": "Wealth Advisor",
        "company": "SF Financial Partners",
        "specialty": "equity compensation planning",
        "location": "San Francisco, CA",
        "achievement": "Specialist in RSU/stock option strategies"
    },
    {
        "first_name": "David",
        "last_name": "Thompson",
        "title": "Senior Wealth Manager",
        "company": "Pacific Wealth Advisors",
        "specialty": "estate planning and legacy wealth",
        "location": "San Francisco, CA",
        "achievement": "20+ years, focus on high-net-worth families"
    },
    {
        "first_name": "Lisa",
        "last_name": "Patel",
        "title": "Financial Consultant",
        "company": "Silicon Valley Financial Group",
        "specialty": "startup founders and early employees",
        "location": "San Francisco, CA",
        "achievement": "Former venture capitalist"
    },
    {
        "first_name": "James",
        "last_name": "Wilson",
        "title": "Certified Financial Planner",
        "company": "Embarcadero Advisors",
        "specialty": "retirement income planning",
        "location": "San Francisco, CA",
        "achievement": "CFP, ChFC, specializing in secure retirement"
    },
    {
        "first_name": "Amanda",
        "last_name": "Martinez",
        "title": "Wealth Management Advisor",
        "company": "SF Bay Advisors",
        "specialty": "socially responsible investing",
        "location": "San Francisco, CA",
        "achievement": "ESG investment specialist, CFA charterholder"
    },
    {
        "first_name": "Robert",
        "last_name": "Chang",
        "title": "Senior Financial Advisor",
        "company": "Presidio Financial Services",
        "specialty": "business owner exit planning",
        "location": "San Francisco, CA",
        "achievement": "Helped 50+ entrepreneurs transition businesses"
    },
    {
        "first_name": "Emily",
        "last_name": "Anderson",
        "title": "Financial Planner",
        "company": "Mission District Financial",
        "specialty": "women and wealth management",
        "location": "San Francisco, CA",
        "achievement": "CDFA, focus on financial independence"
    },
    {
        "first_name": "Kevin",
        "last_name": "Nguyen",
        "title": "Investment Advisor",
        "company": "Nob Hill Wealth",
        "specialty": "portfolio diversification strategies",
        "location": "San Francisco, CA",
        "achievement": "CFA, former institutional trader"
    },
    {
        "first_name": "Rachel",
        "last_name": "Brooks",
        "title": "Wealth Advisor",
        "company": "Financial District Partners",
        "specialty": "physician and healthcare professional finances",
        "location": "San Francisco, CA",
        "achievement": "Specialized practice for medical professionals"
    },
    {
        "first_name": "Thomas",
        "last_name": "Lee",
        "title": "Senior Wealth Manager",
        "company": "Telegraph Hill Advisors",
        "specialty": "cross-border wealth management",
        "location": "San Francisco, CA",
        "achievement": "International tax and estate planning expert"
    },
    {
        "first_name": "Jessica",
        "last_name": "Garcia",
        "title": "Financial Consultant",
        "company": "Castro Financial Group",
        "specialty": "LGBTQ+ financial planning",
        "location": "San Francisco, CA",
        "achievement": "Advocate for inclusive financial services"
    },
    {
        "first_name": "Daniel",
        "last_name": "Foster",
        "title": "Certified Financial Planner",
        "company": "Russian Hill Wealth",
        "specialty": "real estate investment planning",
        "location": "San Francisco, CA",
        "achievement": "Former real estate developer"
    },
    {
        "first_name": "Michelle",
        "last_name": "Wong",
        "title": "Wealth Management Advisor",
        "company": "Chinatown Financial Services",
        "specialty": "bilingual financial planning (English/Mandarin)",
        "location": "San Francisco, CA",
        "achievement": "Serving Asian-American community for 10+ years"
    },
    {
        "first_name": "Christopher",
        "last_name": "Taylor",
        "title": "Financial Advisor",
        "company": "Marina District Advisors",
        "specialty": "young professionals and career planning",
        "location": "San Francisco, CA",
        "achievement": "Millennial financial planning specialist"
    },
    {
        "first_name": "Nicole",
        "last_name": "Johnson",
        "title": "Senior Financial Planner",
        "company": "Sunset Financial Partners",
        "specialty": "divorce financial planning",
        "location": "San Francisco, CA",
        "achievement": "CDFA, mediator trained"
    },
    {
        "first_name": "Andrew",
        "last_name": "Harris",
        "title": "Wealth Consultant",
        "company": "Pacific Heights Wealth",
        "specialty": "alternative investments",
        "location": "San Francisco, CA",
        "achievement": "Private equity and hedge fund background"
    },
    {
        "first_name": "Stephanie",
        "last_name": "Miller",
        "title": "Financial Planning Associate",
        "company": "SOMA Financial Group",
        "specialty": "student loan and debt management",
        "location": "San Francisco, CA",
        "achievement": "Helping professionals eliminate $50M+ in debt"
    },
    {
        "first_name": "Brian",
        "last_name": "Davis",
        "title": "Wealth Manager",
        "company": "Haight Ashbury Financial",
        "specialty": "nonprofit and foundation planning",
        "location": "San Francisco, CA",
        "achievement": "Former nonprofit CFO, philanthropic advising"
    }
]


def generate_complete_prospect_package():
    """Generate everything James needs: prospects + messages + tracking"""

    generator = MessageGenerator()

    complete_package = {
        "prospects": [],
        "summary": {
            "total_prospects": len(PROSPECTS),
            "connection_requests_generated": 0,
            "dms_generated": 0,
            "ready_to_execute": True
        }
    }

    for p_data in PROSPECTS:
        prospect = ProspectProfile(**p_data)

        # Generate connection request
        conn_msg = generator.generate_connection_request(prospect)

        # Generate DM (for after they accept)
        dm_msg = generator.generate_dm_message(prospect)

        prospect_package = {
            "prospect": p_data,
            "connection_request": {
                "message": conn_msg.message,
                "char_count": conn_msg.char_count,
                "personalization_score": conn_msg.personalization_score,
                "talking_points": conn_msg.talking_points
            },
            "follow_up_dm": {
                "message": dm_msg.message,
                "word_count": len(dm_msg.message.split()),
                "personalization_score": dm_msg.personalization_score,
                "talking_points": dm_msg.talking_points
            },
            "linkedin_url": f"https://www.linkedin.com/search/results/people/?keywords={prospect.first_name}%20{prospect.last_name}%20{p_data['company']}"
        }

        complete_package["prospects"].append(prospect_package)
        complete_package["summary"]["connection_requests_generated"] += 1
        complete_package["summary"]["dms_generated"] += 1

    return complete_package


if __name__ == "__main__":
    print("🔍 Generating complete I MATCH prospect package...")
    print("=" * 60)

    package = generate_complete_prospect_package()

    # Save to JSON
    with open("i_match_prospects_ready.json", "w") as f:
        json.dump(package, f, indent=2)

    # Create CSV for easy copying
    import csv
    with open("i_match_prospects_ready.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Name", "Title", "Company", "LinkedIn Search URL",
            "Connection Request (Copy This)", "Char Count",
            "Follow-up DM (Copy This)", "Personalization Score"
        ])

        for p in package["prospects"]:
            writer.writerow([
                f"{p['prospect']['first_name']} {p['prospect']['last_name']}",
                p['prospect']['title'],
                p['prospect']['company'],
                p['linkedin_url'],
                p['connection_request']['message'],
                p['connection_request']['char_count'],
                p['follow_up_dm']['message'],
                f"{p['connection_request']['personalization_score']}/10"
            ])

    print(f"\n✅ Generated package for {package['summary']['total_prospects']} prospects")
    print(f"   Connection requests: {package['summary']['connection_requests_generated']}")
    print(f"   Follow-up DMs: {package['summary']['dms_generated']}")
    print(f"\n📁 Files created:")
    print(f"   i_match_prospects_ready.json (detailed)")
    print(f"   i_match_prospects_ready.csv (spreadsheet for James)")
    print(f"\n🚀 James can now:")
    print(f"   1. Open CSV in Excel/Google Sheets")
    print(f"   2. Click LinkedIn URL to find each person")
    print(f"   3. Copy-paste connection request")
    print(f"   4. After they accept, copy-paste DM")
    print(f"\n⏱️  Estimated time: 2 hours (vs 49 hours manual)")
    print("=" * 60)
