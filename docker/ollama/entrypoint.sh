#!/bin/sh
set -e
ollama serve &
pid=$!
i=0
until ollama list >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 120 ]; then
    echo "Ollama did not become ready in time" >&2
    exit 1
  fi
  sleep 1
done
ollama pull qwen3.5:2b
wait "$pid"
