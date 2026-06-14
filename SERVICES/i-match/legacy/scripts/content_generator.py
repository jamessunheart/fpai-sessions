#!/usr/bin/env python3
"""
Autonomous SEO Content Generator
Generates high-value financial advice pages that rank in search and drive traffic to I MATCH
NO CREDENTIALS REQUIRED - Just deploys content
"""

import os
import anthropic
from pathlib import Path

class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.output_dir = Path("static/advice")
        self.output_dir.mkdir(exist_ok=True)

    def generate_advice_page(self, topic: str, question: str) -> str:
        """Generate a complete HTML advice page"""

        prompt = f"""You are a financial advisor writing genuinely helpful content.

TOPIC: {topic}
MAIN QUESTION: {question}

Create a comprehensive, helpful article that:
1. Actually answers the question (no fluff)
2. Provides actionable advice
3. Introduces Full Potential AI philosophy where relevant:
   - Alignment over Assets
   - Transparency over Complexity
   - Growth Mindset over Preservation
4. Naturally mentions I MATCH as resource for finding aligned advisor
5. Is 800-1200 words
6. Uses clear headings and structure

Write the BODY CONTENT only (I'll add HTML wrapper).
Use markdown formatting (## for h2, ### for h3, **bold**, etc.)
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Convert markdown to HTML and wrap in template
        html = self._wrap_in_html_template(question, content, topic)

        return html

    def _wrap_in_html_template(self, title: str, content: str, description: str) -> str:
        """Wrap content in SEO-optimized HTML template"""

        # Simple markdown conversion
        html_content = content
        html_content = html_content.replace('## ', '<h2>').replace('\n\n', '</h2>\n\n')
        html_content = html_content.replace('### ', '<h3>').replace('\n', '</h3>\n')
        html_content = html_content.replace('**', '<strong>').replace('**', '</strong>')
        html_content = html_content.replace('\n\n', '</p>\n<p>')
        html_content = '<p>' + html_content + '</p>'

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | I MATCH Financial Advice</title>
    <meta name="description" content="{description[:160]}">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 36px;
            margin-bottom: 20px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }}

        .header .breadcrumb {{
            opacity: 0.9;
            font-size: 14px;
        }}

        .header .breadcrumb a {{
            color: white;
            text-decoration: none;
        }}

        .container {{
            max-width: 800px;
            margin: -40px auto 60px;
            background: white;
            padding: 60px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}

        .content h2 {{
            color: #667eea;
            font-size: 28px;
            margin: 40px 0 20px;
        }}

        .content h3 {{
            color: #333;
            font-size: 22px;
            margin: 30px 0 15px;
        }}

        .content p {{
            margin-bottom: 20px;
            font-size: 18px;
            line-height: 1.8;
        }}

        .content strong {{
            color: #764ba2;
            font-weight: 600;
        }}

        .cta-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 15px;
            margin: 50px 0;
            text-align: center;
        }}

        .cta-box h3 {{
            color: white;
            font-size: 26px;
            margin-bottom: 20px;
        }}

        .cta-box p {{
            color: white;
            font-size: 18px;
            margin-bottom: 25px;
            opacity: 0.95;
        }}

        .cta-button {{
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 15px 35px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            font-size: 18px;
            transition: all 0.3s;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }}

        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #666;
            background: white;
            margin-top: 60px;
        }}

        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="breadcrumb">
            <a href="/">I MATCH</a> / <a href="/advice">Financial Advice</a>
        </div>
        <h1>{title}</h1>
    </div>

    <div class="container">
        <div class="content">
            {html_content}
        </div>

        <div class="cta-box">
            <h3>Ready to Find Your Perfect Advisor Match?</h3>
            <p>I MATCH uses AI to analyze 100+ compatibility factors and connect you with advisors who share your values and vision.</p>
            <a href="/match" class="cta-button">Get Matched in 2 Minutes</a>
        </div>
    </div>

    <div class="footer">
        <p><a href="/">I MATCH</a> | <a href="/compatibility-quiz.html">Take Our Quiz</a> | <a href="/advice">More Advice</a></p>
        <p style="margin-top: 15px; font-size: 14px;">Powered by Full Potential AI - Transparent, Values-Aligned Financial Matching</p>
    </div>
</body>
</html>'''

    def generate_top_20_pages(self):
        """Generate the top 20 most-searched financial advice topics"""

        topics = [
            {
                "slug": "how-to-find-financial-advisor",
                "question": "How to Find a Financial Advisor",
                "description": "Step-by-step guide to finding a financial advisor who aligns with your values and vision"
            },
            {
                "slug": "fee-only-vs-commission-advisor",
                "question": "Fee-Only vs Commission Financial Advisor: What's the Difference?",
                "description": "Understanding advisor fee structures and avoiding conflicts of interest"
            },
            {
                "slug": "questions-to-ask-financial-advisor",
                "question": "20 Essential Questions to Ask a Financial Advisor",
                "description": "Critical questions that reveal whether an advisor is right for you"
            },
            {
                "slug": "how-much-does-financial-advisor-cost",
                "question": "How Much Does a Financial Advisor Cost?",
                "description": "Complete breakdown of financial advisor fees and what you should expect to pay"
            },
            {
                "slug": "do-i-need-financial-advisor",
                "question": "Do I Need a Financial Advisor?",
                "description": "When to hire a financial advisor and when to manage investments yourself"
            },
            {
                "slug": "fiduciary-vs-financial-advisor",
                "question": "Fiduciary vs Financial Advisor: Why It Matters",
                "description": "Understanding fiduciary duty and why it protects your interests"
            },
            {
                "slug": "finding-financial-advisor-in-your-20s",
                "question": "Finding a Financial Advisor in Your 20s",
                "description": "Financial guidance for young professionals building wealth"
            },
            {
                "slug": "certified-financial-planner-vs-advisor",
                "question": "CFP vs Financial Advisor: Which Do You Need?",
                "description": "Understanding financial advisor certifications and credentials"
            },
            {
                "slug": "online-financial-advisor-vs-in-person",
                "question": "Online vs In-Person Financial Advisor",
                "description": "Pros and cons of virtual financial advisory relationships"
            },
            {
                "slug": "vanguard-vs-personal-financial-advisor",
                "question": "Robo-Advisor vs Personal Financial Advisor",
                "description": "When automation works and when you need human guidance"
            },
            {
                "slug": "financial-advisor-for-small-business-owners",
                "question": "Financial Advisors for Small Business Owners",
                "description": "Specialized financial planning for entrepreneurs"
            },
            {
                "slug": "how-to-switch-financial-advisors",
                "question": "How to Switch Financial Advisors",
                "description": "Step-by-step process for changing financial advisors"
            },
            {
                "slug": "financial-advisor-red-flags",
                "question": "10 Red Flags When Choosing a Financial Advisor",
                "description": "Warning signs that an advisor may not be right for you"
            },
            {
                "slug": "wealth-manager-vs-financial-advisor",
                "question": "Wealth Manager vs Financial Advisor: Key Differences",
                "description": "Understanding different types of financial professionals"
            },
            {
                "slug": "find-financial-advisor-near-me",
                "question": "How to Find a Financial Advisor Near Me",
                "description": "Local vs virtual advisors and what matters most"
            },
            {
                "slug": "financial-advisor-for-inheritance",
                "question": "Finding a Financial Advisor After Receiving Inheritance",
                "description": "Managing sudden wealth and finding trustworthy guidance"
            },
            {
                "slug": "best-financial-advisor-for-millennials",
                "question": "Best Financial Advisors for Millennials",
                "description": "Modern financial advice for the millennial generation"
            },
            {
                "slug": "transparent-financial-advising",
                "question": "The Case for Transparent Financial Advising",
                "description": "Why transparency matters more than credentials"
            },
            {
                "slug": "values-aligned-financial-planning",
                "question": "Values-Aligned Financial Planning",
                "description": "Matching your money with your meaning"
            },
            {
                "slug": "growth-mindset-financial-planning",
                "question": "Growth Mindset vs Traditional Financial Planning",
                "description": "Thinking bigger than just retirement"
            }
        ]

        print(f"\n🚀 Generating {len(topics)} SEO-Optimized Advice Pages\n")

        for i, topic in enumerate(topics, 1):
            print(f"📝 {i}/{len(topics)}: {topic['question']}")

            html = self.generate_advice_page(topic['description'], topic['question'])

            output_file = self.output_dir / f"{topic['slug']}.html"
            with open(output_file, 'w') as f:
                f.write(html)

            print(f"   ✅ Generated: {output_file}")

        # Create index page
        self._create_advice_index(topics)

        print(f"\n✅ ALL {len(topics)} PAGES GENERATED")
        print(f"📂 Location: {self.output_dir}")
        print(f"\n🌐 Next: Deploy to production server")

    def _create_advice_index(self, topics):
        """Create index page listing all advice articles"""

        articles_html = "\n".join([
            f'<div class="article-card"><h3><a href="/advice/{topic["slug"]}.html">{topic["question"]}</a></h3><p>{topic["description"]}</p></div>'
            for topic in topics
        ])

        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Advice & Guidance | I MATCH</title>
    <meta name="description" content="Expert financial advice on finding advisors, understanding fees, and making smart money decisions.">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 80px 20px; text-align: center; }}
        .header h1 {{ font-size: 48px; margin-bottom: 20px; }}
        .header p {{ font-size: 20px; opacity: 0.95; }}
        .container {{ max-width: 1200px; margin: -60px auto 60px; }}
        .articles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 30px; padding: 0 20px; }}
        .article-card {{ background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); transition: all 0.3s; }}
        .article-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.15); }}
        .article-card h3 {{ color: #667eea; margin-bottom: 15px; font-size: 22px; }}
        .article-card a {{ color: #667eea; text-decoration: none; }}
        .article-card a:hover {{ color: #764ba2; }}
        .article-card p {{ color: #666; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Financial Advice & Guidance</h1>
        <p>Expert insights on finding advisors, understanding fees, and making smart money decisions</p>
    </div>
    <div class="container">
        <div class="articles">
            {articles_html}
        </div>
    </div>
</body>
</html>'''

        with open(self.output_dir / "index.html", 'w') as f:
            f.write(index_html)

        print(f"   ✅ Created index: {self.output_dir}/index.html")


if __name__ == "__main__":
    generator = ContentGenerator()
    generator.generate_top_20_pages()
