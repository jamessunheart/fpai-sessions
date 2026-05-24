/**
 * Cloudflare Worker — Outbounders AI Script Generator backend
 *
 * Calls Anthropic Claude (Haiku for cost) to generate outbound sales scripts.
 * Reads system prompt from KV or env, builds user prompt from form data, returns markdown.
 *
 * Bind ANTHROPIC_API_KEY as a Worker secret:
 *   wrangler secret put ANTHROPIC_API_KEY
 *
 * Optional KV namespace SCRIPT_GEN_KV for rate-limiting + prompt versioning.
 */

const SYSTEM_PROMPT = `You are an outbound sales script writer with 15 years of experience writing scripts for B2B telemarketing campaigns across SaaS, insurance, real estate, financial services, lead-gen, and direct response. You write for human agents who will deliver the script live on phone calls.

Always return exactly four sections, in this order:

### 1. CALLING SCRIPT (~800 words)
A complete script the agent reads on the call. Structure: pattern-interrupt opener · permission frame · value pitch · qualifying questions · soft close. Use natural spoken language. No corporate jargon. Short sentences. Insert [PAUSE] markers where the agent should let the prospect respond.

### 2. TOP 10 OBJECTIONS + REBUTTALS
Number 1-10. Each: **Objection:** verbatim what the prospect would say · **Rebuttal:** 2-3 sentence response — acknowledge first, then reframe, then return-question. Order from most-common to most-specific.

### 3. FIVE QUALIFYING QUESTIONS
Numbered 1-5. Each surfaces a specific data point that determines fit, answerable in <30s, not interrogation-feeling (use "curious" / "help me understand" framing).

### 4. HANDOFF / NEXT-STEPS SCRIPT
Short close script: book a meeting / send follow-up / schedule callback. Exact language for the agent.

Style: confident-operator tone, crisp, no fluff. Result-language over feature-language. No hype words ("game-changer", "revolutionary", etc.). Honor TCPA/DNC/SEC/HIPAA/FINRA where relevant. Don't write scripts for scam-pattern industries. Don't promise specific results. Don't pad.`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    };

    if (request.method === "OPTIONS") return new Response(null, {headers: cors});

    if (url.pathname !== "/api/generate" || request.method !== "POST") {
      return new Response(JSON.stringify({error: "Not found"}), {
        status: 404, headers: {"Content-Type": "application/json", ...cors}
      });
    }

    let body;
    try { body = await request.json(); }
    catch { return json({error: "Invalid JSON"}, 400, cors); }

    const required = ["industry", "offer", "target_role", "target_company_size", "call_goal"];
    for (const f of required) {
      if (!body[f] || typeof body[f] !== "string") {
        return json({error: `Missing field: ${f}`}, 400, cors);
      }
      if (body[f].length > 1000) {
        return json({error: `Field too long: ${f}`}, 400, cors);
      }
    }

    const userPrompt = `Here's the campaign:

**Industry / Vertical:** ${body.industry}

**Product / Offer:** ${body.offer}

**Target persona:**
- Role / title: ${body.target_role}
- Company size: ${body.target_company_size}
- Geography: ${body.target_geography || "Not specified"}

**Call goal:** ${body.call_goal}

**Additional context:** ${body.additional_context || "None provided"}

Generate the four sections per your instructions. Return as clean markdown.`;

    try {
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01"
        },
        body: JSON.stringify({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 3000,
          system: SYSTEM_PROMPT,
          messages: [{role: "user", content: userPrompt}]
        })
      });

      if (!r.ok) {
        const errText = await r.text();
        console.error("Anthropic API error:", r.status, errText);
        return json({error: "Generation failed. Try again in a moment."}, 502, cors);
      }

      const data = await r.json();
      const script = data.content?.[0]?.text || "";
      return json({script, model: data.model, usage: data.usage}, 200, cors);

    } catch (err) {
      console.error("Worker error:", err);
      return json({error: "Internal error"}, 500, cors);
    }
  }
};

function json(body, status, cors) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {"Content-Type": "application/json", ...cors}
  });
}
