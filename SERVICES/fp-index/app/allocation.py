"""
FP Frontier Allocation Engine — v5.4
======================================

Calculates target capital allocation across AI sectors,
weighted by real-time FP Line dimension scores and momentum.

Layer 1 product: Intelligence only. No money touches the system.
"If we were managing capital, here's how we'd allocate it."

Revenue: Free (monthly summary) | Pro $49/mo (weekly) | Premium $199/mo (daily)
Regulatory: Publishing intelligence. Same as Bloomberg. Standard disclaimer.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("fp_index.allocation")

DIMENSION_SECTORS = {
    "reasoning": {
        "name": "Reasoning & Intelligence",
        "description": "Companies building the thinking layer of AI",
        "base_weight": 0.14,
        "subsectors": [
            "Foundation model companies",
            "Inference API providers",
            "Enterprise AI platforms",
        ],
        "tickers": [
            {"ticker": "MSFT", "exposure": "OpenAI partnership, Copilot, Azure AI"},
            {"ticker": "GOOGL", "exposure": "Gemini, DeepMind, cloud AI"},
            {"ticker": "META", "exposure": "LLaMA open source, AI research"},
            {"ticker": "AMZN", "exposure": "Bedrock, AWS AI services"},
        ],
    },
    "code": {
        "name": "Autonomy & Agents",
        "description": "Companies building the doing layer of AI",
        "base_weight": 0.14,
        "subsectors": [
            "Agent framework companies",
            "Automation platforms",
            "Robotic process automation",
        ],
        "tickers": [
            {"ticker": "PATH", "exposure": "UiPath — enterprise automation"},
            {"ticker": "TSLA", "exposure": "Autonomous driving, Optimus robot"},
            {"ticker": "ISRG", "exposure": "Intuitive Surgical — autonomous surgery"},
        ],
    },
    "vision": {
        "name": "Multimodal AI",
        "description": "Companies building the sensing layer of AI",
        "base_weight": 0.10,
        "subsectors": [
            "Computer vision",
            "Audio/speech AI",
            "Video generation",
        ],
        "tickers": [
            {"ticker": "ADBE", "exposure": "Adobe — Firefly, creative AI"},
            {"ticker": "U", "exposure": "Unity — real-time 3D + AI"},
        ],
    },
    "tools": {
        "name": "AI Accessibility",
        "description": "Companies making AI usable by everyone",
        "base_weight": 0.10,
        "subsectors": [
            "No-code AI platforms",
            "API-first AI companies",
            "AI education and upskilling",
        ],
        "tickers": [
            {"ticker": "SNOW", "exposure": "Snowflake — data + AI platform"},
            {"ticker": "MDB", "exposure": "MongoDB — vector search, AI data"},
            {"ticker": "PLTR", "exposure": "Palantir — AI for enterprises"},
        ],
    },
    "general": {
        "name": "AI Infrastructure & Efficiency",
        "description": "Companies powering faster, cheaper AI",
        "base_weight": 0.10,
        "subsectors": [
            "GPU/chip makers",
            "Inference optimization",
            "Cloud compute providers",
        ],
        "tickers": [
            {"ticker": "NVDA", "exposure": "NVIDIA — dominant GPU supplier"},
            {"ticker": "AMD", "exposure": "AMD — AI accelerator chips"},
            {"ticker": "AVGO", "exposure": "Broadcom — custom AI chips"},
            {"ticker": "TSM", "exposure": "TSMC — fabrication for all AI chips"},
        ],
    },
    "security": {
        "name": "AI Safety & Governance",
        "description": "Companies building the trust layer of AI",
        "base_weight": 0.10,
        "subsectors": [
            "AI safety tools",
            "Cybersecurity AI",
            "Compliance and governance",
        ],
        "tickers": [
            {"ticker": "CRWD", "exposure": "CrowdStrike — AI-powered security"},
            {"ticker": "PANW", "exposure": "Palo Alto — AI threat detection"},
            {"ticker": "ZS", "exposure": "Zscaler — zero trust AI security"},
        ],
    },
    "agents": {
        "name": "Workforce Transformation",
        "description": "Companies capturing the displacement wave",
        "base_weight": 0.08,
        "subsectors": [
            "AI customer service",
            "AI legal tech",
            "AI accounting/finance",
            "Upskilling platforms",
        ],
        "tickers": [
            {"ticker": "NOW", "exposure": "ServiceNow — enterprise workflow AI"},
            {"ticker": "WDAY", "exposure": "Workday — HR + AI workforce management"},
            {"ticker": "HUBS", "exposure": "HubSpot — AI sales/marketing automation"},
        ],
    },
    "audio": {
        "name": "Audio & Speech AI",
        "description": "Companies building voice, music, and audio intelligence",
        "base_weight": 0.04,
        "subsectors": [
            "Speech recognition / TTS",
            "Music generation",
            "Audio analytics",
        ],
        "tickers": [
            {"ticker": "SPOT", "exposure": "Spotify — AI-driven audio personalization"},
            {"ticker": "AAPL", "exposure": "Apple — Siri, on-device speech AI"},
        ],
    },
    "science": {
        "name": "Scientific AI",
        "description": "AI accelerating research and discovery",
        "base_weight": 0.04,
        "subsectors": [
            "Drug discovery AI",
            "Materials science",
            "Climate modeling",
        ],
        "tickers": [
            {"ticker": "RXRX", "exposure": "Recursion Pharma — AI drug discovery"},
            {"ticker": "TMO", "exposure": "Thermo Fisher — lab automation + AI"},
        ],
    },
    "creative": {
        "name": "Creative & Generative AI",
        "description": "Companies building AI for content creation and design",
        "base_weight": 0.04,
        "subsectors": [
            "Image generation",
            "Video generation",
            "Design tools",
        ],
        "tickers": [
            {"ticker": "ADBE", "exposure": "Adobe — Firefly generative AI"},
            {"ticker": "CANV", "exposure": "Canva — AI design platform (private)"},
        ],
    },
    "finance": {
        "name": "AI in Finance",
        "description": "AI transforming financial services and trading",
        "base_weight": 0.04,
        "subsectors": [
            "Algorithmic trading",
            "Fraud detection",
            "Automated underwriting",
        ],
        "tickers": [
            {"ticker": "GS", "exposure": "Goldman Sachs — AI trading + analytics"},
            {"ticker": "V", "exposure": "Visa — AI fraud detection at scale"},
        ],
    },
    "health": {
        "name": "AI in Healthcare",
        "description": "AI improving diagnostics, treatment, and health outcomes",
        "base_weight": 0.04,
        "subsectors": [
            "Diagnostic imaging AI",
            "Clinical decision support",
            "Remote patient monitoring",
        ],
        "tickers": [
            {"ticker": "ISRG", "exposure": "Intuitive Surgical — robotic surgery AI"},
            {"ticker": "VEEV", "exposure": "Veeva — AI for life sciences"},
        ],
    },
    "education": {
        "name": "AI in Education",
        "description": "AI personalizing and scaling learning",
        "base_weight": 0.04,
        "subsectors": [
            "Adaptive learning platforms",
            "AI tutoring",
            "Assessment automation",
        ],
        "tickers": [
            {"ticker": "DUOL", "exposure": "Duolingo — AI-powered language learning"},
            {"ticker": "COUR", "exposure": "Coursera — AI course recommendations"},
        ],
    },
}


def calculate_allocation(fp_line_data: dict) -> dict:
    """Calculate target allocation across AI sectors using FP Line dimension scores.
    
    Base allocation = dimension weight × score (from FP Line)
    Momentum adjustment = ±20% based on score trend
    Result normalized to 100%.
    """
    domain_scores = fp_line_data.get("domain_scores", {})
    overall_score = fp_line_data.get("overall_score", 50.0)
    momentum = fp_line_data.get("momentum", 0.0)

    raw_scores = {}
    for domain_key, config in DIMENSION_SECTORS.items():
        score = domain_scores.get(domain_key, 50.0)
        weight = config["base_weight"]

        base = weight * score

        mom_adj = 0.0
        if momentum > 2:
            mom_adj = 0.15
        elif momentum > 0.5:
            mom_adj = 0.08
        elif momentum < -2:
            mom_adj = -0.15
        elif momentum < -0.5:
            mom_adj = -0.08

        raw_scores[domain_key] = max(0.01, base * (1 + mom_adj))

    total = sum(raw_scores.values())
    allocations = {}
    for domain_key in raw_scores:
        config = DIMENSION_SECTORS[domain_key]
        pct = round(raw_scores[domain_key] / total * 100, 1)
        score = domain_scores.get(domain_key, 50.0)

        if pct > config["base_weight"] * 100 + 3:
            signal = "overweight"
        elif pct < config["base_weight"] * 100 - 3:
            signal = "underweight"
        else:
            signal = "neutral"

        allocations[domain_key] = {
            "sector_name": config["name"],
            "description": config["description"],
            "target_pct": pct,
            "base_weight_pct": round(config["base_weight"] * 100, 1),
            "dimension_score": score,
            "momentum_signal": signal,
            "subsectors": config["subsectors"],
            "example_tickers": config["tickers"],
        }

    sorted_alloc = dict(sorted(allocations.items(), key=lambda x: x[1]["target_pct"], reverse=True))

    return {
        "fp_line_score": overall_score,
        "fp_line_momentum": momentum,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pct": round(sum(a["target_pct"] for a in sorted_alloc.values()), 1),
        "allocations": sorted_alloc,
    }


def generate_allocation_headline(alloc_data: dict) -> str:
    """One-line headline for the allocation."""
    score = alloc_data["fp_line_score"]
    mom = alloc_data["fp_line_momentum"]
    direction = "advancing" if mom > 0.5 else "consolidating" if mom > -0.5 else "pulling back"

    top_sector = next(iter(alloc_data["allocations"].values()))

    return (
        f"FP Line at {score}, {direction}. "
        f"{top_sector['sector_name']} leads allocation at {top_sector['target_pct']}%. "
        f"Capital should follow the capability signal."
    )


def generate_rebalance_actions(alloc_data: dict) -> list[dict]:
    """Identify sectors that moved significantly from base weight."""
    actions = []
    for key, alloc in alloc_data["allocations"].items():
        diff = alloc["target_pct"] - alloc["base_weight_pct"]
        if abs(diff) >= 2:
            direction = "▲ Increase" if diff > 0 else "▼ Decrease"
            actions.append({
                "sector": alloc["sector_name"],
                "direction": direction,
                "from_pct": alloc["base_weight_pct"],
                "to_pct": alloc["target_pct"],
                "change": round(diff, 1),
                "reason": f"Dimension score at {alloc['dimension_score']:.0f}, signal: {alloc['momentum_signal']}",
            })
    return sorted(actions, key=lambda a: abs(a["change"]), reverse=True)


INVESTMENT_DISCLAIMER = (
    "The FP Frontier Basket is an intelligence product, not a managed fund. "
    "Allocation suggestions are based on the Full Potential Index scoring system "
    "and do not constitute financial advice. Past hypothetical performance does not "
    "predict future results. All investment involves risk of loss. Consult a "
    "qualified financial advisor before making investment decisions."
)
