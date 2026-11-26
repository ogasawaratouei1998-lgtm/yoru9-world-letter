#!/usr/bin/env bash
# Run the model inside this existing GitHub Actions job. Never use a remote AI API.
set -euo pipefail
WORK="$(mktemp -d "${RUNNER_TEMP:-/tmp}/yoru9-local.XXXXXX")"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT
# Pin and verify the release artifact and model bytes before executing.
curl --fail --location --retry 2 --max-time 180 \
  https://github.com/ggml-org/llama.cpp/releases/download/b10786/llama-b10786-bin-ubuntu-x64.tar.gz \
  -o "$WORK/llama.tar.gz"
echo "79c0a6d479cc306bcac6aa891c3d97e0c32d817e898e32a5947bfe0dd22439ef  $WORK/llama.tar.gz" | sha256sum -c -
tar -xzf "$WORK/llama.tar.gz" -C "$WORK"
SERVER="$(find "$WORK" -type f -name llama-server -print -quit)"
test -n "$SERVER"
export LD_LIBRARY_PATH="$(dirname "$SERVER"):${LD_LIBRARY_PATH:-}"
curl --fail --location --retry 2 --max-time 420 \
  https://huggingface.co/lmstudio-community/Qwen3-4B-Instruct-2507-GGUF/resolve/fe59b38c2d9a56304c3fde5cc7320a6a057e8ba5/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
  -o "$WORK/model.gguf"
echo "8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc  $WORK/model.gguf" | sha256sum -c -
# Bind to loopback only. Raw model output and source prompts stay out of logs.
"$SERVER" --model "$WORK/model.gguf" --alias yoru9-local-qwen \
  --host 127.0.0.1 --port 18089 --ctx-size 16384 --parallel 1 \
  --threads 4 --threads-batch 4 --n-gpu-layers 0 >"$WORK/server.log" 2>&1 &
SERVER_PID=$!
READY=false
for attempt in $(seq 1 60); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then echo "::error::Local inference server exited"; exit 1; fi
  if curl --noproxy '*' --silent --fail --max-time 2 http://127.0.0.1:18089/health >/dev/null; then READY=true; break; fi
  sleep 2
done
if [ "$READY" != true ]; then echo "::error::Local inference server failed readiness check"; exit 1; fi
if [ "${1:-}" = "--probe-only" ]; then
  # Explicit non-publishing test; never consume the daily editorial time budget.
  timeout 240 python local_editorial.py --probe
else
  python local_editorial.py
  YORU9_EDITORIAL_BACKEND=local GEMINI_API_KEY= python auto_editorial.py
fi
