#!/bin/bash


# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# Usage: ./tests/run_test.sh [arguments]
#     Available options:
#     -h, --help      Print this help and exit.
#     -rut, --run_unit_test    Run Unit Test.
#     -rit, --run_integ_test    Run Integ Test.


export PYTHONPATH=$PYTHONPATH:../glue:../anonymous_data_logger:../api:../cognito_hosted_ui_resource:../helper

help(){
  cat <<EOF
    Usage: $0 [arguments]
    Available options:
    -h, --help      Print this help and exit.
    --in-venv       Run test in an existing virtual environment [--in-venv 1] (optional)
    --extras        Append more commands to pytest run (optional)
    -rut, --run_unit_test    Run Unit Test.
        [--test_file-name TEST_FILE_NAME] (optional) (e.g `test_api.py` or `test_api.py::test_get_etl_jobs` for a single test.)
        [--aws-region AWS_REGION] (optional, Default is us-east-1.)
    -rit, --run_integ_test    Run Integ Test.
        [--stack-name STACK_NAME] (An existing deployed stack with code changes/version to run integration test on.)
        [--aws-region AWS_REGION]
        [--aws-default-profile AWS_DEFAULT_PROFILE] (AWS default profiles with creds) (Required if --aws-access-key-id and --aws-secret-access-key is not provided)
        [--aws-access-key-id AWS_ACCESS_KEY_ID] [--aws-secret-access-key AWS_SECRET_ACCESS_KEY] (Required if --aws-default-profile is not provided)
        [--data-bucket-name DATA_BUCKET_NAME] (Optional if --test-params-secret-name is provided )
        [--amc-instance-id AMC_INSTANCE_ID] (Optional if --test-params-secret-name is provided )
        [--amc-advertiser-id AMC_ADVERTISER_ID] (Optional if --test-params-secret-name is provided )
        [--amc-marketplace-id AMC_MARKETPLACE_ID] (Optional if --test-params-secret-name is provided )
        [--auth-code AUTH_CODE] (Amazon API auth code) (Optional if --refresh-token is provided) (Optional, but not eligible with --test-params-secret-name as refresh token is required )
        [--client-id CLIENT_ID] (Optional if --test-params-secret-name is provided )
        [--client-secret CLIENT_SECRET] (Optional if --test-params-secret-name is provided )
        [--refresh-token REFRESH_TOKEN] (Amazon API Refresh token) (Required, if --auth-code is not provided.) (Optional if --test-params-secret-name is provided )
        [--test-data-upload-account-id TEST_DATA_UPLOAD_ACCOUNT_ID] (Optional if --test-params-secret-name is provided )
        [--test-user-arn TEST_USER_ARN] (Optional, if not provided '/root' user will be used, with stack account id) (It also assumes user has admin priviledges.)
        [--aws-xray-sdk-enabled] (Optional, Default is false)
        [--boto-config] (Optional, Default is '{"region_name": "AWS_REGION"}')
        [--version] (Optional, Default is 0.0.0)
        [--solution-name] (Optional, Default is Amcufa Integration Test)
        [--test-params-secret-name] (Optional, Run integ test with variables stored in stack account aws secret manager.)
            ## secret-id amcufa_integ_test_secret
            ## secret-value sample, all variables are required.
                {
                    "instance_id": "abcd",
                    "advertiser_id": "ABCD12345",
                    "marketplace_id": "ABCD",
                    "data_upload_account_id": "1234567889",
                    "client_id": "amzn1.XXXXXXXXXX",
                    "client_secret": "amzn1.XXXXXXX",
                    "refresh_token": "Atzr|XXXXXXXXX",
                    "data_bucket_name": "s3-source-bucket",
                    "amc_endpoint_url": "https://some-api-endpoint.us-east-1.amazonawa.com/beta",
                }
        [--test-params-secret-name-region] (Optional, Default to us-east-1.)
        [--deep-test] (Optional, Default to false.) (100% test coverage, but set to false for tests optimization to prevent timeouts.)
EOF
	exit 0
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  echo >&2 -e "${1-}"
  exit "$code"
}

