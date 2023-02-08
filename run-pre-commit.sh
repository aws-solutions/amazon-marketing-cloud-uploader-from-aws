#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run Pre-commit
#
# Usage: ./run-pre-commit.sh [arguments]
# Available options:
# -h, --help      Print this help and exit.
# -rnl, --run_npm_lint    Run npm lint.
# -rpc, --run_pre-commit    Runs Pre commit.

help(){
  cat <<EOF
    Usage: $0 [arguments]
    Available options:
    -h, --help      Print this help and exit.
    -rnl, --run_npm_lint    Run npm lint.
    -rpc, --run_pre-commit    Runs Pre commit.
EOF
	exit 0
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help
fi

if [[ ( $@ == "--run_npm_lint") ||  $@ == "-rnl" ]]
then
    cd source/website
    npm install
    npm run lint
    npm run build
fi


if [[ ( $@ == "--run_pre-commit") ||  $@ == "-rpc" ]]
then
    VENV=$(mktemp -d) && echo "$VENV"
    python3.9 -m venv "$VENV"
    source "$VENV"/bin/activate
    pip install pre-commit
    "$VENV"/bin/pre-commit install
    "$VENV"/bin/pre-commit run --all-files
fi
