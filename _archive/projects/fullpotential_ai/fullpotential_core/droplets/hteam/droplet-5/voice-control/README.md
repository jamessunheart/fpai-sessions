# Voice Control System for Droplet Management

## Overview
Real-time voice control system for managing cloud droplets using local Whisper and OpenAI GPT-4.

## Architecture
```
Dashboard Chat → Voice Server → Local Whisper → GPT-4 → Droplet APIs
```

## Quick Start

### 1. Install Local Whisper
```bash
# Install Python 3.8+ first
pip install openai-whisper
pip install flask flask-cors

# Test Whisper
whisper --help
```

### 2. Start Voice Server
```bash
cd voice-control
npm install
npm start
```

### 3. Start Whisper Service
```bash
cd voice-control
python whisper-server.py
```

### 4. Add Voice Button to Chat
Import and use the VoiceRecorder component in your chat interface.

## Project Structure
```
voice-control/
├── README.md                 # This file
├── WHISPER_SETUP.md         # Whisper installation guide
├── package.json             # Node.js dependencies
├── server.js                # Main voice server
├── whisper-server.py        # Local Whisper API
├── components/
│   └── VoiceRecorder.jsx    # Voice recording component
└── test/
    └── test-voice.js        # Test voice commands
```

## Environment Variables
```
OPENAI_API_KEY=your_openai_key
DROPLET_API_URL=https://drop2.fullpotential.ai
WHISPER_SERVER_URL=http://localhost:5000
```

## API Endpoints
- `POST /voice-command` - Process voice command
- `GET /health` - Health check
- `GET /droplets` - List droplets