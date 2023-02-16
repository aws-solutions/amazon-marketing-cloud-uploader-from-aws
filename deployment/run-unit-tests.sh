#!/bin/bash
set +x
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh
#

[ "$DEBUG" == 'true' ] && set -x
# set -e

# Get reference for all important folders
template_dir="$PWD"
source_dir="$(cd $template_dir/../source; pwd -P)"
root_dir="$template_dir/.."

# Create and activate a temporary Python environment for this script.
echo "------------------------------------------------------------------------------"
echo "Creating a temporary Python virtualenv for this script"
echo "------------------------------------------------------------------------------"
python3 -c "import os; print (os.getenv('VIRTUAL_ENV'))" | grep -q None
if [ $? -ne 0 ]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
command -v python3
if [ $? -ne 0 ]; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi
echo "Using virtual python environment:"
venv_folder=$(mktemp -d) && echo "$venv_folder"
command -v python3 > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi
python3 -m venv $venv_folder
source $venv_folder/bin/activate

# configure the environment
cd $source_dir
pip install --upgrade pip
pip install -r requirements-dev.txt

# env variables
export PYTHONDONTWRITEBYTECODE=1
export AMC_ENDPOINT_URL="AmcEndpointUrl"
export AMC_API_ROLE_ARN="AmcApiRoleArn"
export SOLUTION_NAME="SOLUTION_NAME"
export SOLUTION_VERSION="SOLUTION_VERSION"
export botoConfig='{"region_name": "us-east-1"}'
export AWS_XRAY_SDK_ENABLED=false

# set PYTHONPATH to enable importing modules from ./glue/normalizers
export PYTHONPATH=$PYTHONPATH:./glue

echo "------------------------------------------------------------------------------"
echo "[Test] Run pytest with coverage"
echo "------------------------------------------------------------------------------"
cd $source_dir
# setup coverage report path
coverage_report_path=$source_dir/tests/coverage-reports/source.coverage.xml
echo "coverage report path set to $coverage_report_path"

pytest --cov --cov-report term-missing --cov-report term --cov-report "xml:$coverage_report_path" --cov-config=$source_dir/.coveragerc --ignore="tests/e2e"

# The pytest --cov with its parameters and .coveragerc generates a xml cov-report with `coverage/sources` list
# with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
# absolute paths for source directories, this substitution is used to convert each absolute source directory
# path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path

echo "------------------------------------------------------------------------------"
echo "[Env] Deactivating test virtual environment"
echo "------------------------------------------------------------------------------"
echo ''
# deactivate the virtual environment
deactivate
rm -rf ./amc_uploader/amc_uploader.egg-info
rm -rf $VENV
rm -rf  __pycache__
rm -rf .pytest_cache

cd $template_dir
