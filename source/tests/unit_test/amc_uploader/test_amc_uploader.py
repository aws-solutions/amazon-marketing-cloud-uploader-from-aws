# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# ###############################################################################
# PURPOSE:
#   * Regression test for amc_uploader.
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name amc_uploader/test_amc_uploader.py
###############################################################################

import contextlib
import json
import os
import random
import urllib.parse
import uuid
from unittest.mock import MagicMock, patch
import boto3
import pytest
import responses
from moto import mock_aws
from responses import matchers


@pytest.fixture
def test_configs():
    return {
        "s3_bucket": "fake_s3_bucket",
        "s3_key": "dataset123|user1234",
        "instance_id": "instance123",
        "country_code": "US",
        "advertiser_id": "advertiser123",
        "marketplace_id": "marketplace123",
        "data_set_id": "dataset123",
        "stack_name": os.environ["STACK_NAME"],
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "s3_dimension_key": "amc/dataset123/ADDITIVE/US/dimension/amc12345678|us-east-1_Z85CJEZK1/dimension_manifest.txt",
        "s3_fact_key": "amc/dataset123/ADDITIVE/US/P1D/amc12345678|us-east-1_Z85CJEZK1/fact_manifest.txt",
    }


@contextlib.contextmanager
def create_test_cognito_user():
    with mock_aws():
        cognito_client = boto3.client(
            "cognito-idp", region_name="us-east-1"
        )
        cognito_res = cognito_client.create_user_pool(
            PoolName="user_test_1234"
        )
        user_id = cognito_res["UserPool"]["Id"]
        yield user_id


@pytest.fixture
def fake_event(test_configs):
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": test_configs["s3_bucket"]},
                },
            }
        ],
    }


@pytest.fixture
def fake_context():
    return MagicMock(log_stream_name="fake_log_stream")


def test_is_manifest():
    from amc_uploader.amc_uploader import _is_manifest

    assert _is_manifest("manifest.txt") is True
    assert _is_manifest("data.gz") is False


@patch("amc_uploader.amc_uploader._start_upload")
def test_lambda_handler(
    mock_start_upload, fake_event, fake_context, test_configs
):
    mock_start_upload.return_value = {}
    from amc_uploader.amc_uploader import lambda_handler

    fake_event["Records"][0]["s3"].update(
        {"object": {"key": test_configs["s3_dimension_key"]}}
    )

    lambda_handler(fake_event, fake_context)
    mock_start_upload.assert_called_with(
        bucket=test_configs["s3_bucket"],
        key=fake_event["Records"][0]["s3"]["object"]["key"],
    )

    fake_event["Records"][0]["s3"].update(
        {"object": {"key": test_configs["s3_fact_key"]}}
    )

    lambda_handler(fake_event, fake_context)
    mock_start_upload.assert_called_with(
        bucket=test_configs["s3_bucket"],
        key=fake_event["Records"][0]["s3"]["object"]["key"],
    )


