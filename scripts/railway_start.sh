#!/usr/bin/env sh
set -eu
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 2 --timeout 180 flask_api:app
