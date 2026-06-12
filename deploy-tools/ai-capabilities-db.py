#!/usr/bin/env python3
"""Global AI Capability Database — the map of everything available.

Tables:
  capabilities_global  — Every meaningful AI capability in the world
  gap_analysis         — Auto-generated gaps between our stack and what exists

Usage:
  ai-capabilities-db.py seed          — Populate baseline (run once)
  ai-capabilities-db.py list [cat]    — List all or by category
  ai-capabilities-db.py gaps          — Run gap analysis
  ai-capabilities-db.py search <q>    — Search capabilities
  ai-capabilities-db.py stats         — Database statistics
  ai-capabilities-db.py export        — Export as JSON
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = "/opt/fpai/memory-bus/bus.db"
BUS_URL = "http://127.0.0.1:8195"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS capabilities_global (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            what_it_does TEXT,
            api_available INTEGER DEFAULT 1,
            pricing_model TEXT,
            approximate_cost TEXT,
            free_tier INTEGER DEFAULT 0,
            integration_complexity TEXT,
            our_status TEXT DEFAULT 'not_integrated',
            relevance TEXT DEFAULT 'medium',
            relevance_reason TEXT,
            url TEXT,
            last_verified TEXT,
            notes TEXT,
            UNIQUE(name, category)
        );

        CREATE TABLE IF NOT EXISTS gap_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gap_name TEXT NOT NULL,
            category TEXT,
            current_state TEXT,
            available_options TEXT,
            recommended TEXT,
            integration_effort TEXT,
            impact TEXT,
            priority TEXT DEFAULT 'medium',
            generated_at TEXT,
            UNIQUE(gap_name)
        );

        CREATE INDEX IF NOT EXISTS idx_cap_global_category ON capabilities_global(category);
        CREATE INDEX IF NOT EXISTS idx_cap_global_status ON capabilities_global(our_status);
        CREATE INDEX IF NOT EXISTS idx_cap_global_relevance ON capabilities_global(relevance);
    """)
    db.commit()
    return db


