"""
Proof Witness - Auto-Tagging Logic

AI witnesses the work and suggests tags with confidence scores.
Human confirms in 15 seconds.
"""
from typing import List, Tuple, Optional
import re

from app.config import settings


class AutoTagger:
    """
    Auto-tag proof based on keywords and context

    This is intentionally simple - keyword matching with confidence scores.
    Could be upgraded to use AI (Claude/GPT) later, but keywords work for MVP.
    """

    def __init__(self):
        self.tag_patterns = {
            "greenhouse": {
                "keywords": settings.GREENHOUSE_KEYWORDS,
                "weight": 1.0
            },
            "revenue": {
                "keywords": settings.REVENUE_KEYWORDS,
                "weight": 1.0
            },
            "content": {
                "keywords": settings.CONTENT_KEYWORDS,
                "weight": 1.0
            }
        }

    def suggest_tags(self, text: str, url: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Suggest tags based on text (title + description)

        Returns: List of (tag, confidence) tuples
        """
        text_lower = text.lower()
        url_lower = (url or "").lower()

        suggestions = []

        for tag_name, pattern in self.tag_patterns.items():
            confidence = self._calculate_confidence(
                text_lower,
                url_lower,
                pattern["keywords"],
                pattern["weight"]
            )

            if confidence >= settings.TAG_CONFIDENCE_THRESHOLD:
                suggestions.append((tag_name, confidence))

        # Sort by confidence descending
        return sorted(suggestions, key=lambda x: x[1], reverse=True)

    def _calculate_confidence(self, text: str, url: str, keywords: List[str], weight: float) -> float:
        """
        Calculate confidence score for a tag

        Simple algorithm:
        - Each keyword match = +0.2 confidence
        - URL match = +0.3 confidence
        - Cap at 1.0
        """
        confidence = 0.0

        for keyword in keywords:
            # Check text
            if keyword in text:
                confidence += 0.2

            # Check URL (worth more)
            if keyword in url:
                confidence += 0.3

        # Apply weight and cap at 1.0
        return min(confidence * weight, 1.0)

    def suggest_question(self, tags: List[str], title: str) -> Optional[str]:
        """
        Suggest which question this proof might solve

        For MVP, use simple heuristics. Can upgrade to AI later.
        """
        # Greenhouse questions
        if "greenhouse" in tags:
            if any(word in title.lower() for word in ["electrical", "wire", "outlet", "circuit"]):
                return "greenhouse_electrical"
            elif any(word in title.lower() for word in ["plumbing", "pipe", "water", "drain"]):
                return "greenhouse_plumbing"
            elif any(word in title.lower() for word in ["drywall", "wall", "ceiling", "finish"]):
                return "greenhouse_drywall"
            else:
                return "greenhouse_general"

        # Revenue questions
        if "revenue" in tags:
            if any(word in title.lower() for word in ["dashboard", "visibility", "tracking"]):
                return "revenue_visibility"
            elif any(word in title.lower() for word in ["growth", "increase", "new customer"]):
                return "revenue_growth"
            else:
                return "revenue_general"

        # Content questions
        if "content" in tags:
            if any(word in title.lower() for word in ["proof", "transformation", "before after"]):
                return "content_proof"
            elif any(word in title.lower() for word in ["viral", "views", "engagement"]):
                return "content_growth"
            else:
                return "content_general"

        return None

    def generate_content_draft(self, title: str, tags: List[str], url: Optional[str] = None) -> str:
        """
        Generate a content draft (tweet/post) from proof

        This is the "proof → content" automation.
        Human can edit before posting, but it gives them a starting point.
        """
        # Template based on tags
        if "greenhouse" in tags:
            return f"🏡 Greenhouse progress: {title}\n\nBuilding paradise one wire at a time.\n\n#BuildInPublic #Greenhouse"

        elif "revenue" in tags:
            return f"💰 Revenue update: {title}\n\nShowing the real numbers.\n\n#Transparency #Revenue"

        elif "content" in tags:
            return f"📱 New content: {title}\n\nSharing the journey.\n\n#Content #Story"

        else:
            # Generic template
            return f"✨ Update: {title}\n\n{url if url else ''}\n\n#Progress #Building"


# Global instance
tagger = AutoTagger()
