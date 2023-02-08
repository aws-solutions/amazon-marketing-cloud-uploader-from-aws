#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run Pre-commit
#
# ./run-pre-commit.sh
#

VENV=$(mktemp -d) && echo "$VENV"
python3.9 -m venv "$VENV"
source "$VENV"/bin/activate
pip install pre-commit
"$VENV"/bin/pre-commit install
"$VENV"/bin/pre-commit run --all-files