activate_venv() {
    if [[ ${IN_VENV:-0} -ne 1 ]]; then
        echo "------------------------------------------------------------------------------"
        echo "[Env] Create clean virtual environment and install dependencies"
        echo "------------------------------------------------------------------------------"
        VENV=$(mktemp -d) && echo "$VENV"
        python3 -m venv "$VENV"
        source "$VENV"/bin/activate
    else
        echo "------------------------------------------------------------------------------"
        echo "[Env] Using active virtual environment for tests"
        echo "------------------------------------------------------------------------------"
        echo ''
    fi
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
    help

elif [[ ( $@ == *"--run_unit_test"*) ||  $@ == *"-rut"* ]]
then

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
        --in-venv)
        IN_VENV="${2}"
        shift
        ;;
        --extras)
        EXTRAS="${2}"
        shift
        ;;
        --aws-region)
        AWS_REGION="${2}"
        shift
        ;;
        -?*) die "Unknown option: $1" ;;
        *) break ;;
        esac
        shift
    done

    activate_venv

    AWS_REGION=${AWS_REGION:-"us-east-1"}

    export AMC_INSTANCE_ID="123456fdsf"
    export AMC_ADVERTISER_ID="123456fdsf"
    export AMC_MARKETPLACE_ID="123456fdsf"
    export AMC_API_ROLE_ARN="arn:aws:iam::999999999999:role/SomeTestRole"
    export SOLUTION_NAME="amcufa test"
    export VERSION="0.0.0"
    export botoConfig='{"region_name": "'$AWS_REGION'"}'
    export AWS_XRAY_SDK_ENABLED=false
    export AMC_GLUE_JOB_NAME="some-GlueStack-123-amc-transformation-job"
    export CUSTOMER_MANAGED_KEY="test_customer_managed_key"
    export AWS_REGION=$AWS_REGION
    export SOLUTION_VERSION="0.0.0"
    export SYSTEM_TABLE_NAME="test_table"
    export ARTIFACT_BUCKET="test-etl-artifact"
    export UPLOAD_FAILURES_TABLE_NAME="upload_failures_test_table"
    export CLIENT_ID="123456sdgdg"
    export CLIENT_SECRET="fdvaed4535gd"
    export STACK_NAME="amcufa-stack-name"

    TEST_FILE_NAME="./unit_test/"$TEST_FILE_NAME
    echo "Running test -> "$TEST_FILE_NAME

    set -exuo pipefail

    if [[ ${IN_VENV:-0} -ne 1 ]]; then
        cd ..
        pip install -q -r requirements-dev.txt
        cd tests
        pip install -q -r requirements-test.txt
    else
        cd ../tests
    fi
    pytest $TEST_FILE_NAME ${EXTRAS-} -vv

