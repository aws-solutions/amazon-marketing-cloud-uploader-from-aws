#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# Usage: ./tests/run_test.sh [arguments]
#     Available options:
#     -h, --help      Print this help and exit.
#     -rut, --run_unit_test    Run Unit Test.
#     -rit, --run_integ_test    Run Integ Test.

export PYTHONPATH=$PYTHONPATH:../glue:../anonymous_data_logger:../api

help(){
  cat <<EOF
    Usage: $0 [arguments]
    Available options:
    -h, --help      Print this help and exit.
    -rut, --run_unit_test    Run Unit Test.
    -rit, --run_integ_test    Run Integ Test.
EOF
	exit 0
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help

elif [[ ( $@ == "--run_unit_test") ||  $@ == "-rut" ]]
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
    export SYSTEM_TABLE_NAME="test_table"
    export ARTIFACT_BUCKET="test-etl-artifact"

    cd ..
    pip install -r requirements-dev.txt
    cd tests
    pip install -r requirements-test.txt
    pytest . -vv --ignore="e2e/" --ignore="test_api_integration.py"

elif [[ ( $@ == "--run_integ_test") ||  $@ == "-rit" ]]
then

    VENV=$(mktemp -d) && echo "$VENV"
    python3.10 -m venv "$VENV"
    source "$VENV"/bin/activate

    # Fill all values here
    STACK_NAME=""
    AWS_REGION="us-east-1"
    AWS_DEFAULT_PROFILE=""
    DATA_BUCKET_NAME=""
    CUSTOMER_MANAGED_KEY=""
    AMC_ENDPOINT_URL=""
    AWS_XRAY_SDK_ENABLED=false
    AWS_XRAY_CONTEXT_MISSING=LOG_ERROR
    TEST_DATA_UPLOAD_ACCOUNT_ID=""
    # End

    if [ -z $STACK_NAME ]
    then
    echo "ERROR: You must set the variable 'STACK_NAME'"
    exit 1
    fi

    if [ -z $AWS_REGION ]
    then
    echo "ERROR: You must set the variable 'AWS_REGION'"
    exit 1
    fi

    if [ -z $AWS_DEFAULT_PROFILE ]
    then
    echo "ERROR: You must set the variable 'AWS_DEFAULT_PROFILE'"
    exit 1
    fi

    if [ -z $DATA_BUCKET_NAME ]
    then
    echo "ERROR: You must set the variable 'DATA_BUCKET_NAME'"
    exit 1
    fi

    if [ -z $AMC_ENDPOINT_URL ]
    then
    echo "ERROR: You must set the variable 'AMC_ENDPOINT_URL'"
    exit 1
    fi

    if [ -z $TEST_DATA_UPLOAD_ACCOUNT_ID ]
    then
    echo "ERROR: You must set the variable 'TEST_DATA_UPLOAD_ACCOUNT_ID'"
    exit 1
    fi

    export AMC_API_ENDPOINT=$AMC_ENDPOINT_URL
    export SOLUTION_NAME="Amc integ testing"
    export VERSION="0.0.1"
    export botoConfig="{}"
    export AWS_XRAY_CONTEXT_MISSING=$AWS_XRAY_CONTEXT_MISSING
    export AWS_XRAY_SDK_ENABLED=$AWS_XRAY_SDK_ENABLED
    export DATA_BUCKET_NAME=$DATA_BUCKET_NAME
    export CUSTOMER_MANAGED_KEY=$CUSTOMER_MANAGED_KEY
    export AWS_REGION=$AWS_REGION
    export AWS_DEFAULT_PROFILE=$AWS_DEFAULT_PROFILE
    export TEST_DATA_UPLOAD_ACCOUNT_ID=$TEST_DATA_UPLOAD_ACCOUNT_ID

    RESOURCE_ID=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id GlueStack --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    echo $RESOURCE_ID
    NESTED_STACK_ID=$(echo $RESOURCE_ID | cut -d "/" -f 2)
    echo $NESTED_STACK_ID

    AMC_GLUE_JOB_NAME=$(aws cloudformation describe-stack-resources --stack-name $NESTED_STACK_ID --logical-resource-id "AmcGlueJob" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    AMC_GLUE_JOB_NAME=$(echo "$AMC_GLUE_JOB_NAME" | tr -d '"')
    export AMC_GLUE_JOB_NAME=$AMC_GLUE_JOB_NAME
    AMC_GLUE_JOB_ROLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $NESTED_STACK_ID --logical-resource-id "AmcGlueJobRole" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    AMC_GLUE_JOB_ROLE_NAME=$(echo $AMC_GLUE_JOB_ROLE_NAME | tr -d '"')
    echo "AMC_GLUE_JOB_ROLE_NAME: $AMC_GLUE_JOB_ROLE_NAME"
    aws iam attach-role-policy --role-name $AMC_GLUE_JOB_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE
    ROLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "AmcApiAccessRole" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    ROLE_NAME=$(echo $ROLE_NAME | tr -d '"')
    echo "ROLE_NAME: $ROLE_NAME"
    CURRENT_ASSUME_ROLE_POLICY1=$(aws iam get-role --role-name $ROLE_NAME --query "Role.AssumeRolePolicyDocument.Statement[0]" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    CURRENT_ASSUME_ROLE_POLICY2=$(aws iam get-role --role-name $ROLE_NAME --query "Role.AssumeRolePolicyDocument.Statement[1]" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    TEST_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    TEST_ACCOUNT_ID=$(echo $TEST_ACCOUNT_ID | tr -d '"')
    export TEST_ACCOUNT_ID
    TEST_USER_ARN="arn:aws:iam::$TEST_ACCOUNT_ID"
    TEST_USER_ASSUME_ROLE_POLICY='{"Effect":"Allow","Principal":{"AWS":"'"$TEST_USER_ARN"':root"},"Action":"sts:AssumeRole"}'
    echo "TEST_USER_ASSUME_ROLE_POLICY: $TEST_USER_ASSUME_ROLE_POLICY"
    TEST_IAM_USER_POLICY='{"Version":"2012-10-17","Statement":['$CURRENT_ASSUME_ROLE_POLICY1', '$CURRENT_ASSUME_ROLE_POLICY2', '$TEST_USER_ASSUME_ROLE_POLICY']}'
    aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document "$TEST_IAM_USER_POLICY" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE
    export AMC_API_ROLE_ARN="arn:aws:iam::$TEST_ACCOUNT_ID:role/$ROLE_NAME"
    ARTIFACT_BUCKET=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "ArtifactBucket" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    ARTIFACT_BUCKET=$(echo $ARTIFACT_BUCKET | tr -d '"')
    echo "ARTIFACT_BUCKET: $ARTIFACT_BUCKET"
    export ARTIFACT_BUCKET=$ARTIFACT_BUCKET
    SYSTEM_TABLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "SystemTable" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
    SYSTEM_TABLE_NAME=$(echo $SYSTEM_TABLE_NAME | tr -d '"')
    export SYSTEM_TABLE_NAME=$SYSTEM_TABLE_NAME

    pip install -q -r requirements-test.txt
    pytest test_api_integration.py -vv ;
    aws iam detach-role-policy --role-name $AMC_GLUE_JOB_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE
else
    help
fi
