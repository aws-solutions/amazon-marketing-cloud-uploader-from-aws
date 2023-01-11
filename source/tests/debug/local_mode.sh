#!/bin/bash
################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   This script is intended for dev testing/debuging this application in localhost mode, before deployment.
#
# USAGE: ./local_mode.sh [arguments]
#   Available options:
#   -h, --help      Print this help and exit.
#   -rw, --run_web    Builds and runs npm site in localhost.
#   -ra, --run_app    Runs REST API in chalice local test server.
################################################################################

PORT="5001"
DOMAIN="http://127.0.0.1"
set -Eeuo pipefail # see https://wizardzines.com/comics/bash-errors/

help(){
  cat <<EOF
    Usage: $0 [arguments]
    Available options:
    -h, --help      Print this help and exit.
    -rw, --run_web    Builds and runs npm site in localhost.
    -ra, --run_app    Runs REST API in chalice local test server.
EOF
	exit 0  
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help
fi

if [[ ( $@ == "--run_web") ||  $@ == "-rw" ]]
then
    cd ../../website
    command -v npm > /dev/null
    if [ $? -ne 0 ]; then
		echo "NPM is required to run this script."
		echo "goto https://docs.npmjs.com/downloading-and-installing-node-js-and-npm to install npm."
		exit 1
	fi
	
	npm install && npm run lint && npm run build && npm run serve;
elif [[ ( $@ == "--run_app") ||  $@ == "-ra" ]]
then
	# Create and activate a temporary Python environment for this script.
    echo "------------------------------------------------------------------------------"
    echo "Creating a temporary Python virtualenv for this script"
    echo "------------------------------------------------------------------------------"
    Python3.9 -c "import os; print (os.getenv('VIRTUAL_ENV'))" | grep -q None
    if [ $? -ne 0 ]; then
        echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
        exit 1;
    fi
    echo "Using virtual python environment:"
    VENV=$(mktemp -d) && echo "$VENV"
    command -v python3.9 > /dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR: install Python3.9 before running this script."
        exit 1
    fi
    Python3.9 -m venv "$VENV"
    source "$VENV"/bin/activate
    pip install --upgrade pip
	pip install -r requirements-debug.txt
    command -v jq > /dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR: install jq before running this script."
        echo "hint(mac users): brew install jq."
        exit 1
    fi
    echo $( echo $(cat ../../website/public/runtimeConfig.json | jq '.API_ENDPOINT |= "'"$DOMAIN:$PORT"'/"') | tr -d ' ' ) > ../../website/public/runtimeConfig.json
    cd ../../api
    export AWS_XRAY_CONTEXT_MISSING=LOG_ERROR # https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-python-configuration.html
	chalice local --port $PORT
else
    help
fi