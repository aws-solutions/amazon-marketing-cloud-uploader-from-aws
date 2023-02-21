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
    -rsl, --run_sonar-lint   Runs Sonar Lint. (export env vars required -> [SONAR_QUBE_PROJECT_KEY] [SONAR_QUBE_AUTH_TOKEN] ) .
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
    python3.10 -m venv "$VENV"
    source "$VENV"/bin/activate
    pip install pre-commit
    "$VENV"/bin/pre-commit install
    "$VENV"/bin/pre-commit run --all-files
fi

if [[ ( $@ == "--run_sonar-lint") ||  $@ == "-rsl" ]]
then
    if [ -z $SONAR_QUBE_PROJECT_KEY ]
    then
        echo "ERROR: SONAR_QUBE_PROJECT_KEY required. Goto https://docs.sonarqube.org/9.6/try-out-sonarqube/ to install a local instance of SonarQube"
        exit 1
    fi

    if [ -z $SONAR_QUBE_AUTH_TOKEN ]
    then
        echo "ERROR: SONAR_QUBE_AUTH_TOKEN required. Goto https://docs.sonarqube.org/9.6/try-out-sonarqube/ to install a local instance of SonarQube"
        exit 1
    fi

    # Run the scan in root of repository
    docker run --rm -v `pwd`:/usr/src --workdir /usr/src \
        --user=$(id -u):$(id -g) --network host \
        -e SONAR_HOST_URL="http://localhost:9000" \
        -e SONAR_SCANNER_OPTS="-Dsonar.projectKey=${SONAR_QUBE_PROJECT_KEY}" \
        -e SONAR_LOGIN="${SONAR_QUBE_AUTH_TOKEN}" \
        sonarsource/sonar-scanner-cli -Dproject.settings=sonar-project.properties
fi
