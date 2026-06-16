#!/usr/bin/env bash
# Idempotent Ollama setup for the T1 local model fallback.
set -euo pipefail

MODEL="${MODEL_ROUTER_OLLAMA_MODEL:-llama3.1:8b}"

if command -v ollama >/dev/null 2>&1; then
  echo "ollama already installed: $(command -v ollama)"
else
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y ollama || curl -fsSL https://ollama.ai/install.sh | sh
  else
    curl -fsSL https://ollama.ai/install.sh | sh
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl enable ollama || true
  systemctl start ollama || true
fi

if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
  ollama pull "$MODEL"
fi

echo "ollama ready with $MODEL"
