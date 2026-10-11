#!/usr/bin/env bash
#
# MyBatis 3 Localization & Publishing E2E Test Suite Runner
#
# Usage:
#   ./test_e2e_suite.sh                 # Run all 4 tiers
#   ./test_e2e_suite.sh --milestone M1  # Run M1 tests
#   ./test_e2e_suite.sh --milestone M2  # Run M2 tests
#   ./test_e2e_suite.sh --milestone M3  # Run M3 tests
#   ./test_e2e_suite.sh --tier 1        # Run Tier 1 tests
#   ./test_e2e_suite.sh --feature F01   # Run Feature F01 tests
#   ./test_e2e_suite.sh --json          # JSON report
#

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3 2>/dev/null || echo "python")"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Error: python3 is required to run the E2E test suite." >&2
    exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/test_e2e_suite.py" "$@"
