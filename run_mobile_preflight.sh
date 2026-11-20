#!/usr/bin/env bash
# Run the identical mobile interaction test BEFORE the new issue is committed.
# Public workflow runs still check the deployed Pages origin independently.
set -euo pipefail
test -f _site/index.html
python check_release_candidate.py --site _site

npm install --no-save --no-audit --no-fund playwright@1.56.1
google-chrome --version
mkdir -p "$HOME/.local/share/fonts"
curl --fail --location --retry 2 --connect-timeout 10 --max-time 90 --silent --show-error \
 "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf" \
 --output "$HOME/.local/share/fonts/NotoSansCJKjp-Regular.otf"
fc-cache -f "$HOME/.local/share/fonts"
fc-list :lang=ja | grep 'Noto Sans CJK JP' > /dev/null
python -m http.server 8765 --bind 127.0.0.1 --directory _site > /tmp/yoru9-preflight-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 15); do
 if curl --fail --silent --output /dev/null "http://127.0.0.1:8765/index.html"; then break; fi
 if [ "$attempt" -eq 15 ]; then
  cat /tmp/yoru9-preflight-server.log
  exit 1
 fi
 sleep 1
done
READER_SITE_URL=http://127.0.0.1:8765/ node tests/mobile_visual_smoke.mjs
