#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# Usage: ./tests/run_test.sh [arguments]
#     Available options:
#     -h, --help      Print this help and exit.
#     -rut, --run_unit_test    Run Unit Test.

export PYTHONPATH=$PYTHONPATH:./glue

help(){
  cat <<EOF
    Usage: $0 [arguments]
    Available options:
    -h, --help      Print this help and exit.
    -rut, --run_unit_test    Run Unit Test.
EOF
	exit 0
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help
fi

if [[ ( $@ == "--run_unit_test") ||  $@ == "-rut" ]]
then

    VENV=$(mktemp -d) && echo "$VENV"
    python3.10 -m venv "$VENV"
    source "$VENV"/bin/activate

    export AMC_ENDPOINT_URL="https://example.com/alpha"
    export AMC_API_ROLE_ARN="arn:aws:iam::999999999999:role/SomeTestRole"
    export SOLUTION_NAME="amcufa test"
    export VERSION="0.0.0"
    export botoConfig='{"region_name": "us-east-1"}'
    export AWS_XRAY_SDK_ENABLED=false
    export AMC_GLUE_JOB_NAME="some-GlueStack-123-amc-transformation-job"
    export CUSTOMER_MANAGED_KEY=""
    export AWS_REGION="us-east-1"
    export SOLUTION_VERSION="0.0.0"

    pip install -r requirements-dev.txt
    pytest tests -vv --ignore="tests/e2e/"

fi
