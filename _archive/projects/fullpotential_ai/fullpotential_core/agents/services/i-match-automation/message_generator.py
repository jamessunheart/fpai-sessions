"""
LinkedIn Message Generator for I MATCH Launch
Powered by Claude AI - Generates personalized outreach messages
"""

import os
from anthropic import Anthropic
from typing import Optional, List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class ProspectProfile(BaseModel):
    """Prospect information for personalization"""
    first_name: str
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    specialty: Optional[str] = None
    location: Optional[str] = None
    achievement: Optional[str] = None
    linkedin_url: Optional[str] = None


class GeneratedMessage(BaseModel):
    """Generated message with metadata"""
    message: str
    message_type: str  # "connection_request" or "dm"
    char_count: int
    talking_points: List[str]
    personalization_score: int  # 1-10


class MessageGenerator:
    """AI-powered LinkedIn message generator"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=self.api_key)

    def generate_connection_request(self, prospect: ProspectProfile) -> GeneratedMessage:
        """Generate personalized LinkedIn connection request (300 char limit)"""

        prompt = f"""Generate a LinkedIn connection request message for this financial advisor prospect:

Name: {prospect.first_name} {prospect.last_name or ''}
Title: {prospect.title or 'Financial Advisor'}
Company: {prospect.company or 'Not specified'}
Specialty: {prospect.specialty or 'Financial planning'}
Location: {prospect.location or 'San Francisco'}

Requirements:
- MAXIMUM 280 characters (LinkedIn limit is 300, leave buffer)
- Mention I MATCH AI lead matching
- Professional but casual tone
- Include value proposition hint
- NO pushy sales language
- Personalize if possible based on their specialty

Example good messages:
"Hi {prospect.first_name} - Noticed your work in {prospect.specialty}. Building AI matching for financial advisors. Interested in quality lead gen?"

"Hi {prospect.first_name} - AI lead matching for {prospect.specialty} advisors. Better client fit = higher close rates. Open to chat?"