elif [[ ( $@ == *"--run_integ_test"*) ||  $@ == *"-rit"* ]]
then

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
        --amc-instance-id)
        AMC_INSTANCE_ID="${2}"
        shift
        ;;
        --amc-advertiser-id)
        AMC_ADVERTISER_ID="${2}"
        shift
        ;;
        --amc-marketplace-id)
        AMC_MARKETPLACE_ID="${2}"
        shift
        ;;
        --test-data-upload-account-id)
        TEST_DATA_UPLOAD_ACCOUNT_ID="${2}"
        shift
        ;;
        --test-user-arn)
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
        --solution-name)
        SOLUTION_NAME="${2}"
        shift
        ;;
        --client-id)
        CLIENT_ID="${2}"
        shift
        ;;
        --client-secret)
        CLIENT_SECRET="${2}"
        shift
        ;;
        --refresh-token)
        REFRESH_TOKEN="${2}"
        shift
        ;;
        --auth-code)
        AUTH_CODE="${2}"
        shift
        ;;
        --in-venv)
        IN_VENV="${2}"
        shift
        ;;
        --test-params-secret-name)
        TEST_PARAMS_SECRET_NAME="${2}"
        shift
        ;;
        --test-params-secret-name-region)
        TEST_PARAMS_SECRET_NAME_REGION="${2}"
        shift
        ;;
        --extras)
        EXTRAS="${2}"
        shift
        ;;
        --deep-test)
        DEEP_TEST="${2}"
        shift
        ;;
        -?*) die "Unknown option: $1" ;;
        *) break ;;
        esac
        shift
    done

    activate_venv

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

    if [[ -z $DATA_BUCKET_NAME && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'DATA_BUCKET_NAME' with params --data-bucket-name."
        exit 1
    fi

    if [[ -z $AMC_INSTANCE_ID  && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'AMC_INSTANCE_ID' with params --amc-instance-id."
        exit 1
    fi

    if [[ -z $AMC_ADVERTISER_ID && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'AMC_ADVERTISER_ID' with params --amc-advertiser-id."
        exit 1
    fi

    if [[ -z $AMC_MARKETPLACE_ID && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'AMC_MARKETPLACE_ID' with params --amc-marketplace-id."
        exit 1
    fi

    if [[ -z $TEST_DATA_UPLOAD_ACCOUNT_ID && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'TEST_DATA_UPLOAD_ACCOUNT_ID' with params --test-data-upload-account-id."
        exit 1
    fi
    if [[ -z $CLIENT_ID && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'CLIENT_ID' with params --client-id."
        exit 1
    fi
    if [[ -z $CLIENT_SECRET && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        echo "ERROR: You must set the variable 'CLIENT_SECRET' with params --client-secret."
        exit 1
    fi
    if [[ -z $REFRESH_TOKEN && -z $TEST_PARAMS_SECRET_NAME ]]
    then
        if [ -z $AUTH_CODE ]
        then
            echo "ERROR: You must set the variable 'REFRESH_TOKEN' with params --refresh-token. or 'AUTH_CODE' with params --auth-code"
            USER_INTERFACE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[0].OutputValue" --region $AWS_REGION --profile $AWS_DEFAULT_PROFILE)
            USER_INTERFACE=$(echo $USER_INTERFACE | tr -d '"')
            echo "UI_URL --> $USER_INTERFACE"
            REDIRECT_URI="$USER_INTERFACE/redirect"
            echo "Add $REDIRECT_URI to Allowed Return URLs."
            read -p "Did you add $REDIRECT_URI to Allowed Return URLs? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
            read -p "Did you login to $USER_INTERFACE stack? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
            AUTH_URL="https://www.amazon.com/ap/oa?client_id=$CLIENT_ID&scope=profile%20advertising::campaign_management&response_type=code&redirect_uri=$REDIRECT_URI"
            echo "Running AUTH_URL -> $AUTH_URL"
            if which xdg-open > /dev/null
            then
                xdg-open $AUTH_URL
            elif which gnome-open > /dev/null
            then
                gnome-open $AUTH_URL
            else
                browser_exist=$(which $(open -a "Google Chrome"))
                b_info="Unable to find application named 'Google Chrome'"
                if [ "$browser_exist" = "$b_info" ]
                then
                    echo "Unable to find a browser."
                    echo "AUTH_URL: $AUTH_URL"
                    echo "Run AUTH_URL on ur browser, then;"
                    echo "provide '?code=' value parameters in url."
                else
                    open -a "Google Chrome" $AUTH_URL
                fi
            fi

            read -p "Provide AUTH_CODE from '?code=' parameters in url: " INPUT_AUTH_TOKEN
            if [ -z "$INPUT_AUTH_TOKEN" ]
            then
                exit 1
            else
                AUTH_CODE=$INPUT_AUTH_TOKEN
                echo "PROVIDED AUTH CODE: $AUTH_CODE"
            fi
        fi
    fi

    export TEST_PARAMS_SECRET_NAME=$TEST_PARAMS_SECRET_NAME
    export TEST_PARAMS_SECRET_NAME_REGION=$TEST_PARAMS_SECRET_NAME_REGION
    export AMC_INSTANCE_ID=$AMC_INSTANCE_ID
    export AMC_ADVERTISER_ID=$AMC_ADVERTISER_ID
    export AMC_MARKETPLACE_ID=$AMC_MARKETPLACE_ID
    export SOLUTION_NAME=${SOLUTION_NAME:-"Amcufa Integration Test"}
    export VERSION=${VERSION:-"0.0.0"}
    export botoConfig=${botoConfig:-'{"region_name": "'$AWS_REGION'"}'}
    export AWS_XRAY_SDK_ENABLED=${AWS_XRAY_SDK_ENABLED:-false}
    export DATA_BUCKET_NAME=$DATA_BUCKET_NAME
    export CUSTOMER_MANAGED_KEY=$CUSTOMER_MANAGED_KEY
    export AWS_REGION=$AWS_REGION
    export TEST_DATA_UPLOAD_ACCOUNT_ID=$TEST_DATA_UPLOAD_ACCOUNT_ID
    export CLIENT_ID=$CLIENT_ID
    export CLIENT_SECRET=$CLIENT_SECRET
    export REFRESH_TOKEN=$REFRESH_TOKEN
    export AUTH_CODE=$AUTH_CODE
    export STACK_NAME=$STACK_NAME
    export USER_INTERFACE=$USER_INTERFACE
    export DEEP_TEST=$DEEP_TEST

    if [ ! -z $AWS_DEFAULT_PROFILE ]
    then
        export AWS_DEFAULT_PROFILE=$AWS_DEFAULT_PROFILE
    elif [[ ! -z $AWS_ACCESS_KEY_ID && ! -z $AWS_SECRET_ACCESS_KEY ]]
    then
        export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
        export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
    fi

    set -exuo pipefail

    GLUE_RESOURCE_ID=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id GlueStack6 --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    echo $GLUE_RESOURCE_ID
    GLUE_NESTED_STACK_ID=$(echo $GLUE_RESOURCE_ID | cut -d "/" -f 2)
    echo $GLUE_NESTED_STACK_ID

    AMC_GLUE_JOB_NAME=$(aws cloudformation describe-stack-resources --stack-name $GLUE_NESTED_STACK_ID --logical-resource-id "AmcGlueJob" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    AMC_GLUE_JOB_NAME=$(echo "$AMC_GLUE_JOB_NAME" | tr -d '"')
    echo "AMC_GLUE_JOB_NAME: $AMC_GLUE_JOB_NAME"
    export AMC_GLUE_JOB_NAME=$AMC_GLUE_JOB_NAME

    AMC_GLUE_JOB_ROLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $GLUE_NESTED_STACK_ID --logical-resource-id "AmcGlueJobRole" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    AMC_GLUE_JOB_ROLE_NAME=$(echo $AMC_GLUE_JOB_ROLE_NAME | tr -d '"')
    echo "AMC_GLUE_JOB_ROLE_NAME: $AMC_GLUE_JOB_ROLE_NAME"

    aws iam attach-role-policy --role-name $AMC_GLUE_JOB_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi)
    ROLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "AmcApiAccessRole" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    ROLE_NAME=$(echo $ROLE_NAME | tr -d '"')
    echo "ROLE_NAME: $ROLE_NAME"
    CURRENT_ASSUME_ROLE_POLICY1=$(aws iam get-role --role-name $ROLE_NAME --query "Role.AssumeRolePolicyDocument.Statement[0]" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    CURRENT_ASSUME_ROLE_POLICY2=$(aws iam get-role --role-name $ROLE_NAME --query "Role.AssumeRolePolicyDocument.Statement[1]" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))

    TEST_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    TEST_ACCOUNT_ID=$(echo $TEST_ACCOUNT_ID | tr -d '"')
    export TEST_ACCOUNT_ID

    TEST_USER_ARN=${TEST_USER_ARN:-"arn:aws:iam::$TEST_ACCOUNT_ID:root"}
    echo $TEST_USER_ARN
    TEST_USER_ASSUME_ROLE_POLICY='{"Effect":"Allow","Principal":{"AWS":"'"$TEST_USER_ARN"'"},"Action":"sts:AssumeRole"}'
    echo "TEST_USER_ASSUME_ROLE_POLICY: $TEST_USER_ASSUME_ROLE_POLICY"
    TEST_IAM_USER_POLICY='{"Version":"2012-10-17","Statement":['$CURRENT_ASSUME_ROLE_POLICY1', '$CURRENT_ASSUME_ROLE_POLICY2', '$TEST_USER_ASSUME_ROLE_POLICY']}'
    aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document "$TEST_IAM_USER_POLICY" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi)
    export AMC_API_ROLE_ARN="arn:aws:iam::$TEST_ACCOUNT_ID:role/$ROLE_NAME"

    ARTIFACT_BUCKET=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "ArtifactBucket" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    ARTIFACT_BUCKET=$(echo $ARTIFACT_BUCKET | tr -d '"')
    echo "ARTIFACT_BUCKET: $ARTIFACT_BUCKET"
    export ARTIFACT_BUCKET=$ARTIFACT_BUCKET

    SYSTEM_TABLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "SystemTable" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    SYSTEM_TABLE_NAME=$(echo $SYSTEM_TABLE_NAME | tr -d '"')
    export SYSTEM_TABLE_NAME=$SYSTEM_TABLE_NAME

    UPLOAD_FAILURES_TABLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id "UploadFailuresTable" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    UPLOAD_FAILURES_TABLE_NAME=$(echo $UPLOAD_FAILURES_TABLE_NAME | tr -d '"')
    export UPLOAD_FAILURES_TABLE_NAME=$UPLOAD_FAILURES_TABLE_NAME

    AUTH_RESOURCE_ID=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id AuthStack --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    echo $AUTH_RESOURCE_ID
    AUTH_NESTED_RESOURCE_ID=$(echo $AUTH_RESOURCE_ID | cut -d "/" -f 2)
    echo $AUTH_NESTED_RESOURCE_ID

    USER_POOL_ID=$(aws cloudformation describe-stack-resources --stack-name $AUTH_NESTED_RESOURCE_ID --logical-resource-id "UserPool" --query "StackResources[0].PhysicalResourceId" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi))
    USER_POOL_ID=$(echo "$USER_POOL_ID" | tr -d '"')
    echo "USER_POOL_ID: $USER_POOL_ID"
    export USER_POOL_ID=$USER_POOL_ID

    if [[ ${IN_VENV:-0} -ne 1 ]]; then
        pip install -q -r requirements-test.txt
    fi
    pytest integration_test/test_api_integration.py ${EXTRAS-} -vv ;
    aws iam detach-role-policy --role-name $AMC_GLUE_JOB_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $AWS_REGION $(if [ ! -z $AWS_DEFAULT_PROFILE ]; then echo "--profile $AWS_DEFAULT_PROFILE"; fi) ;

else
    help
fi
