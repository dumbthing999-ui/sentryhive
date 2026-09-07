#!/usr/bin/env bash
# /home/kali/volthacks-project/run_claude.sh
# Multi-Tier Intelligent Fallback Engine for Claude Code
# Tier 1: antigravity/gemini-3.8-flash-tiered
# Tier 2: antigravity/claude-opus-4-6-thinking
# Tier 3: hcnsec/glm-5-3-flash (or hcnsec/auto)

set -uo pipefail
PROJECT_DIR="/home/kali/volthacks-project"
cd "$PROJECT_DIR"

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 \"task description\" [optional_forced_model]"
    exit 1
fi

TASK="$1"
FORCED_MODEL="${2:-}"

export ANTHROPIC_BASE_URL="http://127.0.0.1:20128/v1"
export ANTHROPIC_API_KEY="${OMNIROUTE_API_KEY:-}"

# Fallback ladder
MODELS=("antigravity/gemini-3.8-flash-tiered" "antigravity/claude-opus-4-6-thinking" "hcnsec/glm-5-3-flash" "hcnsec/auto" "antigravity/claude-sonnet-4-6")

if [ -n "$FORCED_MODEL" ]; then
    MODELS=("$FORCED_MODEL")
fi

TMP_OUTPUT=$(mktemp /tmp/claude_run_XXXXXX.log)
trap "rm -f $TMP_OUTPUT" EXIT

for MODEL in "${MODELS[@]}"; do
    echo "[run_claude] Attempting tier model: $MODEL" >&2
    export ANTHROPIC_MODEL="$MODEL"
    
    set +e
    claude -p "$TASK" --dangerously-skip-permissions 2>&1 | tee "$TMP_OUTPUT"
    EXIT_CODE="${PIPESTATUS[0]}"
    set -e
    
    if [ "$EXIT_CODE" -eq 0 ] && ! grep -qiE "exhausted their quota|rate limit|429|overloaded|bad gateway|502|503" "$TMP_OUTPUT"; then
        exit 0
    else
        echo "[run_claude] Model $MODEL failed (exit $EXIT_CODE or rate limited). Falling back to next tier..." >&2
    fi
done

echo "[run_claude] All fallback tiers failed." >&2
exit 1
