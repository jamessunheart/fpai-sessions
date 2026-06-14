const axios = require('axios');

const VOICE_SERVER_URL = 'http://localhost:3001';
const WHISPER_SERVER_URL = 'http://localhost:5000';

async function testHealthCheck() {
  console.log('🏥 Testing health checks...');
  
  try {
    // Test voice server
    const voiceHealth = await axios.get(`${VOICE_SERVER_URL}/health`);
    console.log('✅ Voice Server:', voiceHealth.data);
    
    // Test Whisper server
    const whisperHealth = await axios.get(`${WHISPER_SERVER_URL}/health`);
    console.log('✅ Whisper Server:', whisperHealth.data);
    
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
  }
}

async function testDropletList() {
  console.log('\n📋 Testing droplet list...');
  
  try {
    const response = await axios.get(`${VOICE_SERVER_URL}/droplets`);
    console.log('✅ Droplets:', response.data);
  } catch (error) {
    console.error('❌ Droplet list failed:', error.message);
  }
}

async function runTests() {
  console.log('🧪 Starting Voice Control System Tests\n');
  
  await testHealthCheck();
  await testDropletList();
  
  console.log('\n✨ Tests completed!');
  console.log('\n📝 Next steps:');
  console.log('1. Start Whisper server: python whisper-server.py');
  console.log('2. Start voice server: npm start');
  console.log('3. Test with voice commands in your dashboard');
}

runTests();