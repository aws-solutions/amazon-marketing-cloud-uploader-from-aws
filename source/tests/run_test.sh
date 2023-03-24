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
    -rut, --run_unit_test    Run Unit Test. [--test_file-name TEST_FILE_NAME] (optional)
    -rit, --run_integ_test    Run Integ Test. 
        [--stack-name STACK_NAME] 
        [--aws-region AWS_REGION] 
        [--aws-default-profile AWS_DEFAULT_PROFILE]
        [--aws-access-key-id AWS_ACCESS_KEY_ID] [--aws-secret-access-key AWS_SECRET_ACCESS_KEY] (Required if --aws-default-profile is not provided)
        [--data-bucket-name DATA_BUCKET_NAME]
        [--amc_endpoint_url AMC_ENDPOINT_URL] 
        [--test-data-upload-account-id TEST_DATA_UPLOAD_ACCOUNT_ID] 
        [--test-user-arn TEST_USER_ARN] (Optional, if not provided '/root' user will be used, with stack account id)
        [--aws-xray-sdk-enabled] (Optional, Default is False)
        [--boto-config] (Optional, Default is {})
        [--version] (Optional, Default is 0.0.0)
        [--solution_name] (Optional, Default is Amcufa Integration Test)
EOF
	exit 0
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  echo >&2 -e "${1-}"
#   exit "$code"
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help

elif [[ ( $@ == *"--run_unit_test"*) ||  $@ == *"-rut"* ]]
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

    while :; do
        case "${1-}" in
        -h | --help) help ;;
        -rut | --run_unit_test)
        echo "cmd --> ${1}"
        ;;
        --test-file-name)
        TEST_FILE_NAME="${2}"
        shift
        ;;
        -?*) die "Unknown option: $1" ;;
        *) break ;;
        esac
        shift
    done

    TEST_FILE_NAME="./unit_test/"$TEST_FILE_NAME
    echo "Running test -> "$TEST_FILE_NAME

    cd ..
    pip install -r requirements-dev.txt
    cd tests
    pip install -r requirements-test.txt
    pytest $TEST_FILE_NAME -vv --ignore="e2e/" --ignore="test_api_integration.py"

elif [[ ( $@ == *"--run_integ_test"*) ||  $@ == *"-rit"* ]]
then

    VENV=$(mktemp -d) && echo "$VENV"
    python3.10 -m venv "$VENV"
    source "$VENV"/bin/activate

    while :; do
        case "${1-}" in
        -h | --help) help ;;
        -rit | --run_integ_test)
        echo "cmd --> ${1}"
        ;;
        --stack-name)
        STACK_NAME="${2}"
        shift
        ;;
        --aws-region)
        AWS_REGION="${2}"
        shift
        ;;
        --aws-default-profile)
        AWS_DEFAULT_PROFILE="${2}"
        shift
        ;;
        --aws-access-key-id)
        AWS_ACCESS_KEY_ID="${2}"
        shift
        ;;
        --aws-secret-access-key)
        AWS_SECRET_ACCESS_KEY="${2}"
        shift
        ;;
        --data-bucket-name)
        DATA_BUCKET_NAME="${2}"
        shift
        ;;
        --amc-endpoint-url)
        AMC_ENDPOINT_URL="${2}"
        shift
        ;;
        --test_upload_account_id)
        TEST_DATA_UPLOAD_ACCOUNT_ID="${2}"
        shift
        ;;
        --test_user_arn)
        TEST_USER_ARN="${2}"
        shift
        ;;
        --aws-xray-sdk-enabled)
        AWS_XRAY_SDK_ENABLED="${2}"
        shift
        ;;
        --boto-config)
        botoConfig="${2}"
        shift
        ;;
        --version)
        VERSION="${2}"
        shift
        ;;
        --solution_name)
        SOLUTION_NAME="${2}"
        shift
        ;;
        -?*) die "Unknown option: $1" ;;
        *) break ;;
        esac
        shift
    done

    if [ -z $STACK_NAME ]
    then
        echo "ERROR: You must set the variable 'STACK_NAME' with params --stack-name."
        exit 1
    fi

    if [ -z $AWS_REGION ]
    then
        echo "ERROR: You must set the variable 'AWS_REGION' with params --aws-region."
        exit 1
    fi

    if [ -z $AWS_DEFAULT_PROFILE ]
    then
        if [[ -z $AWS_ACCESS_KEY_ID || -z $AWS_SECRET_ACCESS_KEY ]]
        then
            echo "ERROR:"
            echo "You must set the variable 'AWS_DEFAULT_PROFILE' with params --aws-default-profile."
            echo "OR"
            echo "You must set the variable 'AWS_ACCESS_KEY_ID' with params --aws-access-key-id and AWS_SECRET_ACCESS_KEY with params --aws-secret-access-key."
            exit 1
        fi
    fi

    if [ -z $DATA_BUCKET_NAME ]
    then
        echo "ERROR: You must set the variable 'DATA_BUCKET_NAME' with params --data-bucket-name."
        exit 1
    fi

    if [ -z $AMC_ENDPOINT_URL ]
    then
        echo "ERROR: You must set the variable 'AMC_ENDPOINT_URL' with params --amc-endpoint-url."
        exit 1
    fi

    if [ -z $TEST_DATA_UPLOAD_ACCOUNT_ID ]
    then
        echo "ERROR: You must set the variable 'TEST_DATA_UPLOAD_ACCOUNT_ID' with params --test_upload_account_id."
        exit 1
    fi

    export AMC_API_ENDPOINT=$AMC_ENDPOINT_URL
    export SOLUTION_NAME=${SOLUTION_NAME:-"Amcufa Integration Test"}
    export VERSION=${VERSION:-"0.0.0"}
    export botoConfig=${botoConfig:-"{}"}
    export AWS_XRAY_SDK_ENABLED=${AWS_XRAY_SDK_ENABLED:-false}
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
    TEST_USER_ARN=${TEST_USER_ARN:-"arn:aws:iam::$TEST_ACCOUNT_ID:root"}
    TEST_USER_ASSUME_ROLE_POLICY='{"Effect":"Allow","Principal":{"AWS":"'"$TEST_USER_ARN"'"},"Action":"sts:AssumeRole"}'
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
    pytest integration_test/test_api_integration.py -vv ;
    aws iam detach-role-policy --role-name $AMC_GLUE_JOB_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE
else
    help
fi