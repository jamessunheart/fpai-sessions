# Local Whisper Installation Guide

## Prerequisites
- Python 3.8 or higher
- Git
- 4GB+ RAM (8GB recommended)

## Step 1: Install Python Dependencies
```bash
# Install Whisper
pip install openai-whisper

# Install additional dependencies
pip install flask flask-cors python-multipart

# Install ffmpeg (required for audio processing)
# Windows: Download from https://ffmpeg.org/download.html
# Or use chocolatey: choco install ffmpeg
```

## Step 2: Test Whisper Installation
```bash
# Test with a sample audio file
whisper sample.wav --model base

# Available models:
# tiny    - Fastest, lower accuracy
# base    - Good balance (recommended)
# small   - Better accuracy
# medium  - High accuracy, slower
# large   - Best accuracy, slowest
```

## Step 3: Start Whisper Server
```bash
cd voice-control
python whisper-server.py
```

## Step 4: Test API
```bash
# Test the Whisper API endpoint
curl -X POST http://localhost:5000/transcribe \
  -F "audio=@test-audio.wav"
```

## Troubleshooting

### Error: "No module named 'whisper'"
```bash
pip install --upgrade openai-whisper
```

### Error: "ffmpeg not found"
- Download ffmpeg from https://ffmpeg.org/download.html
- Add to PATH environment variable
- Restart terminal

### Slow transcription
- Use smaller model: `--model tiny` or `--model base`
- Ensure you have enough RAM
- Consider using GPU if available

## Performance Tips
- Use `base` model for development (good speed/accuracy balance)
- Use `tiny` model for testing (fastest)
- Use `small` or `medium` for production (better accuracy)