Generate ONE connection request message. Output ONLY the message text, no quotes, no explanation."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        message = response.content[0].text.strip()

        # Ensure within character limit
        if len(message) > 280:
            message = message[:277] + "..."

        talking_points = [
            f"Mentioned: {prospect.specialty or 'financial services'}",
            "Value prop: AI matching",
            "Soft approach, no hard sell"
        ]

        return GeneratedMessage(
            message=message,
            message_type="connection_request",
            char_count=len(message),
            talking_points=talking_points,
            personalization_score=self._calculate_personalization_score(prospect)
        )

    def generate_dm_message(self, prospect: ProspectProfile) -> GeneratedMessage:
        """Generate follow-up DM after connection accepted"""

        prompt = f"""Generate a LinkedIn DM (direct message) for this financial advisor who just accepted your connection:

Name: {prospect.first_name} {prospect.last_name or ''}
Title: {prospect.title or 'Financial Advisor'}
Company: {prospect.company or 'Not specified'}
Specialty: {prospect.specialty or 'Financial planning'}
Achievement: {prospect.achievement or 'Not specified'}

Context: They accepted your connection request about AI lead matching for advisors.

Requirements:
- 150-250 words (conversational length)
- Start with genuine compliment about their work
- Explain I MATCH value proposition clearly
- Include specific benefits (20% success fee, AI matching quality)
- Mention launching with 10 SF advisors this week (creates urgency/exclusivity)
- End with clear call to action
- Link: http://198.54.123.234:8401/providers.html
- Professional but warm tone
- Use their first name

Structure:
1. Personalized opener (their achievement/specialty)
2. Value proposition (AI matching, better fit, 20% success fee)
3. Social proof (launching with 10 SF advisors)
4. Clear CTA
5. Sign off as James

Generate ONE DM message. Output ONLY the message text, no quotes or explanation."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        message = response.content[0].text.strip()

        talking_points = [
            f"Personalized: {prospect.achievement or prospect.specialty}",
            "Clear value prop: 20% success fee, AI matching",
            "Urgency: launching with 10 SF advisors",
            "CTA: provider signup link"
        ]

        return GeneratedMessage(
            message=message,
            message_type="dm",
            char_count=len(message),
            talking_points=talking_points,
            personalization_score=self._calculate_personalization_score(prospect)
        )

    def _calculate_personalization_score(self, prospect: ProspectProfile) -> int:
        """Calculate how personalized the message can be (1-10)"""
        score = 5  # baseline

        if prospect.specialty:
            score += 2
        if prospect.achievement:
            score += 2
        if prospect.company:
            score += 1

        return min(score, 10)

    def generate_batch_messages(
        self,
        prospects: List[ProspectProfile],
        message_type: str = "connection_request"
    ) -> List[Dict]:
        """Generate messages for multiple prospects"""

        results = []
        for i, prospect in enumerate(prospects, 1):
            try:
                if message_type == "connection_request":
                    generated = self.generate_connection_request(prospect)
                else:
                    generated = self.generate_dm_message(prospect)

                results.append({
                    "prospect_name": f"{prospect.first_name} {prospect.last_name or ''}",
                    "message": generated.message,
                    "char_count": generated.char_count,
                    "personalization_score": generated.personalization_score,
                    "talking_points": generated.talking_points
                })

                print(f"✓ Generated message {i}/{len(prospects)}: {prospect.first_name}")

            except Exception as e:
                print(f"✗ Failed for {prospect.first_name}: {e}")
                results.append({
                    "prospect_name": f"{prospect.first_name} {prospect.last_name or ''}",
                    "error": str(e)
                })

        return results


# CLI Interface
if __name__ == "__main__":
    import json
    import sys

    print("🤖 I MATCH LinkedIn Message Generator")
    print("=" * 50)

    # Example usage
    generator = MessageGenerator()

    # Sample prospects
    sample_prospects = [
        ProspectProfile(
            first_name="Sarah",
            last_name="Chen",
            title="Senior Financial Advisor",
            company="Bay Area Wealth Management",
            specialty="retirement planning for tech executives",
            location="San Francisco",
            achievement="20+ years helping tech leaders retire early"
        ),
        ProspectProfile(
            first_name="Michael",
            last_name="Rodriguez",
            title="CFP, Wealth Manager",
            company="Golden Gate Financial",
            specialty="tax-efficient wealth strategies",
            location="San Francisco"
        ),
        ProspectProfile(
            first_name="Jennifer",
            title="Financial Planner",
            specialty="family wealth management"
        )
    ]

    print("\n📝 Generating Connection Requests...")
    print("-" * 50)
    connection_messages = generator.generate_batch_messages(
        sample_prospects,
        message_type="connection_request"
    )

    for msg in connection_messages:
        print(f"\n👤 {msg['prospect_name']}")
        print(f"📊 Personalization: {msg.get('personalization_score', 'N/A')}/10")
        print(f"📏 Length: {msg.get('char_count', 0)} chars")
        print(f"💬 Message:")
        print(f"   {msg.get('message', msg.get('error'))}")

    print("\n\n📧 Generating DM Messages...")
    print("-" * 50)
    dm_messages = generator.generate_batch_messages(
        sample_prospects[:2],  # Just first 2 for demo
        message_type="dm"
    )

    for msg in dm_messages:
        print(f"\n👤 {msg['prospect_name']}")
        print(f"📊 Personalization: {msg.get('personalization_score', 'N/A')}/10")
        print(f"💬 Message:")
        print(f"   {msg.get('message', msg.get('error'))}")
        print(f"\n🎯 Talking Points: {', '.join(msg.get('talking_points', []))}")

    print("\n" + "=" * 50)
    print("✅ Message generation complete!")
    print("\nTo use with your own prospects:")
    print("1. Create CSV with: first_name,last_name,title,company,specialty,achievement")
    print("2. Import and use: generator.generate_batch_messages(your_prospects)")
