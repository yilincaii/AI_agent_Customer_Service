#!/usr/bin/env bash
set -euo pipefail
curl -N -H "Content-Type: application/json" -d '{"session_id":"demo","message":"到手不喜欢能退吗？"}' http://localhost:8000/api/chat
