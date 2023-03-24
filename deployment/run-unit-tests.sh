#!/bin/bash
###############################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   Verify that pytest scripts achieve a minimum threshold for code coverage.
#
# USAGE:
#  ./run-unit-tests.sh [-h] [-v]
#
#    The following options are available:
#
#     -h | --help       Print usage
#     -v | --verbose    Print script debug info
#
###############################################################################

trap cleanup_and_die SIGINT SIGTERM ERR

usage() {
  msg "$msg"
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v]

Available options:

-h, --help        Print this help and exit (optional)
-v, --verbose     Print script debug info (optional)
EOF
  exit 1
}

cleanup_and_die() {
  trap - SIGINT SIGTERM ERR
  echo "Trapped signal."
  cleanup
  die 1
}

cleanup() {
  # Deactivate and remove the temporary python virtualenv used to run this script
  if [[ "$VIRTUAL_ENV" != "" ]];
  then
    echo ''
    deactivate
    rm -rf $VENV
    rm -rf ./amc_uploader/amc_uploader.egg-info
    rm -rf $VENV
    rm -rf  __pycache__
    rm -rf .pytest_cache
    cd $template_dir
    echo "------------------------------------------------------------------------------"
    echo "Cleaning up complete"
    echo "------------------------------------------------------------------------------"
  fi
}

msg() {
  echo >&2 -e "${1-}"
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  msg "$msg"
  exit "$code"
}

parse_params() {
  # default values of variables set from params
  flag=0
  param=''
  use_solution_builder_pipeline=false

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -v | --verbose) set -x ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  args=("$@")

  return 0
}

parse_params "$@"

# Get reference for all important folders
template_dir="$PWD"
source_dir="$(cd $template_dir/../source; pwd -P)"
root_dir="$template_dir/.."

# Create and activate a temporary Python environment for this script.
echo "------------------------------------------------------------------------------"
echo "Creating a temporary Python virtualenv for this script"
echo "------------------------------------------------------------------------------"
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
command -v python3
if [ $? -ne 0 ]; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi
echo "Using virtual python environment:"
VENV=$(mktemp -d) && echo "$VENV"
command -v python3 > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi
python3 -m venv "$VENV"
source "$VENV"/bin/activate

# configure the environment
cd $source_dir
pip install --upgrade pip
pip install -q -r requirements-dev.txt
pip install -q -r tests/requirements-test.txt

# env variables
export PYTHONDONTWRITEBYTECODE=1
export AMC_ENDPOINT_URL="https://example.com/alpha"
export AMC_API_ROLE_ARN="arn:aws:iam::999999999999:role/SomeTestRole"
export SOLUTION_NAME="amcufa test"
export ARTIFACT_BUCKET="test_bucket"
export SYSTEM_TABLE_NAME="test_table"
export VERSION="0.0.0"
export botoConfig='{"region_name": "us-east-1"}'
export AWS_XRAY_SDK_ENABLED=false
export AMC_GLUE_JOB_NAME="some-GlueStack-123-amc-transformation-job"
export CUSTOMER_MANAGED_KEY=""
export AWS_REGION="us-east-1"
export SOLUTION_VERSION="0.0.0"

echo "------------------------------------------------------------------------------"
echo "[Test] Run pytest with coverage"
echo "------------------------------------------------------------------------------"
cd $source_dir
# setup coverage report path
coverage_report_path=$source_dir/tests/coverage-reports/source.coverage.xml
echo "coverage report path set to $coverage_report_path"
cd tests
# set PYTHONPATH to enable importing modules from ./glue/library,/anonymous_data_logger
export PYTHONPATH=$PYTHONPATH:../glue:../anonymous_data_logger:../api
pytest unit_test/. --cov=$source_dir/glue/ --cov=$source_dir/helper/ --cov=$source_dir/amc_uploader/ --cov=$source_dir/anonymous_data_logger/ --cov=$source_dir/api/ --cov=$source_dir/share/ --cov-report term-missing --cov-report term --cov-report "xml:$coverage_report_path" --cov-config=$source_dir/.coveragerc -vv
cd ..

# The pytest --cov with its parameters and .coveragerc generates a xml cov-report with `coverage/sources` list
# with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
# absolute paths for source directories, this substitution is used to convert each absolute source directory
# path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path

cleanup
echo "Done"
exit 0
