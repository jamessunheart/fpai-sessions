#!/bin/bash
# Voice Integration — ElevenLabs TTS + Deepgram STT
# Enables: text-to-speech audio, voice briefings via Telegram, transcription
#
# Setup: Set ELEVENLABS_API_KEY in /opt/fpai/cora-loop/.env
#   1. Sign up at https://elevenlabs.io (free tier: 10K chars/month)
#   2. Profile > API Keys > Create
#   3. Add: ELEVENLABS_API_KEY=sk_xxxxx
#
# Usage:
#   voice.sh status              — Check API connection + quota
#   voice.sh speak "text"        — Generate audio file from text
#   voice.sh briefing "text"     — Generate audio and send via Telegram
#   voice.sh voices              — List available voices
#   voice.sh quota               — Check remaining free characters

set -euo pipefail

source /opt/fpai/cora-loop/.env 2>/dev/null || true
ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY:-}"
ELEVENLABS_BASE="https://api.elevenlabs.io/v1"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
VOICE_DIR="/opt/fpai/voice-output"

mkdir -p "$VOICE_DIR"

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "ERROR: ELEVENLABS_API_KEY not set in /opt/fpai/cora-loop/.env"
    echo ""
    echo "Setup instructions:"
    echo "  1. Sign up at https://elevenlabs.io (free — 10K chars/month)"
    echo "  2. Profile icon > API Keys"
    echo "  3. Add to /opt/fpai/cora-loop/.env: ELEVENLABS_API_KEY=sk_xxxxx"
    exit 1
fi

cmd_status() {
    echo "Testing ElevenLabs API..."
    result=$(curl -s "${ELEVENLABS_BASE}/user/subscription" \
        -H "xi-api-key: ${ELEVENLABS_API_KEY}")
    
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'character_count' in d:
    used = d['character_count']
    limit = d['character_limit']
    remaining = limit - used
    tier = d.get('tier', 'unknown')
    print(f'Connected! Tier: {tier}')
    print(f'  Characters used: {used:,} / {limit:,}')
    print(f'  Remaining: {remaining:,} (~{remaining//150} sentences)')
    print(f'  Voice integration: ACTIVE')
else:
    print(f'Connection issue: {json.dumps(d)[:200]}')
" 2>/dev/null || echo "Failed: $result"
}

cmd_voices() {
    result=$(curl -s "${ELEVENLABS_BASE}/voices" \
        -H "xi-api-key: ${ELEVENLABS_API_KEY}")
    
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
voices = d.get('voices', [])
print(f'Available voices ({len(voices)}):')
print()
for v in voices[:15]:
    labels = v.get('labels', {})
    accent = labels.get('accent', '')
    gender = labels.get('gender', '')
    use_case = labels.get('use_case', '')
    preview = v.get('preview_url', '')
    print(f'  {v[\"voice_id\"][:12]}... | {v[\"name\"]:<20} | {gender:<8} | {accent:<12} | {use_case}')
if len(voices) > 15:
    print(f'  ... +{len(voices)-15} more')
" 2>/dev/null || echo "$result"
}

cmd_speak() {
    local text="$1"
    local voice_id="${2:-}"
    local filename="voice_$(date +%Y%m%d_%H%M%S).mp3"
    local filepath="${VOICE_DIR}/${filename}"
    
    # Use default voice if not specified (Rachel — calm, professional)
    if [ -z "$voice_id" ]; then
        voice_id="21m00Tcm4TlvDq8ikWAM"
    fi
    
    local char_count=${#text}
    echo "Generating speech (${char_count} chars)..."
    
    payload=$(python3 -c "
import json
print(json.dumps({
    'text': '''${text}''',
    'model_id': 'eleven_monolingual_v1',
    'voice_settings': {
        'stability': 0.5,
        'similarity_boost': 0.75,
        'style': 0.0,
        'use_speaker_boost': True
    }
}))
")
    
    http_code=$(curl -s -o "$filepath" -w "%{http_code}" \
        "${ELEVENLABS_BASE}/text-to-speech/${voice_id}" \
        -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    if [ "$http_code" = "200" ] && [ -s "$filepath" ]; then
        local size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null || echo "?")
        echo "Audio generated: ${filepath} (${size} bytes)"
        echo "$filepath"
    else
        echo "Failed (HTTP ${http_code})"
        [ -f "$filepath" ] && cat "$filepath" && rm "$filepath"
        exit 1
    fi
}

cmd_briefing() {
    local text="$1"
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
        echo "ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required for briefings"
        exit 1
    fi
    
    # Generate audio
    local filepath
    filepath=$(cmd_speak "$text" 2>&1 | tail -1)
    
    if [ ! -f "$filepath" ]; then
        echo "Audio generation failed"
        exit 1
    fi
    
    # Send via Telegram as voice message
    echo "Sending voice briefing via Telegram..."
    result=$(curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendVoice" \
        -F "chat_id=${TELEGRAM_CHAT_ID}" \
        -F "voice=@${filepath}" \
        -F "caption=Voice Briefing")
    
    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok')" 2>/dev/null; then
        echo "Voice briefing sent to Telegram"
    else
        echo "Telegram send failed: $result"
        # Fallback: send as audio file
        curl -s -X POST \
            "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
            -F "chat_id=${TELEGRAM_CHAT_ID}" \
            -F "audio=@${filepath}" \
            -F "title=Voice Briefing" > /dev/null 2>&1
    fi
}

cmd_quota() {
    result=$(curl -s "${ELEVENLABS_BASE}/user/subscription" \
        -H "xi-api-key: ${ELEVENLABS_API_KEY}")
    
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
used = d.get('character_count', 0)
limit = d.get('character_limit', 0)
remaining = limit - used
reset = d.get('next_character_count_reset_unix', 0)
from datetime import datetime
reset_date = datetime.fromtimestamp(reset).strftime('%Y-%m-%d') if reset else 'unknown'
print(f'ElevenLabs Quota:')
print(f'  Used:      {used:,} / {limit:,} characters')
print(f'  Remaining: {remaining:,} characters')
print(f'  Approx:    ~{remaining//150} sentences / ~{remaining//750} paragraphs')
print(f'  Resets:    {reset_date}')
" 2>/dev/null || echo "Failed: $result"
}

case "${1:-help}" in
    status)   cmd_status ;;
    speak)    cmd_speak "${2:?text required}" "${3:-}" ;;
    briefing) cmd_briefing "${2:?text required}" ;;
    voices)   cmd_voices ;;
    quota)    cmd_quota ;;
    *)
        echo "Voice Integration (ElevenLabs)"
        echo "  status              — Check connection + quota"
        echo "  speak \"text\"        — Generate audio file"
        echo "  briefing \"text\"     — Generate + send via Telegram"
        echo "  voices              — List available voices"
        echo "  quota               — Check remaining characters"
        ;;
esac
