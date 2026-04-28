#!/bin/bash
set -eo pipefail

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export CI=true

cd /workspace/pint
pytest -v --tb=short --benchmark-skip -p no:cacheprovider \
    --ignore=pint/testsuite/benchmarks \
    --ignore=pint/testsuite/test_matplotlib.py \
    pint/testsuite/

