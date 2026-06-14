# 🌟 FPAI Empire - Multi-Service Docker Image
# Runs FPAI Hub + All Autonomous Agents

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY fpai-hub/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir anthropic aiohttp web3

# Copy all service code
COPY fpai-hub/ /app/fpai-hub/
COPY autonomous-agents/ /app/autonomous-agents/
COPY treasury/ /app/treasury/
COPY token/ /app/token/

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🌟 Starting FPAI Empire..."\n\
\n\
# Start FPAI Hub in background\n\
cd /app/fpai-hub\n\
python app.py &\n\
FPAI_HUB_PID=$!\n\
\n\
# Start agents in background\n\
cd /app/autonomous-agents\n\
python defi_yield_agent.py &\n\
python gas_optimizer_agent.py &\n\
python arbitrage_agent.py &\n\
python human_recruiter_agent.py &\n\
\n\
echo "✅ FPAI Empire running!"\n\
echo "   FPAI Hub: http://localhost:8010"\n\
echo "   Agents: 4 running"\n\
\n\
# Wait for FPAI Hub (main process)\n\
wait $FPAI_HUB_PID\n\
' > /app/start-empire.sh && chmod +x /app/start-empire.sh

# Expose FPAI Hub port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Run empire
CMD ["/app/start-empire.sh"]
