#!/usr/bin/env bash
# Layani folder saat ini di background. Pakai: serve.sh [port=8080]. Hentikan: kill $(cat /tmp/codinx-serve.pid)
port="${1:-8080}"
nohup python3 -m http.server "$port" --bind 127.0.0.1 >/tmp/codinx-serve.log 2>&1 &
echo $! > /tmp/codinx-serve.pid
sleep 1
echo "melayani http://127.0.0.1:$port (PID $(cat /tmp/codinx-serve.pid), log /tmp/codinx-serve.log)"
