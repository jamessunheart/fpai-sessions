# Full Potential OS v.521-M

A Flask-based API service for persistent memory storage using Mem0.ai. This service provides endpoints for storing chat messages, reflections, and intents in a centralized memory system.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Features

- **Memory Storage**: Store chat messages, reflections, and intents in Mem0
- **User Management**: Support for user-specific memory storage
- **RESTful API**: Clean REST endpoints for all operations
- **Error Handling**: Comprehensive error handling and validation
- **Environment-based Configuration**: Secure configuration via environment variables

## Prerequisites

- Python 3.12+ (Python 3.10+ should work)
- pip (Python package manager)
- Mem0 API key ([Get one here](https://app.mem0.ai/dashboard/api-keys))
- (Optional) Virtual environment (recommended)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd full-potential-os-v521
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Required: Mem0 API Key
MEM0_API_KEY=your-mem0-api-key-here

# Optional: Mem0 Organization and Project IDs
MEM0_ORG_ID=your-org-id  # Optional
MEM0_PROJECT_ID=your-project-id  # Optional

# Server Configuration
PORT=7860  # Default: 7860
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `MEM0_API_KEY` | Yes | Your Mem0 API key | - |
| `MEM0_ORG_ID` | No | Mem0 organization ID | - |
| `MEM0_PROJECT_ID` | No | Mem0 project ID | - |
| `PORT` | No | Server port | 7860 |

### Configuration File

The application also reads from `config/settings.yaml`:

```yaml
app_name: "Full Potential OS v.521-M"
port: 7860
```

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python app/server.py
```

The server will start on `http://0.0.0.0:7860` (accessible from all interfaces).

### Production Mode

For production, use a WSGI server like Gunicorn:

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:7860 app.server:create_app()
```

Or with environment variables:

```bash
gunicorn -w 4 -b 0.0.0.0:${PORT:-7860} --env MEM0_API_KEY=$MEM0_API_KEY app.server:create_app()
```

## 📡 API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "v.521-M"
}
```

### Store Chat Message

```http
POST /chat
Content-Type: application/json
```

**Request Body:**
```json
{
  "role": "user",
  "content": "Hello, this is a test message",
  "user_id": "optional_user_id"
}
```

**Response:**
```json
{
  "stored": true,
  "echo": "Hello, this is a test message"
}
```

**Parameters:**
- `role` (required): Message role (`"user"` or `"assistant"`)
- `content` (required): Message content
- `user_id` (optional): User identifier (defaults to `"default_user"`)

### Store Reflection

```http
POST /reflect
Content-Type: application/json
```

**Request Body:**
```json
{
  "summary": "Reflection summary",
  "insights": ["Insight 1", "Insight 2"],
  "decisions": ["Decision A", "Decision B"],
  "user_id": "optional_user_id"
}
```

**Response:**
```json
{
  "stored": true
}
```

### Store Intent

```http
POST /intent
Content-Type: application/json
```

**Request Body:**
```json
{
  "intent": "Complete project documentation",
  "horizon_min": 60,
  "tags": ["work", "documentation"],
  "user_id": "optional_user_id"
}
```

**Response:**
```json
{
  "stored": true
}
```

**Parameters:**
- `intent` (required): Intent description
- `horizon_min` (optional): Time horizon in minutes (default: 60)
- `tags` (optional): List of tags
- `user_id` (optional): User identifier

## Testing

### Test API Key

```bash
python test_api_key.py
```

### Test All Endpoints

```bash
# Make sure server is running first
python test_endpoints.py
```

### Manual Testing with curl

```bash
# Health check
curl http://localhost:7860/health

# Chat endpoint
curl -X POST http://localhost:7860/chat \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Test message"}'

# With bash script
./test_endpoints.sh
```

## 🚢 Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7860", "app.server:create_app()"]
```

Build and run:

```bash
docker build -t full-potential-os .
docker run -p 7860:7860 --env-file .env full-potential-os
```

### Systemd Service (Linux)

Create `/etc/systemd/system/full-potential-os.service`:

```ini
[Unit]
Description=Full Potential OS API Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/full-potential-os
Environment="PATH=/opt/full-potential-os/venv/bin"
ExecStart=/opt/full-potential-os/venv/bin/gunicorn -w 4 -b 0.0.0.0:7860 app.server:create_app()
Restart=always
EnvironmentFile=/opt/full-potential-os/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable full-potential-os
sudo systemctl start full-potential-os
sudo systemctl status full-potential-os
```

### Environment Setup on Server

1. **Clone repository:**
   ```bash
   cd /opt
   git clone <repository-url> full-potential-os
   cd full-potential-os
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   # Create .env file
   nano .env
   # Add MEM0_API_KEY and other variables
   ```

4. **Set permissions:**
   ```bash
   chmod +x app/server.py
   ```

5. **Test locally:**
   ```bash
   python app/server.py
   ```

6. **Deploy with Gunicorn:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:7860 app.server:create_app()
   ```

### Nginx Reverse Proxy (Optional)

Add to `/etc/nginx/sites-available/full-potential-os`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/full-potential-os /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔍 Troubleshooting

### Common Issues

#### 1. API Key Error (401)
```
Error: HTTP 401: Invalid API key
```

**Solution:**
- Verify `MEM0_API_KEY` is set correctly in `.env`
- Check for extra spaces or quotes in the API key
- Verify the API key is valid at https://app.mem0.ai/dashboard/api-keys

#### 2. Connection Refused
```
Error: Connection refused
```

**Solution:**
- Ensure the server is running
- Check the port is correct (default: 7860)
- Verify firewall settings

#### 3. Module Not Found
```
ModuleNotFoundError: No module named 'dotenv'
```

**Solution:**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

#### 4. Port Already in Use
```
Error: Address already in use
```

**Solution:**
- Change port in `.env`: `PORT=7861`
- Or kill the process using the port: `lsof -ti:7860 | xargs kill`

### Logs

Check application logs:

```bash
# If using systemd
sudo journalctl -u full-potential-os -f

# If using Gunicorn directly
# Logs will appear in terminal or configured log file
```

### Health Check

Test if the service is running:

```bash
curl http://localhost:7860/health
```

Expected response:
```json
{"status": "ok", "version": "v.521-M"}
```

## 📝 Development

### Project Structure

```
full-potential-os-v521/
├── app/
│   ├── __init__.py
│   ├── server.py          # Flask application
│   └── memory_mem0.py     # Mem0 API adapter
├── config/
│   └── settings.yaml      # Application settings
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── test_api_key.py        # API key validation test
├── test_endpoints.py      # Endpoint tests
├── test_endpoints.sh      # Bash test script
└── README.md              # This file
```

### Dependencies

- `flask==3.0.3` - Web framework
- `pyyaml==6.0.2` - YAML configuration
- `requests==2.32.3` - HTTP client
- `python-dotenv==1.0.0` - Environment variable management

## Security Notes

- **Never commit `.env` file** - It contains sensitive API keys
- Use environment variables in production
- Consider using a secrets management service (AWS Secrets Manager, HashiCorp Vault, etc.)
- Enable HTTPS in production (use Nginx with SSL/TLS)
- Implement rate limiting for production use
- Add authentication/authorization if exposing to public networks

## Support

For issues or questions:
- Check the [Mem0 API Documentation](https://docs.mem0.ai/api-reference/memory/add-memories)
- Review error messages in logs
- Test API key: `python test_api_key.py`

## License

[Add your license information here]

## Version

Current version: **v.521-M**

