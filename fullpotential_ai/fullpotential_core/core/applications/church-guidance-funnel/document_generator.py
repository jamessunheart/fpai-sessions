#!/usr/bin/env python3
"""
AI Document Generator for Church Formation Guidance
Generates customized church documents based on user input
"""

import anthropic
import os
import json
from datetime import datetime
from typing import Dict, List

class ChurchDocumentGenerator:
    """Generates customized church formation documents using Claude AI"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-haiku-20240307"

    def generate_articles_of_faith(self, user_data: Dict) -> str:
        """Generate customized Articles of Faith"""

        prompt = f"""Generate a comprehensive Articles of Faith document for a 508(c)(1)(A) church.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- State: {user_data.get('state')}
- Religious Tradition: {user_data.get('tradition', 'Not specified')}
- Core Beliefs: {user_data.get('core_beliefs')}
- Mission Statement: {user_data.get('mission_statement')}

REQUIREMENTS:
1. Create a professional Articles of Faith document
2. Include 8-12 core doctrinal statements
3. Base the statements on the provided beliefs
4. Use formal religious language
5. Include sections on: Scripture, God, Salvation, Church, Worship, Leadership
6. Make it specific to their stated beliefs, not generic

FORMAT:
- Start with church name and document title
- Number each article
- Keep each article clear and concise
- End with signature/adoption section

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: This document is a template generated for educational purposes based on your input. It has not been reviewed by an attorney. Before using this document, consult with a qualified attorney licensed in your state to ensure it meets all legal requirements and is appropriate for your specific situation."

Generate the complete Articles of Faith document now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_bylaws(self, user_data: Dict) -> str:
        """Generate customized Church Bylaws"""

        prompt = f"""Generate comprehensive Church Bylaws for a 508(c)(1)(A) church.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- State: {user_data.get('state')}
- Governance Model: {user_data.get('governance_model')}
- Leadership Structure: {user_data.get('leadership_structure', 'Not specified')}
- Membership Requirements: {user_data.get('membership_requirements', 'Not specified')}
- Meeting Frequency: {user_data.get('meeting_frequency', 'Not specified')}
- Activities: {user_data.get('activities', 'Not specified')}

REQUIREMENTS:
1. Create comprehensive bylaws covering all standard church governance areas
2. Tailor to their specific governance model
3. Include sections on:
   - Article I: Name and Purpose
   - Article II: Statement of Faith
   - Article III: Membership
   - Article IV: Leadership and Officers
   - Article V: Meetings
   - Article VI: Finances
   - Article VII: Amendments
   - Article VIII: Dissolution

4. Make provisions specific to 508(c)(1)(A) status
5. Include state-specific considerations for {user_data.get('state')}
6. Use formal legal language
7. Include voting procedures appropriate to their governance model

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: This document is a template generated for educational purposes based on your input. It has not been reviewed by an attorney. Before using this document, consult with a qualified attorney licensed in {user_data.get('state')} to ensure it meets all legal requirements and is appropriate for your specific situation. State laws vary significantly."

Generate the complete Bylaws document now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_irs_letter_1045(self, user_data: Dict) -> str:
        """Generate IRS Letter 1045 (Notice of Church Tax-Exempt Status)"""

        prompt = f"""Generate an IRS Letter 1045 template for notifying the IRS of 508(c)(1)(A) church tax-exempt status.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- State: {user_data.get('state')}
- Core Beliefs: {user_data.get('core_beliefs')}
- Activities: {user_data.get('activities', 'Not specified')}

REQUIREMENTS:
1. Create a formal letter to the IRS
2. Reference IRC Section 508(c)(1)(A) explicitly
3. State that the church is claiming automatic exemption
4. Include required church information
5. Reference First Amendment protections
6. List church activities proving religious purpose
7. Include proper formatting for IRS correspondence

CRITICAL NOTES:
- This is a NOTIFICATION, not an application
- Churches under 508(c)(1)(A) are not required to apply for tax-exempt status
- This letter is optional but recommended for record-keeping

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: This is an educational template. We are not attorneys or tax professionals and this is not legal or tax advice. Before sending any correspondence to the IRS, consult with a qualified tax attorney or CPA licensed in {user_data.get('state')} to ensure this is appropriate for your situation and complies with current IRS requirements."

Generate the complete IRS Letter 1045 template now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_operating_procedures(self, user_data: Dict) -> str:
        """Generate Operating Procedures document"""

        prompt = f"""Generate comprehensive Operating Procedures for a 508(c)(1)(A) church.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- Governance Model: {user_data.get('governance_model')}
- Meeting Frequency: {user_data.get('meeting_frequency')}
- Financial Model: {user_data.get('financial_model', 'Not specified')}
- Activities: {user_data.get('activities', 'Not specified')}

REQUIREMENTS:
1. Create detailed operating procedures covering:
   - Worship Service Procedures
   - Financial Management (offerings, expenses, record-keeping)
   - Meeting Procedures (how to conduct, minutes)
   - Membership Procedures (joining, discipline, removal)
   - Leadership Selection Procedures
   - Conflict Resolution Procedures
   - Amendment Procedures

2. Make procedures practical and actionable
3. Align with their governance model
4. Include record-keeping requirements for 508(c)(1)(A) compliance
5. Include best practices for maintaining religious autonomy

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: These are educational templates for church operating procedures. They have not been reviewed by legal counsel. Consult with a qualified attorney to ensure these procedures are appropriate for your specific situation and comply with applicable laws."

Generate the complete Operating Procedures document now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_meeting_minutes_template(self, user_data: Dict) -> str:
        """Generate Meeting Minutes Template"""

        prompt = f"""Generate a Meeting Minutes Template for a 508(c)(1)(A) church.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- Governance Model: {user_data.get('governance_model')}
