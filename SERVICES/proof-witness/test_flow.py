#!/usr/bin/env python3
"""
Test the proof witness flow end-to-end
"""
import asyncio
from datetime import datetime
from app.storage import storage
from app.models import ProofCandidate, ProofSource, ProofType, ProofStatus

async def test_flow():
    print("🧪 Testing Proof Witness Flow\n")

    # 1. Create a test proof candidate
    print("1️⃣ Creating test proof candidate...")
    candidate = ProofCandidate(
        id="test-001",
        source=ProofSource.GITHUB,
        type=ProofType.CODE,
        status=ProofStatus.PENDING,
        owner="atlas",
        title="Fixed greenhouse lighting circuit",
        description="Wired 220V outlets, passed inspection",
        url="https://github.com/jamessunheart/greenhouse/commit/abc123",
        media=None,
        data={"repo": "greenhouse", "commit": "abc123"},
        tags=["greenhouse_electrical"],
        suggested_question="greenhouse_electrical",
        confidence=0.9,
        occurred_at=datetime.utcnow(),
        captured_at=datetime.utcnow(),
        confirmed_at=None,
        content_draft="🏡 Greenhouse progress: Fixed lighting circuit\n\nBuilding paradise one wire at a time."
    )

    candidate_id = storage.add_candidate(candidate)
    print(f"   ✅ Created candidate: {candidate_id}\n")

    # 2. Retrieve pending candidates
    print("2️⃣ Retrieving pending candidates...")
    pending = storage.get_pending_candidates(limit=10)
    print(f"   ✅ Found {len(pending)} pending candidates\n")

    if pending:
        print("   📋 Pending proof:")
        for p in pending:
            print(f"      • {p.owner}: {p.title} ({p.confidence*100:.0f}% confidence)")

    # 3. Confirm the candidate
    print("\n3️⃣ Confirming proof candidate...")
    confirmed = storage.confirm_candidate(
        candidate_id=candidate_id,
        tags=["greenhouse_electrical"],
        question_id="greenhouse_electrical",
        impact="220V circuits installed, electrical work 60% complete"
    )
    print(f"   ✅ Proof confirmed: {confirmed.id}\n")
    print(f"      Owner: {confirmed.owner}")
    print(f"      Title: {confirmed.title}")
    print(f"      Impact: {confirmed.impact}")
    print(f"      Tags: {', '.join(confirmed.tags)}")

    # 4. Get daily summary
    print("\n4️⃣ Generating daily summary...")
    summary = storage.get_daily_summary()
    print(f"   ✅ Daily summary:")
    print(f"      Total candidates: {summary.total_candidates}")
    print(f"      Total confirmed: {summary.total_confirmed}")
    print(f"      Highlights: {len(summary.highlights)}")

    if summary.highlights:
        print("\n   📊 Confirmed proof:")
        for proof in summary.highlights:
            print(f"      • {proof.owner}: {proof.title}")
            if proof.impact:
                print(f"        → {proof.impact}")

    print("\n✅ All tests passed!\n")

if __name__ == "__main__":
    asyncio.run(test_flow())
