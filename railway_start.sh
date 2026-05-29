#!/usr/bin/env sh
set -eu
PORT="${PORT:-8080}"
echo "Starting EGO-AI Streamlit on port ${PORT}..."
exec python -m streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.fileWatcherType=none