def seed_baseline():
    """Populate the baseline database with 100+ AI capabilities."""
    db = get_db()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entries = [
        # ========== LANGUAGE MODELS ==========
        ("OpenAI GPT-4o", "language_models", "general", "Multimodal LLM — text, vision, audio. Flagship model.", 1, "per token", "$2.50/1M in, $10/1M out", 0, "low", "not_integrated", "high", "Direct competitor/complement to Claude", "https://platform.openai.com"),
        ("OpenAI GPT-4o-mini", "language_models", "general", "Fast, cheap multimodal model for lightweight tasks.", 1, "per token", "$0.15/1M in, $0.60/1M out", 0, "low", "not_integrated", "medium", "Could handle intake agent qualification cheaply", "https://platform.openai.com"),
        ("OpenAI o3", "language_models", "reasoning", "Advanced reasoning model for complex problem solving.", 1, "per token", "$10/1M in, $40/1M out", 0, "low", "not_integrated", "low", "Expensive, Claude handles our reasoning needs", "https://platform.openai.com"),
        ("Anthropic Claude Sonnet", "language_models", "general", "Our primary LLM. Strong reasoning, coding, analysis.", 1, "per token", "$3/1M in, $15/1M out", 0, "low", "integrated", "critical", "Powers CORA, Operator, Ori, and Adam via MetaClaw", "https://anthropic.com"),
        ("Anthropic Claude Haiku", "language_models", "fast", "Ultra-fast, cheap Claude variant for simple tasks.", 1, "per token", "$0.25/1M in, $1.25/1M out", 0, "low", "not_integrated", "high", "Could replace Sonnet for simple Operator tasks, 10x cheaper", "https://anthropic.com"),
        ("Google Gemini 2.0 Flash", "language_models", "fast", "Fast multimodal model with massive context window (1M tokens).", 1, "per token", "$0.075/1M in", 1, "low", "not_integrated", "high", "Free tier, huge context — could process entire knowledge bases", "https://ai.google.dev"),
        ("Google Gemini 2.0 Pro", "language_models", "general", "Google's flagship. Strong on factual tasks and long context.", 1, "per token", "$1.25/1M in, $5/1M out", 0, "low", "not_integrated", "medium", "Alternative to Claude for diversity", "https://ai.google.dev"),
        ("Meta Llama 3.3 70B", "language_models", "open_source", "Best open-source model. Run locally via Ollama.", 1, "free (self-hosted)", "$0 via Ollama", 1, "medium", "integrated", "high", "Already running via Ollama for Pulse reflections", "https://llama.meta.com"),
        ("Mistral Large", "language_models", "general", "Strong European LLM. Good coding and reasoning.", 1, "per token", "$2/1M in, $6/1M out", 0, "low", "not_integrated", "low", "No clear advantage over Claude for our use cases", "https://mistral.ai"),
        ("DeepSeek V3", "language_models", "reasoning", "Chinese LLM with strong math/coding. Very cheap.", 1, "per token", "$0.27/1M in, $1.10/1M out", 0, "low", "not_integrated", "medium", "Extremely cheap alternative for bulk tasks", "https://deepseek.com"),
        ("Cohere Command R+", "language_models", "rag", "Specialized for RAG and enterprise search.", 1, "per token", "$2.50/1M in, $10/1M out", 1, "low", "not_integrated", "low", "Relevant if we build a knowledge base product", "https://cohere.com"),
        ("Groq", "language_models", "inference", "Ultra-fast inference for Llama/Mistral models. 500+ tok/sec.", 1, "per token", "$0.05/1M in (Llama 70B)", 1, "low", "not_integrated", "high", "Could make local-quality LLM calls nearly instant and free-tier", "https://groq.com"),

        # ========== CODE GENERATION ==========
        ("GitHub Copilot", "code_generation", "ide", "AI code completion in IDE. Powered by GPT-4.", 1, "subscription", "$10/mo individual", 0, "low", "not_integrated", "low", "Ori uses Cursor which has its own AI", "https://github.com/features/copilot"),
        ("Cursor", "code_generation", "ide", "AI-native IDE. Powers Ori agent.", 1, "subscription", "$20/mo pro", 0, "low", "integrated", "critical", "Ori's entire operating environment", "https://cursor.com"),
        ("Devin", "code_generation", "autonomous", "Autonomous AI software engineer. Full project execution.", 1, "subscription", "$500/mo", 0, "high", "not_integrated", "medium", "Expensive but could handle complex builds without Ori", "https://devin.ai"),
        ("Replit Agent", "code_generation", "autonomous", "Build and deploy apps from natural language.", 1, "subscription", "$25/mo", 0, "medium", "not_integrated", "low", "We have Cursor+Ori", "https://replit.com"),

        # ========== VOICE / AUDIO ==========
        ("ElevenLabs", "voice_audio", "text_to_speech", "Realistic voice synthesis, voice cloning, real-time streaming.", 1, "per character", "$0.30/1K chars, free tier", 1, "low", "not_integrated", "high", "Enables voice agent, automated calls, podcast generation", "https://elevenlabs.io"),
        ("OpenAI TTS", "voice_audio", "text_to_speech", "Text to speech. 6 voices, good quality.", 1, "per character", "$15/1M chars", 0, "low", "not_integrated", "medium", "Simpler than ElevenLabs but less flexible", "https://platform.openai.com"),
        ("OpenAI Whisper", "voice_audio", "speech_to_text", "Best-in-class speech recognition. Open source.", 1, "per minute", "$0.006/min", 1, "low", "not_integrated", "high", "Needed for voice intake, call transcription", "https://platform.openai.com"),
        ("Deepgram", "voice_audio", "speech_to_text", "Real-time speech recognition. Fastest available.", 1, "per minute", "$0.0043/min, free tier", 1, "low", "not_integrated", "high", "Best for real-time voice agent conversations", "https://deepgram.com"),
        ("AssemblyAI", "voice_audio", "speech_to_text", "Speech-to-text with speaker diarization and summarization.", 1, "per minute", "$0.01/min", 1, "low", "not_integrated", "medium", "Good for meeting transcription", "https://assemblyai.com"),
        ("PlayHT", "voice_audio", "text_to_speech", "Ultra-realistic voice cloning and generation.", 1, "per character", "$0.20/1K chars", 1, "low", "not_integrated", "medium", "Alternative to ElevenLabs", "https://play.ht"),
        ("Resemble.AI", "voice_audio", "voice_cloning", "Clone voices from minutes of audio. Real-time synthesis.", 1, "per character", "Custom pricing", 0, "medium", "not_integrated", "medium", "Could clone Sunheart's voice for automated calls", "https://resemble.ai"),

        # ========== VISION / IMAGE ==========
        ("OpenAI DALL-E 3", "vision_image", "generation", "Image generation from text prompts.", 1, "per image", "$0.04-0.12/image", 0, "low", "not_integrated", "medium", "Content creation for retreats, social media", "https://platform.openai.com"),
        ("Midjourney", "vision_image", "generation", "Highest quality AI image generation. Discord-based.", 1, "subscription", "$10/mo", 0, "medium", "not_integrated", "medium", "Best quality but harder to automate (Discord API)", "https://midjourney.com"),
        ("Stable Diffusion (SDXL/SD3)", "vision_image", "generation", "Open-source image generation. Run locally or via API.", 1, "free (local) or per image", "$0 local, ~$0.01/img API", 1, "medium", "not_integrated", "medium", "Free option for image generation", "https://stability.ai"),
        ("Flux", "vision_image", "generation", "Fast, high-quality open-source image model from Black Forest Labs.", 1, "free or API", "$0.003/img (Replicate)", 1, "low", "not_integrated", "medium", "Cheapest high-quality option", "https://blackforestlabs.ai"),
        ("GPT-4 Vision / Claude Vision", "vision_image", "analysis", "Analyze images, screenshots, documents with LLMs.", 1, "per token", "Included in LLM pricing", 0, "low", "integrated", "high", "Adam's browser tool uses this for visual analysis", "https://anthropic.com"),
        ("Google Cloud Vision", "vision_image", "analysis", "OCR, object detection, face detection, label detection.", 1, "per image", "$1.50/1K images", 1, "low", "not_integrated", "low", "Claude Vision handles our needs", "https://cloud.google.com/vision"),

        # ========== VIDEO ==========
        ("Runway Gen-3", "video", "generation", "AI video generation from text/image. Industry leader.", 1, "per second", "$0.50/sec gen", 0, "medium", "not_integrated", "low", "Not currently needed, expensive", "https://runwayml.com"),
        ("OpenAI Sora", "video", "generation", "Text-to-video generation. High quality.", 1, "subscription", "$20/mo via ChatGPT Plus", 0, "medium", "not_integrated", "low", "Not currently needed", "https://openai.com/sora"),
        ("HeyGen", "video", "avatar", "AI avatar videos. Spokesperson videos from text.", 1, "subscription", "$24/mo", 0, "low", "not_integrated", "medium", "Could create retreat promo videos automatically", "https://heygen.com"),
        ("Synthesia", "video", "avatar", "AI presenter videos for training and marketing.", 1, "subscription", "$22/mo", 0, "low", "not_integrated", "medium", "Alternative to HeyGen", "https://synthesia.io"),
        ("Captions", "video", "editing", "AI video editing, auto-captions, eye contact correction.", 1, "subscription", "$10/mo", 0, "low", "not_integrated", "low", "Nice-to-have for content", "https://captions.ai"),

        # ========== SEARCH / KNOWLEDGE ==========
        ("Perplexity API", "search_knowledge", "ai_search", "AI-powered search with citations. Real-time web access.", 1, "per query", "$0.005/query (small), $0.02 (pro)", 0, "low", "integrated", "high", "Adam has perplexity.sh tool", "https://perplexity.ai"),
        ("Tavily", "search_knowledge", "ai_search", "Search API built for AI agents. Structured results.", 1, "per query", "$0.005/query, 1K free/mo", 1, "low", "not_integrated", "high", "Better than raw Google for agent search tasks", "https://tavily.com"),
        ("Exa", "search_knowledge", "semantic_search", "Semantic search engine. Finds similar content.", 1, "per query", "Free tier + $0.001/query", 1, "low", "not_integrated", "medium", "Good for finding leads and similar businesses", "https://exa.ai"),
        ("Google Custom Search API", "search_knowledge", "web_search", "Programmable Google search. 100 free queries/day.", 1, "per query", "Free 100/day, then $5/1K", 1, "low", "not_integrated", "medium", "Fallback for web search", "https://developers.google.com/custom-search"),
        ("SerpAPI", "search_knowledge", "web_search", "Scrapes Google/Bing/etc. Structured search results.", 1, "per query", "$50/mo for 5K searches", 1, "low", "not_integrated", "medium", "Reliable search scraping", "https://serpapi.com"),
        ("Firecrawl", "search_knowledge", "web_scraping", "Turn websites into structured data. LLM-ready scraping.", 1, "per page", "$0.004/page, free tier", 1, "low", "not_integrated", "high", "Would massively improve lead scraping quality", "https://firecrawl.dev"),

        # ========== DATA / ANALYTICS ==========
        ("Snowflake Cortex", "data_analytics", "ai_analytics", "AI-powered data analytics on Snowflake.", 1, "usage-based", "Varies", 0, "high", "not_integrated", "low", "Overkill for our scale", "https://snowflake.com"),
        ("Databricks", "data_analytics", "ml_platform", "Unified data + AI platform.", 1, "usage-based", "Varies", 0, "high", "not_integrated", "low", "Enterprise scale, not needed yet", "https://databricks.com"),

        # ========== AGENT FRAMEWORKS ==========
        ("OpenClaw", "agent_frameworks", "agent_runtime", "AI agent framework. Our primary agent runtime for Adam.", 1, "free (self-hosted)", "$0", 1, "medium", "integrated", "critical", "Adam runs on this", "https://openclaw.ai"),
        ("LangChain / LangGraph", "agent_frameworks", "orchestration", "Agent orchestration framework. Chains, graphs, tools.", 1, "free (library)", "$0 + LangSmith $39/mo", 1, "medium", "not_integrated", "medium", "Could improve CORA loop if we outgrow current approach", "https://langchain.com"),
        ("CrewAI", "agent_frameworks", "multi_agent", "Multi-agent orchestration. Role-based agent teams.", 1, "free (library)", "$0", 1, "medium", "not_integrated", "high", "Could replace our custom CORA-Operator with more flexible multi-agent", "https://crewai.com"),
        ("AutoGen", "agent_frameworks", "multi_agent", "Microsoft's multi-agent framework. Conversation-based.", 1, "free (library)", "$0", 1, "medium", "not_integrated", "medium", "Alternative to CrewAI", "https://github.com/microsoft/autogen"),
        ("Dify", "agent_frameworks", "low_code", "Low-code AI app builder. Visual agent workflows.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "medium", "Could build client-facing AI tools faster", "https://dify.ai"),
        ("n8n", "agent_frameworks", "automation", "Workflow automation with AI capabilities. Self-hosted.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "high", "Could automate intake, lead routing, overflow without custom code", "https://n8n.io"),
        ("Composio", "agent_frameworks", "tool_integration", "100+ tool integrations for AI agents. GitHub, Slack, Google, etc.", 1, "free tier", "$0 for 1K actions", 1, "low", "not_integrated", "high", "Instant calendar, email, CRM integrations for Adam", "https://composio.dev"),

        # ========== MEMORY / PERSISTENCE ==========
        ("Mem0", "memory_persistence", "agent_memory", "Long-term memory for AI agents. Cloud or self-hosted.", 1, "free tier + usage", "$0 free tier", 1, "low", "integrated", "high", "Adam uses this for persistent memory", "https://mem0.ai"),
        ("Pinecone", "memory_persistence", "vector_db", "Managed vector database. Fast similarity search.", 1, "usage-based", "$0 free tier (100K vectors)", 1, "low", "not_integrated", "medium", "Could store and search all conversation history", "https://pinecone.io"),
        ("Chroma", "memory_persistence", "vector_db", "Open-source vector database. Run locally.", 1, "free (self-hosted)", "$0", 1, "medium", "not_integrated", "medium", "Free Pinecone alternative", "https://trychroma.com"),
        ("Supabase", "memory_persistence", "database", "Postgres + auth + storage + real-time. Firebase alternative.", 1, "free tier", "$0 free tier, $25/mo pro", 1, "low", "not_integrated", "high", "Could replace our SQLite bus with real-time subscriptions", "https://supabase.com"),
        ("Redis", "memory_persistence", "cache", "In-memory data store. Fast read/write, pub/sub.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "medium", "Could speed up memory bus for real-time use", "https://redis.io"),

        # ========== AUTOMATION / INTEGRATION ==========
        ("Zapier", "automation_integration", "workflow", "Connect 6000+ apps. No-code automation.", 1, "subscription", "$0 free (5 zaps), $20/mo", 1, "low", "not_integrated", "medium", "Quick integrations but recurring cost", "https://zapier.com"),
        ("Make (Integromat)", "automation_integration", "workflow", "Visual automation platform. More flexible than Zapier.", 1, "subscription", "$0 free tier, $10/mo", 1, "low", "not_integrated", "medium", "Alternative to Zapier", "https://make.com"),
        ("Browserbase", "automation_integration", "browser", "Cloud browser infrastructure for AI agents. Headless.", 1, "per session", "$0.01/min", 1, "low", "not_integrated", "high", "Could replace our Playwright setup with managed infra", "https://browserbase.com"),
        ("Steel", "automation_integration", "browser", "Open-source browser API for AI agents.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "medium", "Alternative to Browserbase", "https://steel.dev"),

        # ========== COMMUNICATION ==========
        ("Telegram Bot API", "communication", "messaging", "Bot platform. Our primary communication channel.", 1, "free", "$0", 1, "low", "integrated", "critical", "CORA summaries, steering, alerts all via Telegram", "https://core.telegram.org/bots/api"),
        ("WhatsApp Business API", "communication", "messaging", "Business messaging via WhatsApp. Via Meta or Twilio.", 1, "per message", "$0.005-0.08/msg", 0, "medium", "not_integrated", "medium", "Reach people who don't use Telegram", "https://business.whatsapp.com"),
        ("Twilio", "communication", "voice_sms", "Programmable voice, SMS, WhatsApp.", 1, "per use", "$0.01/min voice, $0.0079/SMS", 0, "low", "integrated", "high", "PersonaPlex voice system uses this", "https://twilio.com"),
        ("Resend", "communication", "email", "Developer-first email API. Our primary email sender.", 1, "per email", "$0 for 3K/mo, then $0.001/email", 1, "low", "integrated", "critical", "Adam's email tool uses this", "https://resend.com"),
        ("Brevo (Sendinblue)", "communication", "email", "Email marketing + transactional. Adam's fallback.", 1, "per email", "$0 for 300/day", 1, "low", "integrated", "high", "Fallback email provider", "https://brevo.com"),
        ("Intercom", "communication", "live_chat", "Customer messaging platform. Live chat + AI.", 1, "subscription", "$39/mo starter", 0, "medium", "not_integrated", "medium", "Could add live chat to fullpotential.ai", "https://intercom.com"),
        ("Crisp", "communication", "live_chat", "Live chat + chatbot + CRM. Self-hosted option.", 1, "subscription", "$0 basic, $25/mo", 1, "low", "not_integrated", "medium", "Cheaper Intercom alternative", "https://crisp.chat"),

        # ========== SCHEDULING ==========
        ("Calendly", "scheduling", "booking", "Automated scheduling. Share link, book meetings.", 1, "subscription", "$0 free (1 event type)", 1, "low", "not_integrated", "critical", "NEEDED for intake agent — book calls automatically", "https://calendly.com"),
        ("Cal.com", "scheduling", "booking", "Open-source Calendly alternative. Self-hosted.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "high", "Free alternative, could self-host on our server", "https://cal.com"),
        ("Google Calendar API", "scheduling", "calendar", "Read/write Google Calendar. Check availability.", 1, "free", "$0", 0, "medium", "not_integrated", "high", "Needed if Sunheart uses Google Calendar", "https://developers.google.com/calendar"),

        # ========== PAYMENT ==========
        ("Stripe", "payment", "processing", "Payment processing. Subscriptions, invoicing.", 1, "per transaction", "2.9% + $0.30", 0, "low", "integrated", "high", "Adam has stripe.sh tool", "https://stripe.com"),
        ("LemonSqueezy", "payment", "digital_products", "Sell digital products. Handles tax, payments.", 1, "per transaction", "5% + $0.50", 0, "low", "not_integrated", "medium", "Could sell Full Potential sessions directly", "https://lemonsqueezy.com"),

        # ========== DOCUMENT / KNOWLEDGE ==========
        ("Notion API", "document_knowledge", "knowledge_base", "Read/write Notion databases and pages.", 1, "free", "$0", 0, "low", "not_integrated", "medium", "Could sync knowledge base with Notion", "https://developers.notion.com"),
        ("Google Docs API", "document_knowledge", "documents", "Create and edit Google Docs programmatically.", 1, "free", "$0", 0, "medium", "not_integrated", "medium", "Generate proposals, contracts", "https://developers.google.com/docs"),
        ("Docusign", "document_knowledge", "e_signature", "Electronic signatures for contracts.", 1, "per envelope", "$10/mo starter", 0, "medium", "not_integrated", "medium", "Needed for client contracts", "https://docusign.com"),

        # ========== BROWSER / WEB ==========
        ("Playwright", "browser_web", "automation", "Browser automation. Screenshots, navigation, interaction.", 1, "free", "$0", 1, "low", "integrated", "high", "Adam's browser tool uses this", "https://playwright.dev"),
        ("Puppeteer", "browser_web", "automation", "Chrome automation by Google. Node.js based.", 1, "free", "$0", 1, "low", "not_integrated", "low", "We use Playwright which is better", "https://pptr.dev"),

        # ========== CRYPTO / FINANCE ==========
        ("CoinGlass", "crypto_finance", "market_data", "Crypto derivatives data. Funding, OI, liquidations.", 1, "api key", "Free tier", 1, "low", "integrated", "high", "Adam's coinglass.sh tool", "https://coinglass.com"),
        ("CoinGecko", "crypto_finance", "market_data", "Crypto prices, market cap, volume. Free API.", 1, "free tier", "$0 free (30 calls/min)", 1, "low", "not_integrated", "medium", "Broader market data than CoinGlass", "https://coingecko.com"),
        ("Binance API", "crypto_finance", "exchange", "Trading and market data from Binance.", 1, "free", "$0 for data", 1, "medium", "not_integrated", "low", "Trading is dormant currently", "https://binance.com"),

        # ========== MONITORING ==========
        ("Sentry", "monitoring", "error_tracking", "Error tracking and performance monitoring.", 1, "subscription", "$0 free tier (5K events)", 1, "low", "not_integrated", "medium", "Would catch service errors automatically", "https://sentry.io"),
        ("Uptime Robot", "monitoring", "uptime", "Website and API uptime monitoring. Free 50 monitors.", 1, "subscription", "$0 free tier", 1, "low", "not_integrated", "high", "Should monitor all our endpoints", "https://uptimerobot.com"),
        ("Grafana + Prometheus", "monitoring", "metrics", "Open-source metrics and dashboards.", 1, "free (self-hosted)", "$0 self-hosted", 1, "high", "not_integrated", "medium", "Beautiful dashboards but heavy setup", "https://grafana.com"),

        # ========== CRM / CONTACTS ==========
        ("Apollo.io", "crm_contacts", "lead_finding", "Find emails and contacts. Enrichment and outreach.", 1, "subscription", "$0 free (10K records/mo)", 1, "low", "integrated", "high", "Leads.py uses Apollo for prospecting", "https://apollo.io"),
        ("Hunter.io", "crm_contacts", "email_finding", "Find emails from domains. Verify emails.", 1, "per search", "$0 free (25/mo), $34/mo", 1, "low", "integrated", "medium", "Leads.py uses Hunter as fallback", "https://hunter.io"),
        ("HubSpot CRM", "crm_contacts", "crm", "Free CRM with contact management, deals, tasks.", 1, "subscription", "$0 free tier", 1, "medium", "not_integrated", "high", "Could replace our SQLite leads DB with proper CRM", "https://hubspot.com"),
        ("Clay", "crm_contacts", "enrichment", "AI-powered lead enrichment and sequencing.", 1, "subscription", "$149/mo", 0, "low", "not_integrated", "medium", "Expensive but powerful lead enrichment", "https://clay.com"),
        ("Instantly.ai", "crm_contacts", "outreach", "Cold email automation with warming and rotation.", 1, "subscription", "$30/mo", 0, "low", "not_integrated", "high", "Could automate email outreach at scale", "https://instantly.ai"),

        # ========== SOCIAL MEDIA ==========
        ("Meta Graph API", "social_media", "facebook_instagram", "Post, read, ads on Facebook and Instagram.", 1, "free", "$0 (plus ad spend)", 1, "medium", "integrated", "high", "Adam has facebook.sh tool", "https://developers.facebook.com"),
        ("Twitter/X API", "social_media", "twitter", "Post, read, search tweets.", 1, "subscription", "$100/mo basic", 0, "low", "not_integrated", "low", "Expensive for limited value", "https://developer.x.com"),
        ("LinkedIn API", "social_media", "linkedin", "Post content, read profile data. Limited.", 1, "subscription", "Restricted access", 0, "high", "not_integrated", "medium", "Hard to automate but valuable for B2B", "https://developer.linkedin.com"),
        ("Buffer", "social_media", "scheduling", "Schedule posts across social platforms.", 1, "subscription", "$0 free (3 channels)", 1, "low", "not_integrated", "medium", "Batch and schedule social content", "https://buffer.com"),

        # ========== AI SAFETY / EVAL ==========
        ("Patronus AI", "ai_safety", "evaluation", "LLM evaluation and hallucination detection.", 1, "subscription", "Custom pricing", 0, "medium", "not_integrated", "low", "Relevant when we productize AI services", "https://patronus.ai"),
        ("Langfuse", "ai_safety", "observability", "Open-source LLM observability. Trace, evaluate, debug.", 1, "free (self-hosted)", "$0 self-hosted", 1, "medium", "not_integrated", "high", "Would help debug and optimize our Claude usage", "https://langfuse.com"),
    ]

    inserted = 0
    for entry in entries:
        try:
            db.execute(
                """INSERT OR IGNORE INTO capabilities_global
                   (name, category, subcategory, what_it_does, api_available,
                    pricing_model, approximate_cost, free_tier, integration_complexity,
                    our_status, relevance, relevance_reason, url, last_verified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*entry, now)
            )
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {entry[0]}: {e}")

    db.commit()
    total = db.execute("SELECT COUNT(*) FROM capabilities_global").fetchone()[0]
    print(f"Seeded {inserted} entries. Total in database: {total}")
    return total


def run_gap_analysis():
    """Compare our integrated capabilities against the full landscape."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Find categories where we have nothing integrated
    cats = db.execute("""
        SELECT category, 
               COUNT(*) as total,
               SUM(CASE WHEN our_status = 'integrated' THEN 1 ELSE 0 END) as integrated,
               SUM(CASE WHEN relevance = 'high' OR relevance = 'critical' THEN 1 ELSE 0 END) as high_rel
        FROM capabilities_global
        GROUP BY category
        ORDER BY high_rel DESC
    """).fetchall()

    gaps = []
    for cat in cats:
        if cat["integrated"] == 0 and cat["high_rel"] > 0:
            # Full gap — nothing integrated in a high-relevance category
            options = db.execute(
                "SELECT name, approximate_cost, integration_complexity, relevance_reason FROM capabilities_global WHERE category = ? AND relevance IN ('high', 'critical') ORDER BY relevance DESC",
                (cat["category"],)
            ).fetchall()

            gap = {
                "gap_name": f"No {cat['category'].replace('_', ' ')} capability",
                "category": cat["category"],
                "current_state": "Nothing integrated",
                "available_options": ", ".join(o["name"] for o in options),
                "recommended": options[0]["name"] if options else "None",
                "integration_effort": options[0]["integration_complexity"] if options else "unknown",
                "impact": options[0]["relevance_reason"] if options else "",
                "priority": "high" if cat["high_rel"] >= 2 else "medium",
            }
            gaps.append(gap)

        elif cat["integrated"] > 0:
            # Partial gap — we have something but there are better/missing options
            not_integrated_high = db.execute(
                "SELECT name, relevance_reason, approximate_cost FROM capabilities_global WHERE category = ? AND our_status != 'integrated' AND relevance IN ('high', 'critical')",
                (cat["category"],)
            ).fetchall()

            if not_integrated_high:
                integrated = db.execute(
                    "SELECT name FROM capabilities_global WHERE category = ? AND our_status = 'integrated'",
                    (cat["category"],)
                ).fetchall()

                gap = {
                    "gap_name": f"Missing {cat['category'].replace('_', ' ')} options",
                    "category": cat["category"],
                    "current_state": f"Have: {', '.join(i['name'] for i in integrated)}",
                    "available_options": ", ".join(o["name"] for o in not_integrated_high),
                    "recommended": not_integrated_high[0]["name"],
                    "integration_effort": "low-medium",
                    "impact": not_integrated_high[0]["relevance_reason"],
                    "priority": "medium",
                }
                gaps.append(gap)

    # Write gaps to DB
    for gap in gaps:
        db.execute(
            """INSERT OR REPLACE INTO gap_analysis
               (gap_name, category, current_state, available_options, recommended,
                integration_effort, impact, priority, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (gap["gap_name"], gap["category"], gap["current_state"],
             gap["available_options"], gap["recommended"], gap["integration_effort"],
             gap["impact"], gap["priority"], now)
        )
    db.commit()

    # Write to bus
    try:
        import requests
        requests.post("http://127.0.0.1:8195/bus/messages", json={
            "from": "intel_scanner",
            "to": "cora",
            "type": "gap_analysis",
            "priority": "high",
            "content": {"gaps": gaps, "generated_at": now},
        }, timeout=5)
    except Exception:
        pass

    # Print
    print(f"\n{'='*70}")
    print("GAP ANALYSIS — Our Stack vs Global AI Capabilities")
    print(f"{'='*70}")

    for gap in sorted(gaps, key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g["priority"], 3)):
        icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(gap["priority"], "?")
        print(f"\n{icon} GAP: {gap['gap_name']}")
        print(f"   CURRENT: {gap['current_state']}")
        print(f"   AVAILABLE: {gap['available_options']}")
        print(f"   RECOMMENDED: {gap['recommended']}")
        print(f"   EFFORT: {gap['integration_effort']}")
        print(f"   IMPACT: {gap['impact']}")
        print(f"   PRIORITY: {gap['priority']}")

    print(f"\n{len(gaps)} gaps identified.")
    return gaps


def cmd_list(category=None):
    db = get_db()
    if category:
        rows = db.execute("SELECT * FROM capabilities_global WHERE category = ? ORDER BY relevance DESC, name", (category,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM capabilities_global ORDER BY category, relevance DESC, name").fetchall()

    if not rows:
        print("No entries." + (f" Category '{category}' not found." if category else ""))
        return

    current_cat = None
    for r in rows:
        if r["category"] != current_cat:
            current_cat = r["category"]
            print(f"\n  === {current_cat.upper().replace('_', ' ')} ===")
        status_icon = {"integrated": "✅", "not_integrated": "  ", "testing": "🧪", "evaluated": "👁️"}.get(r["our_status"], "  ")
        rel_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(r["relevance"], "  ")
        print(f"  {status_icon} {rel_icon} {r['name']:<30} {(r['approximate_cost'] or ''):>25}  {(r['what_it_does'] or '')[:50]}")

    total = len(rows)
    integrated = sum(1 for r in rows if r["our_status"] == "integrated")
    print(f"\n  Total: {total} | Integrated: {integrated} | Gaps: {total - integrated}")


def cmd_search(query):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM capabilities_global WHERE name LIKE ? OR what_it_does LIKE ? OR category LIKE ? ORDER BY relevance DESC",
        (f"%{query}%", f"%{query}%", f"%{query}%")
    ).fetchall()
    if not rows:
        print(f"No results for '{query}'")
        return
    for r in rows:
        status = {"integrated": "✅", "not_integrated": "❌"}.get(r["our_status"], "?")
        print(f"  {status} [{r['relevance']:8}] {r['name']:<30} ({r['category']})")
        print(f"     {r['what_it_does'][:80]}")
        print(f"     Cost: {r['approximate_cost']} | Complexity: {r['integration_complexity']} | {r['url']}")
        print()


def cmd_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM capabilities_global").fetchone()[0]
    integrated = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE our_status = 'integrated'").fetchone()[0]
    by_cat = db.execute("SELECT category, COUNT(*) c FROM capabilities_global GROUP BY category ORDER BY c DESC").fetchall()
    by_relevance = db.execute("SELECT relevance, COUNT(*) c FROM capabilities_global GROUP BY relevance ORDER BY c DESC").fetchall()
    free = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE free_tier = 1").fetchone()[0]

    print(f"Global AI Capability Database")
    print(f"  Total entries:    {total}")
    print(f"  Integrated:       {integrated} ({100*integrated//max(total,1)}%)")
    print(f"  With free tier:   {free}")
    print(f"\n  By category:")
    for r in by_cat:
        print(f"    {r['category']:<30} {r['c']}")
    print(f"\n  By relevance:")
    for r in by_relevance:
        print(f"    {r['relevance']:<10} {r['c']}")


def cmd_export():
    db = get_db()
    rows = db.execute("SELECT * FROM capabilities_global ORDER BY category, name").fetchall()
    out = [dict(r) for r in rows]
    path = "/opt/fpai/memory-bus/capabilities_global.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Exported {len(out)} entries to {path}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "seed":
        seed_baseline()
    elif cmd == "list":
        cmd_list(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "gaps":
        run_gap_analysis()
    elif cmd == "search":
        cmd_search(" ".join(sys.argv[2:]) if len(sys.argv) > 2 else "")
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "export":
        cmd_export()
    else:
        print(__doc__)
