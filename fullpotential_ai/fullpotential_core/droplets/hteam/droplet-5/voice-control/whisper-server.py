#!/usr/bin/env python3
"""
Local Whisper API Server
Provides speech-to-text transcription using OpenAI Whisper
"""

import whisper
import tempfile
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load Whisper model (change model size as needed)
MODEL_SIZE = "base"  # Options: tiny, base, small, medium, large
logger.info(f"Loading Whisper model: {MODEL_SIZE}")
model = whisper.load_model(MODEL_SIZE)
logger.info("Whisper model loaded successfully")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": MODEL_SIZE,
        "whisper_version": whisper.__version__
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file to text"""
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        logger.info(f"Processing audio file: {audio_file.filename}")
        
        # Transcribe with Whisper
        result = model.transcribe(temp_path)
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Return transcription result
        response = {
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "confidence": "high",  # Whisper doesn't provide confidence scores
            "duration": result.get("duration", 0)
        }
        
        logger.info(f"Transcription: {response['text']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        # Clean up temp file if it exists
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available Whisper models"""
    models = ["tiny", "base", "small", "medium", "large"]
    return jsonify({
        "available_models": models,
        "current_model": MODEL_SIZE,
        "model_info": {
            "tiny": "Fastest, lower accuracy (~39 MB)",
            "base": "Good balance (~74 MB)",
            "small": "Better accuracy (~244 MB)",
            "medium": "High accuracy (~769 MB)",
            "large": "Best accuracy (~1550 MB)"
        }
    })

if __name__ == '__main__':
    print("🎤 Starting Whisper API Server...")
    print(f"📊 Model: {MODEL_SIZE}")
    print("🌐 Server: http://localhost:5000")
    print("📋 Health: http://localhost:5000/health")
    print("🎯 Transcribe: POST http://localhost:5000/transcribe")
    
    app.run(host='0.0.0.0', port=5000, debug=False)