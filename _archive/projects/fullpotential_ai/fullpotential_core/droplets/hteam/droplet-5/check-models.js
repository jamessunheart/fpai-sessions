const https = require('https');

const apiKey = process.env.OPENAI_API_KEY;

if (!apiKey) {
  console.log('❌ OPENAI_API_KEY not set in environment');
  console.log('Set it in .env file or run: set OPENAI_API_KEY=your_key');
  process.exit(1);
}

const options = {
  hostname: 'api.openai.com',
  path: '/v1/models',
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiKey}`
  }
};

console.log('🔍 Fetching available OpenAI models...\n');

const req = https.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    try {
      const response = JSON.parse(data);
      
      if (response.error) {
        console.log('❌ Error:', response.error.message);
        return;
      }

      const models = response.data
        .map(m => m.id)
        .filter(id => id.includes('gpt') || id.includes('o1') || id.includes('o3'))
        .sort();

      console.log('✅ Available GPT/O-series models:\n');
      models.forEach(model => {
        if (model.includes('o3') || model.includes('o1')) {
          console.log(`  🌟 ${model} (Latest reasoning model)`);
        } else if (model.includes('gpt-4o')) {
          console.log(`  ⭐ ${model} (GPT-4 optimized)`);
        } else if (model.includes('gpt-4')) {
          console.log(`  📘 ${model}`);
        } else {
          console.log(`  📗 ${model}`);
        }
      });

      console.log('\n💡 Recommended for production:');
      const recommended = models.find(m => m.includes('o3-mini')) || 
                         models.find(m => m.includes('gpt-4o')) ||
                         models.find(m => m.includes('gpt-4-turbo'));
      console.log(`  ${recommended || 'gpt-4o'}`);
      
    } catch (error) {
      console.log('❌ Failed to parse response:', error.message);
    }
  });
});

req.on('error', (error) => {
  console.log('❌ Request failed:', error.message);
});

req.end();