@contextlib.contextmanager
def stub_system_table(test_configs):
    with mock_aws():
        dynamodb = boto3.resource(
            "dynamodb", region_name=os.environ["AWS_REGION"]
        )
        params = {
            "TableName": os.environ["SYSTEM_TABLE_NAME"],
            "KeySchema": [
                {"AttributeName": "Name", "KeyType": "HASH"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "Name", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        }

        table = dynamodb.create_table(**params)

        item = {
            "Name": "AmcInstances",
            "Value": [
                {
                    "instance_id": test_configs["instance_id"],
                    "advertiser_id": test_configs["advertiser_id"],
                    "marketplace_id": test_configs["marketplace_id"],
                }
            ],
        }
        table.put_item(TableName=os.environ["SYSTEM_TABLE_NAME"], Item=item)

        yield


@contextlib.contextmanager
def stub_secret_and_ads_token(test_configs, user_id):
    with mock_aws():
        refresh_token = f"refresh-token-{uuid.uuid4()}"
        access_token = f"access_token-{uuid.uuid4()}"
        # Create secret if it does not already exist.
        secret_id = f"{test_configs['stack_name']}-{user_id}"
        session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
        client = session.client("secretsmanager")
        secrets = client.list_secrets()
        if secret_id not in [secret['Name'] for secret in secrets['SecretList']]:
            client.create_secret(
                Name=secret_id,
                SecretString=json.dumps(
                    {
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                        "refresh_token": refresh_token,
                    }
                ),
            )
        else:
            client.update_secret(
                SecretId=secret_id,
                SecretString=json.dumps(
                    {
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                        "refresh_token": refresh_token,
                    }
                ),
            )

        responses.post(
            url="https://api.amazon.com/auth/o2/token",
            json={
                "refresh_token": refresh_token,
                "access_token": access_token,
            },
            status=200,
            match=[
                matchers.urlencoded_params_matcher(
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "redirect_uri": "None",
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                    }
                ),
                matchers.header_matcher({}),
            ],
        )
        yield


@pytest.fixture
@responses.activate
def mock_amc_request(test_configs):
    def mock_amc_request_method(
        expected_amc_response, mock_http_method, mock_amc_path
    ):
        getattr(responses, mock_http_method.lower())(
            url=urllib.parse.urljoin(
                "https://advertising-api.amazon.com/",
                f"/amc/advertiserData/{test_configs['instance_id']}{mock_amc_path}",
            ),
            json=expected_amc_response,
            status=200,
        )

    return mock_amc_request_method

def test_start_upload(test_configs, mock_amc_request):
    from amc_uploader.amc_uploader import _start_upload

    expected_data = {"upload": [{"some_upload": "data"}]}

    def start_upload(user_id):
        s3_dimension_key = f"amc/{test_configs['data_set_id']}/ADDITIVE/US/dimension/{test_configs['instance_id']}|{user_id}/dimension_file.json.gz"

        mock_amc_request(
            expected_amc_response=expected_data,
            mock_http_method="POST",
            mock_amc_path="/uploads/" + test_configs["data_set_id"],
        )

        return _start_upload(
            bucket=test_configs["s3_bucket"], key=s3_dimension_key
        )

    with create_test_cognito_user() as user_id:
        # Create secret if it does not already exist.
        secret_id = f"{test_configs['stack_name']}-{user_id}"
        session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
        client = session.client("secretsmanager")
        secrets = client.list_secrets()
        if secret_id not in [secret['Name'] for secret in secrets['SecretList']]:
            client.create_secret(
                Name=secret_id,
                SecretString=json.dumps(
                    {
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                    }
                ),
            )
        with mock_aws():
            # Validate that unauthorized requests return an error message.
            assert (
                str(start_upload(user_id=user_id)["Message"])
                == "Unauthorized AMC request."
            )
        with stub_secret_and_ads_token(
            test_configs=test_configs, user_id=user_id
        ), stub_system_table(test_configs):
            start_upload(user_id=user_id)

            # Uploads are performed asynchronously by the amc_uploader.py Lambda function.
            # That function is triggered by S3 when the Glue ETL job saves its results.
            # If an upload fails, then amc_uploader.py saves the error message to DynamoDB
            # so that the front-end can show the error message to the user.
            #
            # The following test exercises that logic by uploading a dataset and attempting
            # to delete any previously recorded upload failures for that dataset from DynamoDB.
            dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
            params = {
                "TableName": os.environ["UPLOAD_FAILURES_TABLE_NAME"],
                "KeySchema": [
                    {"AttributeName": "instance_id", "KeyType": "HASH"},
                    {"AttributeName": "dataset_id", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "instance_id", "AttributeType": "S"},
                    {"AttributeName": "dataset_id", "AttributeType": "S"},
                ],
                "BillingMode": "PAY_PER_REQUEST",
            }
            dynamodb.create_table(**params)

            s3_fact_key = f"amc/{test_configs['data_set_id']}/ADDITIVE/US/P1D/{test_configs['instance_id']}|{user_id}/fact_file.json-2022_01_06-{random.randint(10, 20)}:01:00.gz"

            mock_amc_request(
                expected_amc_response={},
                mock_http_method="POST",
                mock_amc_path="/uploads/"
                + test_configs["data_set_id"],
            )

            data = _start_upload(
                bucket=test_configs["s3_bucket"], key=s3_fact_key
            )
            assert json.loads(data) == expected_data


@mock_aws
def test_start_upload_unauthorized_amc_request(test_configs):
    from amc_uploader.amc_uploader import _start_upload

    with create_test_cognito_user() as user_id:
        # Create secret if it does not already exist.
        secret_id = f"{test_configs['stack_name']}-{user_id}"
        session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
        client = session.client("secretsmanager")
        secrets = client.list_secrets()
        if secret_id not in [secret['Name'] for secret in secrets['SecretList']]:
            client.create_secret(
                Name=secret_id,
                SecretString=json.dumps(
                    {
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                    }
                ),
            )

        s3_fact_key = f"amc/{test_configs['data_set_id']}/ADDITIVE/US/PT1M/{test_configs['instance_id']}|{user_id}/fact_file.json-2022_01_06-{random.randint(10, 20)}:01:00.gz"
        data = _start_upload(
            bucket=test_configs["s3_bucket"], key=s3_fact_key
        )
        assert str(data["Message"]) == "Unauthorized AMC request."