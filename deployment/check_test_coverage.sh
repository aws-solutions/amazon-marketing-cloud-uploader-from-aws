#!/bin/bash

COVERAGE_RUNS=$( ./run-unit-tests.sh )
SUB="FAIL Required test coverage of"

echo -e $COVERAGE_RUNS

if [[ "$COVERAGE_RUNS" == *"$SUB"* ]]; then
    echo "Required test coverage not reached."
    exit 125
fi
