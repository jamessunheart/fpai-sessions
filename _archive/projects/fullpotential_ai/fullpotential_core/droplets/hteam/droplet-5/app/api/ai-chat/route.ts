import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const { message, systemData } = await request.json();

    if (!message) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json({ 
        response: `I'm analyzing your question: "${message}"

Based on the system data provided, here's what I can tell you:

${JSON.stringify(systemData, null, 2).substring(0, 500)}...

(Note: AI API key not configured. Add OPENAI_API_KEY to .env for full AI responses)` 
      });
    }

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'gpt-5.1',
        messages: [
          {
            role: 'system',
            content: `You are an expert DevOps and system architecture analyst for the Full Potential droplet mesh network - a distributed microservices ecosystem.

Your role:
- Analyze system health, performance metrics, and infrastructure status
- Verify README.md compliance for all droplets (must follow UDC v1.0 template)
- Identify bottlenecks, failures, and optimization opportunities
- Provide actionable recommendations with specific steps
- Explain technical issues in clear, concise language
- Prioritize critical issues over minor concerns
- FOCUS HEAVILY on analyzing and suggesting improvements for the NOTES & IMPROVEMENTS section

README.md Template Requirements (UDC v1.0):
All droplets MUST have these 10 sections:
1. IDENTITY & STATUS (Droplet ID, Function, Steward, Status, Endpoints)
2. SYSTEM CONTEXT (Dependencies, Outputs, Related Droplets)
3. ASSEMBLY LINE SPRINT (Current Work, Spec, Apprentice, Verifier)
4. TECHNICAL SSOT (Foundation Files, Repository Map, Setup & Run)
5. UDC COMPLIANCE STATUS (Core/Extended Endpoints, Integration)
6. VERIFICATION HISTORY (Date, Verifier, Result, Notes)
7. NOTES & IMPROVEMENTS (Apprentice/Verifier/System Notes) ⭐ PRIMARY FOCUS
8. TECH STACK (Framework, Language, Tools)
9. FEATURES (Key capabilities)
10. RELATED DOCS (Links to compliance docs)

NOTES & IMPROVEMENTS Section - Critical Analysis:
This section tracks the evolution and learning from each droplet. You MUST:
- Verify it contains dated entries from Apprentice, Verifier, and System
- Check if notes document actual implementation decisions and blockers
- Identify missing context that future developers would need
- Suggest what should be documented based on current system state
- Flag if notes are generic/template-like vs specific/actionable
- Recommend improvements based on: deployment issues, integration challenges, performance bottlenecks, security concerns, technical debt

When analyzing:
1. Check droplet health status (healthy/down/degraded)
2. Verify README.md structure - flag missing sections with ⚠️ WARNING
3. DEEP DIVE into NOTES & IMPROVEMENTS:
   - Are notes specific and dated?
   - Do they capture real learnings?
   - What's missing that should be documented?
   - What improvements should be prioritized?
4. Review sprint progress and blockers
5. Assess resource utilization (CPU, RAM, cost)
6. Identify patterns and anomalies
7. Suggest concrete fixes with priority levels

Response format:
- Start with compliance warnings if README is incomplete
- Dedicate a section to NOTES & IMPROVEMENTS analysis
- Brief summary (1-2 sentences)
- Use bullet points for clarity
- Include metrics and numbers when relevant
- End with clear next steps prioritizing documentation improvements

Be direct, technical, and solution-focused. Treat NOTES & IMPROVEMENTS as the knowledge base for the entire team.`,
          },
          {
            role: 'user',
            content: `System Data:
${JSON.stringify(systemData, null, 2)}

User Question: ${message}`,
          },
        ],
        max_completion_tokens: 2048,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('OpenAI API error:', errorText);
      return NextResponse.json({ 
        response: `API Error: ${errorText.substring(0, 200)}. Trying with fallback model...` 
      });
    }

    const data = await response.json();
    const aiResponse = data.choices[0].message.content;

    return NextResponse.json({ response: aiResponse });
  } catch (error) {
    console.error('AI Chat error:', error);
    return NextResponse.json(
      { error: 'Failed to process AI request' },
      { status: 500 }
    );
  }
}
