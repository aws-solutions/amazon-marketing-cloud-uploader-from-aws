#!/bin/bash
###############################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   Run selenium tests.
#
# PRELIMINARY:
#  Deploy the solution before running this script and set the following environment variables:
#  - AWS_ACCESS_KEY_ID - To authorize AWS CLI commands
#  - AWS_SECRET_ACCESS_KEY - To authorize AWS CLI commands
#  - EMAIL - To log into the webui
#  - PASSWORD - To log into the webui
#  - DATA_BUCKET_NAME - From which to upload data files for testing
#
# USAGE:
#  ./run_e2e.sh [-h] [-v] --stack-name {STACK_NAME} --region {REGION} [--profile {PROFILE}]
#    STACK_NAME name of the Cloudformation stack where the solution is running.
#    REGION needs to be in a format like us-east-1
#    PROFILE is optional. It's the profile that you have setup in ~/.aws/credentials
#      that you want to use for AWS CLI commands.
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
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--profile PROFILE] --stack-name STACK_NAME --region REGION

Available options:

-h, --help        Print this help and exit (optional)
-v, --verbose     Print script debug info (optional)
--stack-name      Name of the Cloudformation stack where the solution is running.
--region          AWS Region, formatted like us-west-2
--profile         AWS profile for CLI commands (optional)
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
    deactivate
    rm -rf $VENV
    rm -rf __pycache__
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

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -v | --verbose) set -x ;;
    --stack-name)
      stack_name="${2}"
      shift
      ;;
    --region)
      region="${2}"
      shift
      ;;
    --profile)
      profile="${2}"
      shift
      ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  args=("$@")

  # check required params and arguments
  [[ -z "${stack_name}" ]] && usage "Missing required parameter: stack-name"
  [[ -z "${region}" ]] && usage "Missing required parameter: region"

  return 0
}

parse_params "$@"
msg "Parameters:"
msg "- Stack name: ${stack_name}"
msg "- Region: ${region}"
[[ ! -z "${profile}" ]] && msg "- Profile: ${profile}"

echo ""
sleep 3

# Make sure aws cli is installed
if [[ ! -x "$(command -v aws)" ]]; then
  echo "ERROR: This script requires the AWS CLI to be installed. Please install it then run again."
  exit 1
fi

# Make sure aws cli is authorized
if [ -z $AWS_ACCESS_KEY_ID ]
then
  echo "ERROR: You must set the env variable 'AWS_ACCESS_KEY_ID' with a valid IAM access key id."
  exit 1
fi

if [ -z $AWS_SECRET_ACCESS_KEY ]
then
  echo "ERROR: You must set the env variable 'AWS_SECRET_ACCESS_KEY' with a valid IAM secret access key."
  exit 1
fi

# Make sure aws cli is authorized
if [ -z $EMAIL ]
then
  echo "ERROR: You must set the env variable 'EMAIL' to log into the webui."
  exit 1
fi

if [ -z $PASSWORD ]
then
  echo "ERROR: You must set the env variable 'PASSWORD' to log into the webui."
  exit 1
fi

if [ -z $DATA_BUCKET_NAME ]
then
  echo "ERROR: You must set the env variable 'DATA_BUCKET_NAME' from which to upload test data files."
  exit 1
fi

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
VENV=$(mktemp -d) && echo "$VENV"
command -v python3 > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: install Python3 before running this script"
  exit 1
fi
python3 -m venv "$VENV"
source "$VENV"/bin/activate
pip3 install wheel
pip3 install --quiet -r requirements.txt

echo "------------------------------------------------------------------------------"
echo "Running pytest"
echo "------------------------------------------------------------------------------"

export REGION=$region 
export STACK_NAME=$stack_name
export EMAIL=$EMAIL
export PASSWORD=$PASSWORD 
export DATA_BUCKET_NAME=$DATA_BUCKET_NAME
export LOCALHOST_URL=$LOCALHOST_URL
pytest -s -W ignore::DeprecationWarning -p no:cacheproviders

if [ $? -ne 0 ]; then
  die 1
fi

cleanup
echo "Done"
exit 0
