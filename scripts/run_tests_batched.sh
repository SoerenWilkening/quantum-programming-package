#!/usr/bin/env bash
# Run test files in separate processes to avoid OOM in memory-constrained
# containers (e.g. Docker with ~665 MB cgroup limit).
#
# Usage:
#   ./scripts/run_tests_batched.sh                  # run all
#   ./scripts/run_tests_batched.sh tests/python/test_call_graph.py  # run specific files
#
# Exits with non-zero status if any batch fails.

set -euo pipefail

TESTDIR="tests/python"
BATCH_SIZE="${BATCH_SIZE:-5}"  # number of test files per subprocess

# Build pytest args array — supports PYTEST_ARGS env var with proper quoting
if [[ -n "${PYTEST_ARGS:-}" ]]; then
    eval "PYTEST_ARGS_ARRAY=($PYTEST_ARGS)"
else
    PYTEST_ARGS_ARRAY=(--tb=short -q)
fi

if [ $# -gt 0 ]; then
    files=("$@")
else
    mapfile -t files < <(find "$TESTDIR" -name 'test_*.py' -type f | sort)
fi

total=${#files[@]}
passed=0
failed=0
failed_files=()

echo "Running $total test files in batches of $BATCH_SIZE"
echo "---"

for ((i = 0; i < total; i += BATCH_SIZE)); do
    batch=("${files[@]:i:BATCH_SIZE}")
    batch_desc=$(printf '%s ' "${batch[@]}" | sed 's|tests/python/||g')

    if python3 -m pytest "${PYTEST_ARGS_ARRAY[@]}" "${batch[@]}" 2>&1; then
        passed=$((passed + ${#batch[@]}))
    else
        exit_code=$?
        if [ $exit_code -eq 137 ]; then
            echo ""
            echo "FATAL: batch killed by OOM (exit 137). Retrying files individually..."
            for f in "${batch[@]}"; do
                if python3 -m pytest "${PYTEST_ARGS_ARRAY[@]}" "$f" 2>&1; then
                    passed=$((passed + 1))
                else
                    inner_exit=$?
                    if [ $inner_exit -eq 137 ]; then
                        echo "FATAL: $f alone causes OOM — skipping"
                    fi
                    failed=$((failed + 1))
                    failed_files+=("$f")
                fi
            done
        else
            failed=$((failed + ${#batch[@]}))
            failed_files+=("${batch[@]}")
        fi
    fi
    echo ""
done

echo "=== Summary ==="
echo "File batches passed: $passed / $total"
if [ $failed -gt 0 ]; then
    echo "Failed files:"
    printf '  %s\n' "${failed_files[@]}"
    exit 1
else
    echo "All passed."
fi
