#!/bin/bash
# Installs the typesafe Claude Code plugin in cloud sessions.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if ! claude plugin marketplace list 2>/dev/null | grep -q "typesafe-ai"; then
  claude plugin marketplace add typesafe-ai/skills
fi

if ! claude plugin list 2>/dev/null | grep -q "typesafe@typesafe-ai"; then
  claude plugin install typesafe@typesafe-ai
fi
