#!/bin/bash
#############################################################################
# PURPOSE: Build a Lambda layer for specified Python libraries.
#
# PREREQUISITES:
#   docker, aws cli
#
# USAGE:
#   Save the python libraries you want in the lambda layer in
#   requirements.txt, then run like this:
#
#   ./build-lambda-layer.sh <path to requirements.txt>
#
#############################################################################

# Check to see if input has been provided:
if [ -z "$1" ]; then
    echo "USAGE: ./build-lambda-layer.sh <requirements.txt>"
    exit 1
fi

REQUIREMENTS_FILE="$1"

# Check to see if requirements.txt file exists

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "$REQUIREMENTS_FILE does not exist"
    exit 1
fi

# Check to see if AWS CLI and Docker are installed
docker --version
if [ $? -ne 0 ]; then
  echo "ERROR: install Docker before running this script."
  exit 1
else
  docker ps > /dev/null
  if [ $? -ne 0 ]; then
      echo "ERROR: start Docker before running this script."
      exit 1
  fi
fi

echo "------------------------------------------------------------------------------"
echo "Building Lambda Layer zip file"
echo "------------------------------------------------------------------------------"

rm -rf ./lambda_layer_python-3.10/
rm -f ./lambda_layer_python3.10.zip
docker logout public.ecr.aws
docker build --tag=lambda_layer_factory:latest . 2>&1 > /dev/null
if [ $? -eq 0 ]; then
  docker run --rm -v "$PWD":/packages lambda_layer_factory
fi
if [[ ! -f ./lambda_layer_python3.10.zip ]]; then
    echo "ERROR: Failed to build lambda layer zip file."
    exit 1
fi
echo "------------------------------------------------------------------------------"
echo "Verifying the Lambda layer meets AWS size limits"
echo "------------------------------------------------------------------------------"
# See https://docs.aws.amazon.com/lambda/latest/dg/limits.html

unzip -q -d lambda_layer_python-3.10 ./lambda_layer_python3.10.zip
ZIPPED_LIMIT=50
UNZIPPED_LIMIT=250
UNZIPPED_SIZE_310=$(du -sm ./lambda_layer_python-3.10/ | cut -f 1)
ZIPPED_SIZE_310=$(du -sm ./lambda_layer_python3.10.zip | cut -f 1)

rm -rf ./lambda_layer-python-3.10/
if (($UNZIPPED_SIZE_310 > $UNZIPPED_LIMIT || $ZIPPED_SIZE_310 > $ZIPPED_LIMIT)); then
	echo "ERROR: Deployment package exceeds AWS Lambda layer size limits.";
	exit 1
fi
echo "Lambda layers have been saved to ./lambda_layer_python3.10.zip."

echo "------------------------------------------------------------------------------"
echo "Done"
echo "------------------------------------------------------------------------------"
