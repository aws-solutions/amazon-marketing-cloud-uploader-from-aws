# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Regression test for helper.
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name test_helper.py
###############################################################################


import json
import os
from unittest.mock import MagicMock, mock_open, patch

import boto3
import botocore
import pytest
from moto import mock_aws


@pytest.fixture
def test_configs():
    return {
        "response_status": "SUCCESS",
        "s3_bucket": "fake_s3_bucket",
        "s3_key": "some_file.json",
        "s3_prefix": "some_prefix",
        "s3_artifact_bucket": "fake_s3_artifact_bucket",
        "api_endpoint": "https://test_end_point_url.com/test",
        "content_type": "application/json",
    }


@pytest.fixture
def fake_event(test_configs):
    return {
        "StackId": 12345,
        "RequestId": 67890,
        "LogicalResourceId": 1112131415,
        "ResponseURL": "https://test.com/test",
        "ResourceProperties": {
            "WebsiteCodeBucket": test_configs["s3_bucket"],
            "WebsiteCodePrefix": test_configs["s3_prefix"],
            "DeploymentBucket": f"{test_configs['s3_bucket']}.some_bucket",
        },
    }


@pytest.fixture
def fake_config_event(test_configs):
    return {
        "StackId": 12345,
        "RequestId": 67890,
        "LogicalResourceId": 1112131415,
        "ResponseURL": "https://test.com/test",
        "ResourceProperties": {
            "API_ENDPOINT": "API_ENDPOINT Value",
            "AWS_REGION": "AWS_REGION Value",
            "USER_POOL_ID": "USER_POOL_ID Value",
            "USER_POOL_CLIENT_ID": "USER_POOL_CLIENT_ID Value",
            "IDENTITY_POOL_ID": "IDENTITY_POOL_ID Value",
            "DATA_BUCKET_NAME": "DATA_BUCKET_NAME Value",
            "ARTIFACT_BUCKET_NAME": "ARTIFACT_BUCKET_NAME Value",
            "ENCRYPTION_MODE": "ENCRYPTION_MODE Value",
            "HOSTED_UI_DOMAIN": "HOSTED_UI_DOMAIN Value",
            "COGNITO_CALLBACK_URL": "COGNITO_CALLBACK_URL Value",
            "COGNITO_LOGOUT_URL": "COGNITO_LOGOUT_URL Value",
            "WEBSITE_BUCKET": test_configs["s3_bucket"]
        },
    }


@pytest.fixture
def fake_context():
    return MagicMock(log_stream_name="fake_log_stream")


@pytest.fixture
def mock_env_variables(test_configs):
    os.environ["UserPoolId"] = "3333"
    os.environ["PoolClientId"] = "4444"
    os.environ["IdentityPoolId"] = "2222"
    os.environ["ApiEndpoint"] = test_configs["api_endpoint"]
    os.environ["DataBucketName"] = test_configs["s3_bucket"]
    os.environ["ArtifactBucketName"] = test_configs["s3_artifact_bucket"]
    os.environ["EncryptionMode"] = "Secured"


@mock_aws
@patch("urllib.request.build_opener")
def test_send_response(mock_response, fake_event, fake_context, test_configs):
    from helper.website_helper import send_response

    send_response(
        event=fake_event,
        context=fake_context,
        response_status=test_configs["response_status"],
        response_data={},
    )


@mock_aws
@patch("urllib.request.build_opener")
def test_copy_source(mock_response, mock_env_variables, fake_event, fake_context, test_configs):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3_bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3_bucket"],
        f'{test_configs["s3_prefix"]}/{test_configs["s3_key"]}',
    )
    s3_object.put(Body="{}", ContentType=test_configs["content_type"])
    file_loc = "./webapp-manifest.json"
    from helper.website_helper import lambda_handler

    manifest_data = [test_configs["s3_key"]]

    with patch(
        "builtins.open", mock_open(read_data=json.dumps(manifest_data))
    ) as mock_file:
        from helper.website_helper import copy_source
        copy_source(event=fake_event)
        mock_file.assert_called_with(file_loc, encoding="utf-8")


@patch("urllib.request.build_opener")
def test_lambda_handler(mock_response, fake_event, fake_context, test_configs):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=test_configs["s3_bucket"])
        s3 = boto3.resource("s3", region_name="us-east-1")
        s3_object = s3.Object(
            test_configs["s3_bucket"],
            f'{test_configs["s3_prefix"]}/{test_configs["s3_key"]}',
        )
        s3_object.put(Body="{}", ContentType=test_configs["content_type"])
        file_loc = "./webapp-manifest.json"
        from helper.website_helper import lambda_handler

        manifest_data = [test_configs["s3_key"]]

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(manifest_data))
        ) as mock_file:
            fake_event["RequestType"] = "Create"
            lambda_handler(event=fake_event, context=fake_context)

            fake_event["RequestType"] = "Update"
            lambda_handler(event=fake_event, context=fake_context)

        mock_file.assert_called_with(file_loc, encoding="utf-8")
        fake_event["RequestType"] = "Delete"
        lambda_handler(event=fake_event, context=fake_context)


@patch("urllib.request.build_opener")
def test_config_lambda_handler(mock_response, fake_config_event, fake_context, test_configs):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=test_configs["s3_bucket"])
        file = "runtimeConfig.json"
        from helper.config_helper import handler

        fake_config_event["RequestType"] = "Create"
        handler(event=fake_config_event, context=fake_context)
        s3.head_object(Bucket=test_configs["s3_bucket"], Key=file)

        fake_config_event["RequestType"] = "Update"
        handler(event=fake_config_event, context=fake_context)
        s3.head_object(Bucket=test_configs["s3_bucket"], Key=file)

        fake_config_event["RequestType"] = "Delete"
        handler(event=fake_config_event, context=fake_context)
        s3.head_object(Bucket=test_configs["s3_bucket"], Key=file)
