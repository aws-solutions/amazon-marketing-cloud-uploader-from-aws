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
import pytest
from moto import mock_s3


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
def fake_context():
    return MagicMock(log_stream_name="fake_log_stream")


@pytest.fixture
def mock_env_variables(test_configs):
    os.environ["UserPoolId"] = "3333"
    os.environ["AwsRegion"] = "us-east-1"
    os.environ["PoolClientId"] = "4444"
    os.environ["IdentityPoolId"] = "2222"
    os.environ["ApiEndpoint"] = test_configs["api_endpoint"]
    os.environ["DataBucketName"] = test_configs["s3_bucket"]
    os.environ["ArtifactBucketName"] = test_configs["s3_artifact_bucket"]
    os.environ["EncryptionMode"] = "Secured"


@mock_s3
@patch("urllib.request.build_opener")
def test_send_response(mock_response, fake_event, fake_context, test_configs):
    from helper.website_helper import send_response

    send_response(
        event=fake_event,
        context=fake_context,
        response_status=test_configs["response_status"],
        response_data={},
    )


@mock_s3
def test_write_to_s3(fake_event, fake_context, test_configs):
    from helper.website_helper import write_to_s3

    write_to_s3(
        event=fake_event,
        context=fake_context,
        bucket=test_configs["s3_bucket"],
        key=test_configs["s3_key"],
        body={},
    )


@mock_s3
@patch("urllib.request.build_opener")
def test_copy_source(mock_response, fake_event, fake_context):
    from helper.website_helper import copy_source

    fake_event.pop("ResourceProperties")

    copy_source(event=fake_event, context=fake_context)


@mock_s3
@patch("urllib.request.build_opener")
def test_copy_source_fail_env_key(
    mock_response, mock_env_variables, fake_event, fake_context, test_configs
):
    from helper.website_helper import copy_source

    os.environ.pop("UserPoolId")

    copy_source(event=fake_event, context=fake_context)


@patch("urllib.request.build_opener")
def test_copy_source_else(
    mock_response, mock_env_variables, fake_event, fake_context, test_configs
):
    with mock_s3():
        s3 = boto3.client("s3", region_name=os.environ["AwsRegion"])
        s3.create_bucket(Bucket=test_configs["s3_bucket"])
        s3 = boto3.resource("s3")
        s3_object = s3.Object(
            test_configs["s3_bucket"],
            f'{test_configs["s3_prefix"]}/{test_configs["s3_key"]}',
        )
        s3_object.put(Body="{}", ContentType=test_configs["content_type"])
        file_loc = "./webapp-manifest.json"
        manifest_data = [test_configs["s3_key"]]
        from helper.website_helper import copy_source

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(manifest_data))
        ) as mock_file:
            copy_source(event=fake_event, context=fake_context)

        mock_file.assert_called_with(file_loc, encoding="utf-8")


@patch("urllib.request.build_opener")
def test_purge_bucket(mock_response, fake_event, fake_context, test_configs):
    with mock_s3():
        s3 = boto3.client("s3", region_name=os.environ["AwsRegion"])
        s3.create_bucket(Bucket=test_configs["s3_bucket"])
        s3 = boto3.resource("s3")
        s3_object = s3.Object(
            test_configs["s3_bucket"],
            f'{test_configs["s3_prefix"]}/{test_configs["s3_key"]}',
        )
        s3_object.put(Body="{}", ContentType=test_configs["content_type"])
        from helper.website_helper import purge_bucket

        purge_bucket(event=fake_event, context=fake_context)


@patch("urllib.request.build_opener")
def test_lambda_handler(mock_response, fake_event, fake_context, test_configs):
    with mock_s3():
        s3 = boto3.client("s3", region_name=os.environ["AwsRegion"])
        s3.create_bucket(Bucket=test_configs["s3_bucket"])
        s3 = boto3.resource("s3")
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