- Meeting Frequency: {user_data.get('meeting_frequency')}

REQUIREMENTS:
1. Create a reusable template for documenting church meetings
2. Include sections for:
   - Meeting date, time, location
   - Attendees (leadership/members present)
   - Opening prayer/devotional
   - Approval of previous minutes
   - Reports (financial, ministry, etc.)
   - Old business
   - New business
   - Decisions and votes
   - Action items
   - Next meeting date
   - Adjournment
   - Signature section

3. Include instructions for proper record-keeping
4. Note which decisions require voting vs. consensus
5. Emphasize importance of maintaining these records

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: This is an educational template. Proper record-keeping is essential for maintaining your church's integrity and legal standing. Consult with a qualified attorney about record retention requirements in {user_data.get('state')}."

Generate the complete Meeting Minutes Template now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_recordkeeping_guidelines(self, user_data: Dict) -> str:
        """Generate Recordkeeping Guidelines"""

        prompt = f"""Generate comprehensive Recordkeeping Guidelines for a 508(c)(1)(A) church.

CHURCH INFORMATION:
- Name: {user_data.get('church_name')}
- State: {user_data.get('state')}
- Financial Model: {user_data.get('financial_model', 'Not specified')}

REQUIREMENTS:
1. Create detailed guidelines covering:
   - What records to keep (financial, membership, meeting minutes, correspondence)
   - How long to retain each type of record
   - Best practices for organization
   - Digital vs. physical record-keeping
   - Backup and security procedures
   - Annual compliance checklist
   - State-specific requirements for {user_data.get('state')}

2. Emphasize importance of recordkeeping for 508(c)(1)(A) churches
3. Include practical tips for small churches
4. Include sample filing system organization
5. Include annual review procedures

CRITICAL NOTES:
- 508(c)(1)(A) churches don't file Form 990, but still need excellent records
- Records prove religious purpose and operations
- Records protect in case of any future questions or audits

CRITICAL DISCLAIMER:
Add this at the bottom:
"DISCLAIMER: This is educational information about recordkeeping best practices. State and federal requirements vary. Consult with a qualified attorney or CPA licensed in {user_data.get('state')} to ensure you're meeting all legal requirements for your specific situation."

Generate the complete Recordkeeping Guidelines now."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def generate_all_documents(self, user_data: Dict, requested_docs: List[str]) -> Dict[str, str]:
        """Generate all requested documents"""

        documents = {}
        timestamp = datetime.now().strftime("%Y-%m-%d")

        doc_generators = {
            'articles_of_faith': ('Articles_of_Faith', self.generate_articles_of_faith),
            'bylaws': ('Church_Bylaws', self.generate_bylaws),
            'irs_letter': ('IRS_Letter_1045', self.generate_irs_letter_1045),
            'operating_procedures': ('Operating_Procedures', self.generate_operating_procedures),
            'meeting_minutes': ('Meeting_Minutes_Template', self.generate_meeting_minutes_template),
            'recordkeeping': ('Recordkeeping_Guidelines', self.generate_recordkeeping_guidelines)
        }

        print(f"\n🤖 Generating documents for {user_data.get('church_name')}...")

        for doc_key in requested_docs:
            if doc_key in doc_generators:
                doc_name, generator_func = doc_generators[doc_key]
                print(f"  → Generating {doc_name}...")

                try:
                    content = generator_func(user_data)
                    filename = f"{user_data.get('church_name', 'Church')}_{doc_name}_{timestamp}.md"
                    # Clean filename
                    filename = filename.replace(' ', '_').replace('/', '_')
                    documents[filename] = content
                    print(f"  ✅ {doc_name} complete")
                except Exception as e:
                    print(f"  ❌ Error generating {doc_name}: {str(e)}")

        return documents

    def save_documents(self, documents: Dict[str, str], output_dir: str = "./generated_docs"):
        """Save generated documents to files"""

        os.makedirs(output_dir, exist_ok=True)

        for filename, content in documents.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  💾 Saved: {filename}")

        return output_dir

# Example usage / testing
if __name__ == "__main__":
    # Test data
    test_user_data = {
        'church_name': 'New Life Community Church',
        'state': 'TX',
        'email': 'test@example.com',
        'core_beliefs': 'We believe in the Bible as the inspired Word of God, salvation through faith in Jesus Christ, the importance of worship and prayer, and serving our community with love.',
        'mission_statement': 'To spread the gospel of Jesus Christ and serve our community through worship, education, and outreach.',
        'tradition': 'Christian - Non-denominational',
        'governance_model': 'Elder Board',
        'leadership_structure': 'Lead Pastor, Board of 3-5 Elders, Deacons for specific ministries',
        'membership_requirements': 'Profession of faith, baptism, completion of membership class',
        'activities': 'worship_services, bible_study, prayer_meetings, community_outreach',
        'meeting_frequency': 'weekly',
        'financial_model': 'tithes'
    }

    # Documents to generate
    requested_docs = [
        'articles_of_faith',
        'bylaws',
        'irs_letter',
        'operating_procedures',
        'meeting_minutes',
        'recordkeeping'
    ]

    # Generate
    generator = ChurchDocumentGenerator()
    documents = generator.generate_all_documents(test_user_data, requested_docs)

    # Save
    output_path = generator.save_documents(documents)

    print(f"\n✅ All documents generated and saved to: {output_path}")
    print(f"📄 Generated {len(documents)} documents")
