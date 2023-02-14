#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

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

    export AMC_ENDPOINT_URL="https://test_end_point_url.com/test"
    export AMC_API_ROLE_ARN="arn:aws:iam::999999999999:role/SomeTestRole"
    export SOLUTION_NAME="SOLUTION_NAME"
    export SOLUTION_VERSION="SOLUTION_VERSION"
    export botoConfig='{"region_name": "us-east-1"}'
    export AWS_XRAY_SDK_ENABLED=false
    export AMC_GLUE_JOB_NAME="some-GlueStack-123-amc-transformation-job"

    pip install -r requirements-dev.txt
    pytest tests -vv --ignore="tests/e2e/"

fi
