#!/usr/bin/env bash
# Start the stack with a validated env file.
#
# Usage:
#   ./scripts/docker-compose-up.sh                 # use .env in repo root, then: docker compose up --build
#   ./scripts/docker-compose-up.sh ./prod.env -d   # custom env file + extra args to "docker compose up"
#
# Env flow:
#   1. export COMPOSE_ENV_FILE -> absolute path; compose substitutes env_file: ${COMPOSE_ENV_FILE:-.env}
#   2. docker compose --env-file "$ENV_ABS" -> same file used for ${VAR} interpolation in this YAML
#   3. Keys in .env not listed under environment: still reach backend/telegram via env_file
#
# Equivalent manual command (after validation):
#   export COMPOSE_ENV_FILE="$(realpath .env)"
#   docker compose --env-file "$COMPOSE_ENV_FILE" config   # optional: validate + inspect
#   docker compose --env-file "$COMPOSE_ENV_FILE" up --build

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE=".env"
if [[ "${1:-}" == -* ]] || [[ -z "${1:-}" ]]; then
  COMPOSE_EXTRA_ARGS=("$@")
else
  if [[ ! -f "$1" ]]; then
    echo "error: env file not found: $1" >&2
    exit 1
  fi
  ENV_FILE="$1"
  shift
  COMPOSE_EXTRA_ARGS=("$@")
fi

if command -v realpath >/dev/null 2>&1; then
  ENV_ABS="$(realpath "$ENV_FILE")"
else
  ENV_ABS="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
fi
export COMPOSE_ENV_FILE="$ENV_ABS"

if [[ ! -f "$ENV_ABS" ]]; then
  echo "error: env file not found: $ENV_ABS" >&2
  exit 1
fi

# Read last assignment for KEY (ignores comments / blank lines; naive but matches typical .env).
get_env_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ENV_ABS" 2>/dev/null | tail -n1 | sed -E "s/^[[:space:]]*${key}[[:space:]]*=//")" || true
  raw="${raw%$'\r'}"
  while [[ "${raw}" =~ ^\"(.*)\"$ ]] || [[ "${raw}" =~ ^\'(.*)\'$ ]]; do
    raw="${BASH_REMATCH[1]}"
  done
  printf '%s' "$raw"
}

is_blank() {
  [[ -z "${1//[[:space:]]/}" ]]
}

is_placeholder_token() {
  local v="${1,,}"
  case "$v" in
    ""|"api_key"|"bot_token"|"model_name"|"name"|"boolean"|"chat_id") return 0 ;;
  esac
  return 1
}

ERRORS=0
fail() {
  echo "error: $*" >&2
  ERRORS=$((ERRORS + 1))
}

warn() {
  echo "warning: $*" >&2
}

val="$(get_env_value TELEGRAM_BOT_TOKEN)"
if is_blank "$val" || is_placeholder_token "$val"; then
  fail "TELEGRAM_BOT_TOKEN must be set to a real bot token (Telegram bot will not start otherwise)."
fi

val="$(get_env_value TAVILY_API_KEY)"
if is_blank "$val" || [[ "${val,,}" == "api_key" ]]; then
  fail "TAVILY_API_KEY must be set for web search / Tavily-backed tools."
fi

val="$(get_env_value CHAT_LLM)"
if is_blank "$val"; then
  warn "CHAT_LLM is empty; compose defaults to qwen3.5:2b (ensure that model is pulled in Ollama)."
fi

val="$(get_env_value DATABASE_URL)"
if is_blank "$val"; then
  warn "DATABASE_URL is empty; compose will use the default in docker-compose.yml (postgres service on the compose network)."
fi

val="$(get_env_value OLLAMA_BASE_URL)"
if is_blank "$val"; then
  warn "OLLAMA_BASE_URL is empty; compose will use http://ollama:11434 for the backend container."
fi

val="$(get_env_value BACKEND_URL)"
if is_blank "$val"; then
  warn "BACKEND_URL is empty; compose will use http://backend:8000 for the Telegram service."
fi

tracing="$(get_env_value LANGSMITH_TRACING_V2)"
if [[ "${tracing,,}" == "true" || "$tracing" == "1" ]]; then
  val="$(get_env_value LANGSMITH_API_KEY)"
  if is_blank "$val" || [[ "${val,,}" == "api_key" ]]; then
    fail "LANGSMITH_TRACING_V2 is enabled but LANGSMITH_API_KEY is missing or still a placeholder."
  fi
  val="$(get_env_value LANGSMITH_ENDPOINT)"
  if is_blank "$val"; then
    warn "LANGSMITH_ENDPOINT is empty; LangChain may use its default endpoint."
  fi
  val="$(get_env_value LANGSMITH_PROJECT)"
  if is_blank "$val" || [[ "${val,,}" == "name" ]]; then
    warn "LANGSMITH_PROJECT is empty or placeholder; tracing may be mis-attributed."
  fi
else
  val="$(get_env_value LANGSMITH_API_KEY)"
  if ! is_blank "$val"; then
    warn "LANGSMITH_API_KEY is set but LANGSMITH_TRACING_V2 is not true/1; tracing may stay disabled."
  fi
fi

val="$(get_env_value BRAVE_SEARCH_API_KEY)"
if is_blank "$val"; then
  warn "BRAVE_SEARCH_API_KEY is empty; Brave-backed search paths will not work."
fi

val="$(get_env_value OBSIDIAN_VAULT_PATH)"
if is_blank "$val"; then
  warn "OBSIDIAN_VAULT_PATH is empty; wiki / vault features may not find your vault inside the container unless you mount data."
fi

if [[ "$ERRORS" -gt 0 ]]; then
  echo "error: fix $ERRORS issue(s) in $ENV_ABS before starting." >&2
  exit 1
fi

echo "Using env file: $ENV_ABS"
echo "COMPOSE_ENV_FILE=$COMPOSE_ENV_FILE (used for env_file: path + compose interpolation)"

if ! docker compose --env-file "$ENV_ABS" config >/dev/null 2>&1; then
  echo "error: docker compose config failed (bad YAML, missing env_file path, or compose error)." >&2
  docker compose --env-file "$ENV_ABS" config 2>&1 | tail -n 30 >&2 || true
  exit 1
fi

echo "Running: docker compose --env-file \"$ENV_ABS\" up --build ${COMPOSE_EXTRA_ARGS[*]:-}"
exec docker compose --env-file "$ENV_ABS" up --build "${COMPOSE_EXTRA_ARGS[@]}"
