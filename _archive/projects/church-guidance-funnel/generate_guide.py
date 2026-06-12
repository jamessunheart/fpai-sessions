#!/usr/bin/env python3
"""
Generate the free church formation guide using Claude API
"""

import anthropic
import os

def generate_guide():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
    client = anthropic.Anthropic(api_key=api_key)

    prompt = """Generate a comprehensive educational guide about 508(c)(1)(A) church formation.

This is EDUCATIONAL INFORMATION ONLY, not legal advice.

Create a complete guide with these sections:

# The Complete 508(c)(1)(A) Church Formation Guide

## DISCLAIMER
[Full legal disclaimer - this is educational only, not legal advice]

## Introduction
- What this guide covers
- Who this is for
- Important notes about using this information

## Chapter 1: Understanding 508(c)(1)(A) Churches
- What is a 508(c)(1)(A) church
- Legal basis (First Amendment, IRC Section 508)
- Historical context
- Why it exists

## Chapter 2: Benefits of 508(c)(1)(A)
- Tax-exempt status without IRS application
- Privacy protections
- No Form 990 filing requirement
- Constitutional protections
- Comparison with 501(c)(3)

## Chapter 3: Requirements and Qualifications
- What qualifies as a church
- Religious purpose requirement
- Organizational structure
- Documentation needed

## Chapter 4: Formation Process Overview
- Step-by-step high-level process
- Timeline expectations
- Common paths
- State considerations

## Chapter 5: Essential Documents
- Articles of Faith
- Church Bylaws
- IRS Letter 1045
- Operating procedures
- Meeting minutes templates

## Chapter 6: Recordkeeping and Compliance
- What records to keep
- How long to maintain records
- Best practices
- Annual requirements

## Chapter 7: Common Mistakes to Avoid
- Top 10 formation mistakes
- Compliance pitfalls
- Red flags to watch for

## Chapter 8: Ongoing Operations
- Regular meetings
- Financial management
- Member management
- Growth considerations

## Chapter 9: State-Specific Considerations
- State registration requirements
- State tax exemptions
- Reporting obligations

## Chapter 10: Resources and Next Steps
- Recommended resources
- Where to get help
- Professional guidance
- How our AI tools can help

## Appendix A: Sample Documents
## Appendix B: Glossary
## Appendix C: FAQs

Format: Professional, educational, accessible to non-lawyers
Tone: Helpful, informative, empowering
Length: Comprehensive (aim for ~20-25 pages of content)

Include disclaimers throughout. Make it genuinely useful while being clear it's educational only."""

    print("Generating church formation guide...")

    message = client.messages.create(
        model="claude-3-haiku-20240307",  # Model that worked earlier
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    guide_content = message.content[0].text

    # Save to markdown file
    with open("church_formation_guide.md", "w") as f:
        f.write(guide_content)

    print(f"\n✅ Guide generated and saved to church_formation_guide.md")
    print(f"Length: {len(guide_content)} characters")

    return guide_content

if __name__ == "__main__":
    generate_guide()
