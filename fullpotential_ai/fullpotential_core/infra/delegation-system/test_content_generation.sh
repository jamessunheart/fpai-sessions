#!/bin/bash
# Test content generation - Priority 1

echo "🧪 TESTING CONTENT GENERATION (Priority 1)"
echo "=========================================="
echo ""

# Check API key
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    echo ""
    echo "Run: ./setup_api_key.sh for instructions"
    exit 1
fi

echo "✅ ANTHROPIC_API_KEY is set"
echo ""

# Check if we're on the server or need to SSH
if [ -f "/root/delegation-system/marketing_assembly_line.py" ]; then
    # Already on server
    cd /root/delegation-system
else
    # Need to SSH to server
    echo "📡 Connecting to server..."
    ssh root@198.54.123.234 "export ANTHROPIC_API_KEY='${ANTHROPIC_API_KEY}' && cd /root/delegation-system && python3 << 'EOPYTHON'
import os
from marketing_assembly_line import MarketingAssemblyLine

print('\n🏭 Initializing Marketing Assembly Line...\n')

# Initialize with API key from environment
assembly_line = MarketingAssemblyLine()

print('📝 Generating test content for Premium tier...\n')

# Generate ad copy for Facebook
fb_ad = assembly_line.content_gen.generate_ad_copy(
    objective='White Rock Ministry Premium Membership',
    platform='facebook',
    variation='A'
)

print('✅ Facebook Ad Generated:')
print(f\"   Headline: {fb_ad['headline']}\")
print(f\"   Body: {fb_ad['body'][:100]}...\")
print()

# Generate landing page copy
landing = assembly_line.content_gen.generate_landing_page_copy(
    tier='premium',
    variation='A'
)

print('✅ Landing Page Generated:')
print(f\"   Headline: {landing['headline']}\")
print(f\"   Subheadline: {landing['subheadline'][:80]}...\")
print()

print('🎉 SUCCESS! Content generation is working!')
print()
print('Next steps:')
print('1. Review generated content quality')
print('2. If quality is good → Proceed to Priority 2 ($100 manual MVP)')
print('3. If quality needs work → Adjust prompts and re-test')
print()

EOPYTHON
"
    exit 0
fi

# If we're already on the server, run directly
python3 << 'EOPYTHON'
import os
from marketing_assembly_line import MarketingAssemblyLine

print('\n🏭 Initializing Marketing Assembly Line...\n')

# Initialize with API key from environment
assembly_line = MarketingAssemblyLine()

print('📝 Generating test content for Premium tier...\n')

# Generate ad copy for Facebook
fb_ad = assembly_line.content_gen.generate_ad_copy(
    objective='White Rock Ministry Premium Membership',
    platform='facebook',
    variation='A'
)

print('✅ Facebook Ad Generated:')
print(f"   Headline: {fb_ad['headline']}")
print(f"   Body: {fb_ad['body'][:100]}...")
print()

# Generate landing page copy
landing = assembly_line.content_gen.generate_landing_page_copy(
    tier='premium',
    variation='A'
)

print('✅ Landing Page Generated:')
print(f"   Headline: {landing['headline']}")
print(f"   Subheadline: {landing['subheadline'][:80]}...")
print()

print('🎉 SUCCESS! Content generation is working!')
print()
print('Next steps:')
print('1. Review generated content quality')
print('2. If quality is good → Proceed to Priority 2 ($100 manual MVP)')
print('3. If quality needs work → Adjust prompts and re-test')
print()

EOPYTHON
