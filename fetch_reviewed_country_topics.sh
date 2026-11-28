#!/usr/bin/env bash
# Only successful same-day main runs from the designated read-only workflow.
# Optional enrichment must never wait for a running job or require new live sources.
set -euo pipefail
DAY="$1"
DEST="$2"
mkdir -p "$DEST"
CUTOFF="$(date -u -d "$DAY - 1 day" +%F)T15:00:00Z"
IDS=$(timeout 15s gh run list --workflow research-article-countries.yml --branch main --status success --limit 12 --json databaseId,createdAt | jq -r --arg cutoff "$CUTOFF" '[.[]|select(.createdAt >= $cutoff)]|sort_by(.databaseId)|reverse|.[0:3][]|.databaseId') || IDS=""
for ID in $IDS; do
  [[ "$ID" =~ ^[0-9]+$ ]] || continue
  mkdir -p "$DEST/$ID"
  timeout 12s gh run download "$ID" --name reviewed-country-topics --dir "$DEST/$ID" >/dev/null 2>&1 || true
  # Same trusted successful read-only main run, not a PR or arbitrary artifact.
  # Contains hash-bound evidence and exact JPEGs; importer reconstructs the record.
  timeout 12s gh run download "$ID" --name article-country-research --dir "$DEST/$ID/materials" >/dev/null 2>&1 || true
done
