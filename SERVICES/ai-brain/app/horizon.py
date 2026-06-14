"""
Horizon Scanner - THINKING Layer Component
============================================
Part of the Conscious Architecture THINKING pillar.

Pipeline: Scan → Model → Anticipate → Feed

Focuses on:
- 3-5 year foresight
- Weak signals detection
- Scenario modeling
- Emerging technology tracking

Feeds into: Thinkers Council, Strategic Intelligence
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class WeakSignal:
    """A weak signal detected from intelligence data."""
    id: str
    title: str
    source: str
    category: str
    relevance_score: float
    signal_strength: str  # "weak", "emerging", "confirmed"
    first_seen: datetime
    mentions: int = 1
    related_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "signal_strength": self.signal_strength,
            "first_seen": self.first_seen.isoformat(),
            "mentions": self.mentions,
            "related_keywords": self.related_keywords
        }


@dataclass
class ScenarioModel:
    """A future scenario based on current signals."""
    id: str
    name: str
    description: str
    timeframe: str  # "1-2 years", "3-5 years"
    probability: float  # 0-1
    impact: str  # "low", "medium", "high", "transformative"
    key_indicators: List[str]
    supporting_signals: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "timeframe": self.timeframe,
            "probability": self.probability,
            "impact": self.impact,
            "key_indicators": self.key_indicators,
            "supporting_signals": self.supporting_signals
        }


class HorizonScanner:
    """
    Horizon Scanner for the THINKING layer.
    
    Scans intelligence for long-term trends, weak signals,
    and builds scenario models for strategic planning.
    """
    
    # Technologies to track for horizon scanning
    EMERGING_TECH_KEYWORDS = {
        "quantum": ["quantum computing", "quantum", "qubit", "quantum supremacy"],
        "agi": ["agi", "artificial general intelligence", "superintelligence", "general ai"],
        "consciousness": ["consciousness", "sentient", "awareness", "phenomenal"],
        "autonomous": ["autonomous", "self-driving", "automate", "agentic"],
        "sovereign": ["sovereign", "decentralized", "local-first", "self-hosted"],
        "neural": ["neural", "brain-computer", "neuralink", "bci"],
        "robotics": ["robot", "humanoid", "embodied ai", "physical ai"],
        "fusion": ["fusion energy", "fusion reactor", "nuclear fusion"],
        "longevity": ["longevity", "lifespan", "aging", "immortality"],
        "multimodal": ["multimodal", "vision language", "video generation"]
    }
    
    # Research labs to monitor
    RESEARCH_LABS = [
        "deepmind", "openai", "anthropic", "meta ai", "google research",
        "microsoft research", "tesla ai", "nvidia", "apple ml"
    ]
    
    def __init__(self):
        self.weak_signals: Dict[str, WeakSignal] = {}
        self.scenarios: Dict[str, ScenarioModel] = {}
        self.last_scan: Optional[datetime] = None
        
        # Initialize default scenarios
        self._init_default_scenarios()
    
    def _init_default_scenarios(self):
        """Initialize baseline future scenarios."""
        default_scenarios = [
            ScenarioModel(
                id="scenario_agi_emergence",
                name="AGI Emergence",
                description="Development of artificial general intelligence capable of human-level reasoning across domains.",
                timeframe="3-5 years",
                probability=0.25,
                impact="transformative",
                key_indicators=["breakthrough in reasoning", "novel capability emergence", "lab announcements"],
                supporting_signals=[]
            ),
            ScenarioModel(
                id="scenario_sovereign_ai",
                name="Sovereign AI Movement",
                description="Mass adoption of self-hosted, local AI models reducing dependency on cloud providers.",
                timeframe="1-2 years",
                probability=0.65,
                impact="high",
                key_indicators=["local model improvements", "cost reduction", "privacy concerns"],
                supporting_signals=[]
            ),
            ScenarioModel(
                id="scenario_ai_regulation",
                name="AI Regulatory Framework",
                description="Comprehensive AI regulation implemented across major economies.",
                timeframe="1-2 years",
                probability=0.75,
                impact="medium",
                key_indicators=["eu ai act", "legislative proposals", "compliance requirements"],
                supporting_signals=[]
            ),
            ScenarioModel(
                id="scenario_agentic_systems",
                name="Agentic AI Proliferation",
                description="Widespread deployment of autonomous AI agents managing business processes.",
                timeframe="1-2 years",
                probability=0.70,
                impact="high",
                key_indicators=["agent frameworks", "automation tools", "workflow ai"],
                supporting_signals=[]
            )
        ]
        
        for scenario in default_scenarios:
            self.scenarios[scenario.id] = scenario
    
    async def scan(self, intelligence_items: List[Dict]) -> Dict[str, Any]:
        """
        Perform a horizon scan on intelligence items.
        
        Args:
            intelligence_items: List of intelligence items to analyze
            
        Returns:
            Horizon scan results with signals, technologies, and scenarios
        """
        self.last_scan = datetime.now(timezone.utc)
        
        # 1. Detect emerging technologies
        emerging_tech = self._detect_emerging_tech(intelligence_items)
        
        # 2. Find weak signals
        weak_signals = self._detect_weak_signals(intelligence_items)
        
        # 3. Update scenarios based on new signals
        updated_scenarios = self._update_scenarios(intelligence_items)
        
        # 4. Find research lab mentions
        research_signals = self._find_research_signals(intelligence_items)
        
        # 5. Build horizon report
        return {
            "scan_timestamp": self.last_scan.isoformat(),
            "items_analyzed": len(intelligence_items),
            "emerging_technologies": emerging_tech,
            "weak_signals": [s.to_dict() for s in weak_signals],
            "scenarios": [s.to_dict() for s in updated_scenarios],
            "research_signals": research_signals,
            "horizon_timeframe": "3-5 years"
        }
    
    def _detect_emerging_tech(self, items: List[Dict]) -> List[Dict]:
        """Detect mentions of emerging technologies."""
        tech_counts = {tech: 0 for tech in self.EMERGING_TECH_KEYWORDS}
        tech_items = {tech: [] for tech in self.EMERGING_TECH_KEYWORDS}
        
        for item in items:
            title = item.get("title", "").lower()
            summary = item.get("summary", "").lower()
            text = f"{title} {summary}"
            
            for tech, keywords in self.EMERGING_TECH_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text:
                        tech_counts[tech] += 1
                        tech_items[tech].append(item.get("title", ""))
                        break
        
        # Return technologies with at least one mention
        result = []
        for tech, count in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                result.append({
                    "technology": tech,
                    "mentions": count,
                    "trend": "rising" if count >= 3 else "emerging" if count >= 2 else "spotted",
                    "sample_signals": tech_items[tech][:3]
                })
        
        return result
    
    def _detect_weak_signals(self, items: List[Dict]) -> List[WeakSignal]:
        """Detect weak signals that might become significant."""
        signals = []
        
        for item in items:
            relevance = item.get("relevance_score", 0)
            
            # Weak signals are items with moderate relevance (0.3-0.6)
            # that mention novel concepts
            if 0.3 <= relevance <= 0.6:
                title = item.get("title", "")
                
                # Check for novel concept indicators
                novel_indicators = ["new", "breakthrough", "discover", "first", "novel", "emerging"]
                if any(ind in title.lower() for ind in novel_indicators):
                    signal = WeakSignal(
                        id=f"weak_{item.get('id', 'unknown')}",
                        title=title,
                        source=item.get("source", "unknown"),
                        category=item.get("category", "general"),
                        relevance_score=relevance,
                        signal_strength="weak",
                        first_seen=datetime.now(timezone.utc),
                        related_keywords=self._extract_keywords(title)
                    )
                    signals.append(signal)
        
        return signals[:10]  # Return top 10 weak signals
    
    def _update_scenarios(self, items: List[Dict]) -> List[ScenarioModel]:
        """Update scenario probabilities based on new intelligence."""
        for scenario in self.scenarios.values():
            supporting = []
            
            for item in items:
                title = item.get("title", "").lower()
                summary = item.get("summary", "").lower()
                text = f"{title} {summary}"
                
                # Check if item supports this scenario
                for indicator in scenario.key_indicators:
                    if indicator.lower() in text:
                        supporting.append(item.get("title", ""))
                        break
            
            # Update supporting signals
            scenario.supporting_signals = list(set(scenario.supporting_signals + supporting))[-10:]
            
            # Adjust probability slightly based on new evidence
            if supporting:
                # Increase probability slightly (max 0.9)
                scenario.probability = min(0.9, scenario.probability + 0.01 * len(supporting))
        
        return list(self.scenarios.values())
    
    def _find_research_signals(self, items: List[Dict]) -> List[Dict]:
        """Find signals from major research labs."""
        signals = []
        
        for item in items:
            title = item.get("title", "").lower()
            source = item.get("source", "").lower()
            
            for lab in self.RESEARCH_LABS:
                if lab in title or lab in source:
                    signals.append({
                        "lab": lab,
                        "signal": item.get("title"),
                        "source": item.get("source"),
                        "relevance": item.get("relevance_score", 0)
                    })
                    break
        
        return signals[:10]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract significant keywords from text."""
        stopwords = {"the", "a", "an", "is", "are", "to", "of", "in", "for", "on", "with", "and", "or"}
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        return [w for w in words if w not in stopwords][:5]
    
    def get_scenario(self, scenario_id: str) -> Optional[ScenarioModel]:
        """Get a specific scenario by ID."""
        return self.scenarios.get(scenario_id)
    
    def add_custom_scenario(self, scenario: ScenarioModel):
        """Add a custom scenario to track."""
        self.scenarios[scenario.id] = scenario


# Singleton instance
_horizon_scanner: Optional[HorizonScanner] = None


def get_horizon_scanner() -> HorizonScanner:
    """Get or create the singleton horizon scanner."""
    global _horizon_scanner
    if _horizon_scanner is None:
        _horizon_scanner = HorizonScanner()
    return _horizon_scanner
















