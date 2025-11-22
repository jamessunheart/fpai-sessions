const express = require('express');
const cors = require('cors');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const { OpenAI } = require('openai');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Configure multer for file uploads
const upload = multer({ 
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

// OpenAI client for command parsing
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Configuration
const WHISPER_SERVER_URL = process.env.WHISPER_SERVER_URL || 'http://localhost:5000';
const DROPLET_API_URL = process.env.DROPLET_API_URL || 'https://drop2.fullpotential.ai';

// Health check
app.get('/health', async (req, res) => {
  try {
    // Check Whisper server
    const whisperHealth = await axios.get(`${WHISPER_SERVER_URL}/health`);
    
    res.json({
      status: 'healthy',
      services: {
        voice_server: 'online',
        whisper_server: whisperHealth.data.status,
        openai: process.env.OPENAI_API_KEY ? 'configured' : 'missing'
      }
    });
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});

// Process voice command with droplet context
app.post('/voice-command', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    // Extract droplet context from form data
    const dropletContext = {
      id: req.body.id,
      cloudId: req.body.cloudId,
      name: req.body.name,
      provider: req.body.provider,
      powerStatus: req.body.powerStatus,
      ip: req.body.ip,
      region: req.body.region
    };

    const userContext = {
      userId: req.body.userId || 'anonymous',
      sessionId: req.body.sessionId || Date.now().toString()
    };

    console.log('🎤 Processing voice command for:', dropletContext.name);

    // Step 1: Transcribe audio with local Whisper
    const transcription = await transcribeAudio(req.file);
    console.log('📝 Transcription:', transcription.text);

    // Step 2: Parse command with GPT-4 (with droplet context)
    const command = await parseCommand(transcription.text, dropletContext);
    console.log('🎯 Parsed command:', command);

    // Step 3: Validate and execute command
    const result = await executeCommand(command, dropletContext);
    console.log('✅ Command result:', result);

    res.json({
      success: true,
      transcription: transcription.text,
      command: command,
      result: result,
      dropletContext: dropletContext,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Voice command error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Transcribe audio using local Whisper
async function transcribeAudio(audioFile) {
  try {
    const formData = new FormData();
    formData.append('audio', audioFile.buffer, {
      filename: 'audio.wav',
      contentType: audioFile.mimetype
    });

    const response = await axios.post(`${WHISPER_SERVER_URL}/transcribe`, formData, {
      headers: formData.getHeaders(),
      timeout: 30000 // 30 second timeout
    });

    return response.data;
  } catch (error) {
    throw new Error(`Whisper transcription failed: ${error.message}`);
  }
}

// Parse command using GPT-4 with droplet context
async function parseCommand(text, dropletContext) {
  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: `Parse droplet management commands with context. Return JSON with:
          {
            "action": "reboot|start|stop|status|delete|power_on|power_off",
            "dropletId": "string",
            "requiresConfirmation": boolean,
            "confidence": "high|medium|low"
          }
          
          Current droplet context:
          - Name: ${dropletContext.name}
          - Provider: ${dropletContext.provider}
          - Status: ${dropletContext.powerStatus}
          - Region: ${dropletContext.region}
          
          Valid actions: reboot, start, stop, status, delete, power_on, power_off
          Map "power on" to "power_on", "power off" to "power_off"
          Set requiresConfirmation=true for destructive actions (delete, stop, power_off)
          Use the current droplet's cloudId as dropletId`
        },
        {
          role: "user",
          content: text
        }
      ],
      temperature: 0.1
    });

    const commandText = response.choices[0].message.content;
    const parsed = JSON.parse(commandText);
    
    // Override dropletId with actual cloudId
    parsed.dropletId = dropletContext.cloudId;
    
    return parsed;
  } catch (error) {
    throw new Error(`Command parsing failed: ${error.message}`);
  }
}

// Execute command on droplet API with context
async function executeCommand(command, dropletContext) {
  try {
    const { action, requiresConfirmation } = command;
    const { provider, cloudId, name } = dropletContext;

    // Safety check for destructive actions
    if (requiresConfirmation && !command.confirmed) {
      return {
        status: 'confirmation_required',
        message: `This will ${action} ${name}. Say "confirm" to proceed.`,
        action: action,
        dropletId: cloudId
      };
    }

    // Build API endpoint based on provider and action
    let endpoint;
    let method = 'POST';
    
    switch (action) {
      case 'status':
        endpoint = `/multi-cloud?endpoint=/${provider}/list`;
        method = 'GET';
        break;
      case 'reboot':
        endpoint = `/multi-cloud?endpoint=/${provider}/action/${cloudId}?action=reboot`;
        break;
      case 'start':
      case 'power_on':
        endpoint = `/multi-cloud?endpoint=/${provider}/action/${cloudId}?action=power_on`;
        break;
      case 'stop':
      case 'power_off':
        endpoint = `/multi-cloud?endpoint=/${provider}/action/${cloudId}?action=power_off`;
        break;
      case 'delete':
        endpoint = `/multi-cloud?endpoint=/${provider}/delete/${cloudId}`;
        method = 'DELETE';
        break;
      default:
        throw new Error(`Unknown action: ${action}`);
    }

    // Make API call to dashboard's multi-cloud endpoint
    const response = await axios({
      method: method,
      url: `${DROPLET_API_URL}${endpoint}`,
      timeout: 15000
    });

    return {
      status: 'success',
      message: `Successfully executed ${action} on ${name}`,
      data: response.data
    };

  } catch (error) {
    return {
      status: 'error',
      message: `Failed to ${command.action} ${dropletContext.name}: ${error.message}`
    };
  }
}

// List available droplets
app.get('/droplets', async (req, res) => {
  try {
    const response = await axios.get(`${DROPLET_API_URL}/droplets`);
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start server
app.listen(PORT, () => {
  console.log('🚀 Voice Control Server started');
  console.log(`📡 Server: http://localhost:${PORT}`);
  console.log(`🎤 Whisper: ${WHISPER_SERVER_URL}`);
  console.log(`🔗 Droplet API: ${DROPLET_API_URL}`);
  console.log('📋 Health: http://localhost:' + PORT + '/health');
});