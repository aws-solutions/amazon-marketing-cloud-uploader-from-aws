# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Unit test for project api endpoints and workflow.
#
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name test_api.py
###############################################################################

import contextlib
import json
import os
import urllib.parse
import uuid
from unittest.mock import patch, MagicMock

import app
import boto3
import pytest
import responses
from chalice.test import Client
from moto import mock_aws
from responses import matchers


@pytest.fixture
def test_configs():
    return {
        "s3bucket": "fake_s3_bucket",
        "outputBucket": "fake_output_bucket",
        "source_key": "some_file.json",
        "data_set_id": "test_data_set_id",
        "period": "autodetect",
        "content_type": "application/json",
        "s3_artifact_bucket": os.environ["ARTIFACT_BUCKET"],
        "amc_role": os.environ["AMC_API_ROLE_ARN"],
        "stack_name": os.environ["STACK_NAME"],
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "customer_managed_key": os.environ["CUSTOMER_MANAGED_KEY"],
        "ads_scope": "profile%20advertising::campaign_management",
        "instance_id": "amc12345678",
        "advertiser_id": "ads12345",
        "marketplace_id": "12132mkid",
        "redirect_uri": "https://example.com",
        "data_upload_account_id": "123456789012",
        "aws_account_id": "123456789012",
        "state": "test_state",
        "upload_error_message": "The provided timeWindowStart is before our stated retention period. Provided TimeWindowStart = 2021-06-01T00:00:00Z, earliest allowable timeWindowStart = 2022-02-14T21:00:00Z (Service: SquallDataIngestion; Status Code: 400; Error Code: ValidationException; Request ID: 1662b4e7-aee5-418b-aa21-c1d0062ffc90; Proxy: null",
    }


@pytest.fixture
def test_data():
    return [
        {
            "first_name": "Caroline",
            "last_name": "Crane",
            "email": "funis@example.com",
            "product_quantity": 67,
            "product_name": "Product C",
        },
        {
            "first_name": "David",
            "last_name": "Picard",
            "email": "thearound@example.com",
            "product_quantity": 60,
            "product_name": "Product E",
        },
        {
            "first_name": "William",
            "last_name": "Trout",
            "email": "takefood@example.com",
            "product_quantity": 35,
            "product_name": "Product G",
        },
    ]


@pytest.fixture
def get_amc_json(test_data):
    output = ""
    for item in test_data:
        output += json.dumps(item) + "\n"

    return output


@pytest.fixture
def get_amc_instance_info(test_configs):
    return {
        "instance_id": test_configs["instance_id"],
        "advertiser_id": test_configs["advertiser_id"],
        "marketplace_id": test_configs["marketplace_id"],
        "state": test_configs["state"],
    }


@pytest.fixture
def get_headers(test_configs):
    return {
        "Content-Type": test_configs["content_type"],
        "Origin": test_configs["redirect_uri"],
    }


@contextlib.contextmanager
def create_test_cognito_user():
    cognito_client = boto3.client(
        "cognito-idp", region_name="us-east-1"
    )
    cognito_res = cognito_client.create_user_pool(PoolName="user_test_1234")
    user_id = cognito_res["UserPool"]["Id"]
    yield user_id


@mock_aws
@contextlib.contextmanager
@responses.activate
def mock_authorize_amc_request(
    user_id,
    test_configs,
    mock_amc_path,
    mock_amc_response,
    mock_http_method,
    mock_payload=None,
    is_mock_amc_response=True,
    is_amc_report=True,
    override_match_amc_req_headers=None,
):
    refresh_token = f"refresh-token-{uuid.uuid4()}"
    access_token = f"access_token-{uuid.uuid4()}"
    redirect_uri = f"{test_configs['redirect_uri']}/redirect"
    responses.post(
        url="https://api.amazon.com/auth/o2/token",
        json={"refresh_token": refresh_token, "access_token": access_token},
        status=200,
        match=[
            matchers.urlencoded_params_matcher(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "redirect_uri": redirect_uri,
                    "client_id": test_configs["client_id"],
                    "client_secret": test_configs["client_secret"],
                }
            ),
            matchers.header_matcher({}),
        ],
    )

    if override_match_amc_req_headers:
        override_match_amc_req_headers[
            "Authorization"
        ] = f"Bearer {access_token}"

    match_amc_req_headers = override_match_amc_req_headers or {
        "Amazon-Advertising-API-ClientId": test_configs["client_id"],
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Amazon-Advertising-API-AdvertiserId": test_configs["advertiser_id"],
        "Amazon-Advertising-API-MarketplaceId": test_configs["marketplace_id"],
    }

    if is_mock_amc_response:
        payload_match = None
        if mock_payload:
            payload_match = matchers.urlencoded_params_matcher(mock_payload)

        match_data = [
            payload_match,
            matchers.header_matcher(match_amc_req_headers),
        ]
        match_data = [match_item for match_item in match_data if match_item]

        amc_path = mock_amc_path
        if is_amc_report:
            amc_path = (
                f"/amc/advertiserData/{test_configs['instance_id']}{mock_amc_path}"
            )
        getattr(responses, mock_http_method.lower())(
            url=urllib.parse.urljoin(
                "https://advertising-api.amazon.com/",
                amc_path,
            ),
            json=mock_amc_response,
            status=200,
            match=match_data,
        )

    # Save client_id, client_secret, and refresh_token in secrets manager
    # since these values are used within API Handler.
    secret_id = f"{test_configs['stack_name']}-{user_id}"
    session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
    client = session.client("secretsmanager")
    secrets = client.list_secrets()
    if secret_id in [secret['Name'] for secret in secrets['SecretList']]:
        client.delete_secret(
            SecretId=secret_id,
            ForceDeleteWithoutRecovery=True
        )
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
    yield


def test_version(test_configs):
    with Client(app.app) as client:
        response = client.http.get(
            "/version",
            headers={"Content-Type": test_configs["content_type"]},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]

@mock_aws
def test_list_bucket(test_configs):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3bucket"], test_configs["source_key"]
    )
    s3_object.put(Body="{}", ContentType=test_configs["content_type"])

    with Client(app.app) as client:
        response = client.http.post(
            "/list_bucket",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps({"s3bucket": test_configs["s3bucket"]}),
        )
        assert response.status_code == 200
        assert response.json_body[0]["key"] == test_configs["source_key"]
        assert response.json_body[0]["size"] == 2

@mock_aws
def test_get_data_columns(test_configs, get_amc_json, test_data):
    content_type = test_configs["content_type"]
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3bucket"], test_configs["source_key"]
    )
    s3_object.put(Body=get_amc_json, ContentType=content_type)

    with Client(app.app) as client:
        response = client.http.post(
            "/get_data_columns",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"]
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body["columns"] is not None
        for expected_key in list(test_data[0].keys()):
            assert expected_key in response.json_body["columns"]


def test_save_invalid_oauth_credentials(test_configs):
    # Validate that invalid client_id is not saved in the secrets manager.
    # save client and secret to Aws secret.
    xss_signature = "<script>alert(1)</script>"
    with Client(app.app) as client:
        response = client.http.post(
            "/save_secret",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps(
                {
                    "user_id": "sample_user_id",
                    "client_id": xss_signature,
                    "client_secret": test_configs["client_secret"],
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {'Status': 'Error', 'Message': 'Client ID must contain only letters, numbers, dashes, and periods.'}

        response = client.http.post(
            "/save_secret",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps(
                {
                    "user_id": "sample_user_id",
                    "client_id": test_configs["client_id"],
                    "client_secret": xss_signature,
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {'Status': 'Error', 'Message': 'Client Secret must contain only letters, numbers, dashes, and periods.'}


@mock_aws
def test_get_data_columns_invalid_content_type(test_configs, get_amc_json):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3bucket"], test_configs["source_key"]
    )
    s3_object.put(Body=get_amc_json, ContentType="application/octet-stream")

    with Client(app.app) as client:
        response = client.http.post(
            "/get_data_columns",
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"]
                }
            ),
        )
        assert response.status_code == 400
        assert response.json_body["Message"] == "Unsupported content type application/octet-stream"

@mock_aws
def test_get_data_columns_gzip(test_configs, get_amc_json):
    # This test validates the error message which is returned when content type
    # is application/x-gzip but the filename does not end with .json.gz or .csv.gz
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3bucket"], test_configs["source_key"]
    )
    s3_object.put(Body=get_amc_json, ContentType="application/x-gzip")

    with Client(app.app) as client:
        response = client.http.post(
            "/get_data_columns",
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"]
                }
            ),
        )
        message = "Cannot infer file format of gzipped file."
        assert response.status_code == 400
        assert response.json_body["Message"] == message


@mock_aws
def test_get_data_columns_fileformat(test_configs, get_amc_json, test_data):
    # This test validates the error message which is returned when the fileFormat
    # parameter is invalid.
    content_type = test_configs["content_type"]
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=test_configs["s3bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3bucket"], test_configs["source_key"]
    )
    s3_object.put(Body=get_amc_json, ContentType=content_type)

    with Client(app.app) as client:
        response = client.http.post(
            "/get_data_columns",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"],
                    "fileFormat": "NONSENSE_FORMAT"
                }
            ),
        )
        assert response.status_code == 400
        assert response.json_body["Message"] == "Unexpected file format: NONSENSE_FORMAT"

        response = client.http.post(
            "/get_data_columns",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"],
                    "fileFormat": "JSON"
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body["columns"] is not None
        for expected_key in list(test_data[0].keys()):
            assert expected_key in response.json_body["columns"]

        response = client.http.post(
            "/get_data_columns",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "s3bucket": test_configs["s3bucket"],
                    "s3key": test_configs["source_key"],
                    "fileFormat": "CSV"
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body["columns"] is not None


@mock_aws
def test_list_upload_failures(test_configs):
    # this test checks for a valid upload failure message in the upload_failures_table
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
    table = dynamodb.create_table(**params)
    item = {
        "dataset_id": test_configs["data_set_id"],
        "instance_id": test_configs["instance_id"],
        "Value": test_configs["upload_error_message"],
    }
    table.put_item(
        TableName=os.environ["UPLOAD_FAILURES_TABLE_NAME"], Item=item
    )

    payload = {
        "instance_id": test_configs["instance_id"],
        "dataSetId": test_configs["data_set_id"],
    }

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/list_upload_failures",
            headers={"Content-Type": content_type},
            body=json.dumps(payload),
        )
        assert response.status_code == 200
        assert (
            response.body.decode("ascii")
            == test_configs["upload_error_message"]
        )

    # Validate the an invalid request returns an error message
    with Client(app.app) as client:
        response = client.http.post(
            "/list_upload_failures",
            headers={"Content-Type": content_type},
            body=json.dumps({}),
        )
    assert response.json_body == {"Status": "Error", "Message": "'dataSetId'"}


@mock_aws
@pytest.fixture
def run_amc_api_request_test():
    def run_api_test_method(
        api_client,
        mock_params,
        test_response,
    ):
        test_configs = mock_params["test_configs"]
        with create_test_cognito_user() as user_id:

            # Save client_id and client_secret in Secrets Manager if they do not already exist.
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

            # Validate that unauthorized requests return an authorize_url
            with api_client(user_id) as response:
                assert response.json_body["authorize_url"] is not None
                assert (
                    response.json_body["authorize_url"]
                    == f"https://www.amazon.com/ap/oa?client_id={test_configs['client_id']}&scope={test_configs['ads_scope']}&response_type=code&redirect_uri={test_configs['redirect_uri']}/redirect&state={test_configs['state']}"
                )

            # Validate that authorized requests return expected response
            with mock_authorize_amc_request(
                **mock_params,
                user_id=user_id,
            ):
                with api_client(user_id) as response:
                    test_response(response)

    return run_api_test_method


@mock_aws
def test_delete_dataset(
    test_configs, get_amc_instance_info, get_headers, run_amc_api_request_test
):
    dynamodb = boto3.client("dynamodb", region_name=os.environ["AWS_REGION"])
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
    expected_amc_response = {}

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": f"/dataSets/{test_configs['data_set_id']}",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "DELETE",
    }

    @contextlib.contextmanager
    def delete_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/delete_dataset",
                headers=get_headers,
                body=json.dumps(
                    {
                        **get_amc_instance_info,
                        "user_id": user_id,
                        "dataSetId": test_configs["data_set_id"],
                    }
                ),
            )

            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    run_amc_api_request_test(
        api_client=delete_api,
        mock_params=mock_params,
        test_response=test_response,
    )


@mock_aws
def test_list_datasets(
    test_configs, get_headers, run_amc_api_request_test, get_amc_instance_info
):
    expected_amc_response = {
        "dataSets": [
            {
                "columns": [
                    {
                        "dataType": "STRING",
                        "description": "The customer resolved id",
                        "isMainEventTime": False,
                        "isMainUserId": True,
                        "isMainUserIdType": False,
                        "isNullable": True,
                        "name": "user_id",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "dataType": "STRING",
                        "description": "The customer resolved type",
                        "isMainEventTime": False,
                        "isMainUserId": False,
                        "isMainUserIdType": True,
                        "isNullable": True,
                        "name": "user_type",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "dataType": "STRING",
                        "description": "hashed First name",
                        "externalUserIdType": {
                            "hashedPii": "FIRST_NAME"
                        },
                        "isMainEventTime": False,
                        "isMainUserId": False,
                        "isMainUserIdType": False,
                        "isNullable": True,
                        "name": "first_name",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "dataType": "STRING",
                        "description": "hashed Last name",
                        "externalUserIdType": {
                            "hashedPii": "LAST_NAME",
                        },
                        "isMainEventTime": False,
                        "isMainUserId": False,
                        "isMainUserIdType": False,
                        "isNullable": True,
                        "name": "last_name",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "dataType": "TIMESTAMP",
                        "description": "Timestamp",
                        "isMainEventTime": True,
                        "isMainUserId": False,
                        "isMainUserIdType": False,
                        "isNullable": False,
                        "name": "timestamp",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "columnType": "DIMENSION",
                        "dataType": "STRING",
                        "description": "Product quantity",
                        "isMainEventTime": False,
                        "isMainUserId": False,
                        "isMainUserIdType": False,
                        "isNullable": False,
                        "name": "product_quantity",
                        "requiresOneWayHashing": False,
                    },
                    {
                        "columnType": "METRIC",
                        "dataType": "STRING",
                        "description": "Product name",
                        "isMainEventTime": False,
                        "isMainUserId": False,
                        "isMainUserIdType": False,
                        "isNullable": False,
                        "name": "product_name",
                        "requiresOneWayHashing": False,
                    },
                ],
                "compressionFormat": "GZIP",
                "createdTime": "2023-03-14T20:39:19.043Z",
                "dataSetId": "sample_dataset_123",
                "dataSetType": "FACT",
                "fileFormat": "JSON",
                "owner": "CUSTOMER",
                "period": "P1D",
                "updatedTime": "2023-03-14T20:39:19.043Z",
            },
        ]
    }

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": "/dataSets/list",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "POST",
    }

    @contextlib.contextmanager
    def list_datasets_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/list_datasets",
                headers=get_headers,
                body=json.dumps(
                    {
                        **get_amc_instance_info,
                        "user_id": user_id,
                    }
                ),
            )
            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    run_amc_api_request_test(
        api_client=list_datasets_api,
        mock_params=mock_params,
        test_response=test_response,
    )


@mock_aws
def test_describe_dataset(
    test_configs, get_amc_instance_info, get_headers, run_amc_api_request_test
):
    test_body = {
        **get_amc_instance_info,
        "dataSetId": test_configs["data_set_id"],
    }
    expected_amc_response = {
        "columns": [
            {
                "dataType": "STRING",
                "description": "The customer resolved id",
                "isMainEventTime": False,
                "isMainUserId": True,
                "isMainUserIdType": False,
                "isNullable": True,
                "name": "user_id",
                "requiresOneWayHashing": False,
            },
            {
                "dataType": "STRING",
                "description": "The customer resolved type",
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": True,
                "isNullable": True,
                "name": "user_type",
                "requiresOneWayHashing": False,
            },
            {
                "dataType": "STRING",
                "description": "hashed First name",
                "externalUserIdType": {
                    "hashedPii": "FIRST_NAME"
                },
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": True,
                "name": "first_name",
                "requiresOneWayHashing": False,
            },
            {
                "dataType": "STRING",
                "description": "hashed Last name",
                "externalUserIdType": {
                    "hashedPii": "LAST_NAME",
                },
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": True,
                "name": "last_name",
                "requiresOneWayHashing": False,
            },
            {
                "dataType": "STRING",
                "description": "hashed Email",
                "externalUserIdType": {
                    "hashedPii": "EMAIL",
                },
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": True,
                "name": "email",
                "requiresOneWayHashing": False,
            },
            {
                "dataType": "STRING",
                "description": "Product quantity",
                "externalUserIdType": {"externalIdentity": "LIVERAMP"},
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": False,
                "name": "product_quantity",
                "requiresOneWayHashing": False,
            },
            {
                "columnType": "DIMENSION",
                "dataType": "STRING",
                "description": "Timestamp",
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": False,
                "name": "timestamp",
                "requiresOneWayHashing": False,
            },
            {
                "columnType": "DIMENSION",
                "dataType": "STRING",
                "description": "Product name",
                "isMainEventTime": False,
                "isMainUserId": False,
                "isMainUserIdType": False,
                "isNullable": False,
                "name": "product_name",
                "requiresOneWayHashing": False,
            },
        ],
        "compressionFormat": "GZIP",
        "createdTime": "2023-03-22T19:26:35.034Z",
        "dataSetId": "imgeo-normal",
        "dataSetType": "DIMENSION",
        "fileFormat": "JSON",
        "owner": "CUSTOMER",
        "period": "P1D",
        "updatedTime": "2023-03-22T19:26:35.034Z",
    }

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": f"/dataSets/{test_configs['data_set_id']}",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "GET",
    }

    @contextlib.contextmanager
    def describe_dataset_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/describe_dataset",
                headers=get_headers,
                body=json.dumps(
                    {
                        **test_body,
                        "user_id": user_id,
                        "state": test_configs["state"],
                    }
                ),
            )
            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    run_amc_api_request_test(
        api_client=describe_dataset_api,
        mock_params=mock_params,
        test_response=test_response,
    )

    # This test verifies that the POST to /describe_dataset returns an error
    # message when test_body is missing required parameters.
    test_body = {}
    expected_amc_response = {"Message": "'dataSetId'", "Status": "Error"}
    mock_params["mock_amc_response"] = expected_amc_response

    run_amc_api_request_test(
        api_client=describe_dataset_api,
        mock_params=mock_params,
        test_response=test_response,
    )


@mock_aws
def test_upload_status(
    test_configs, get_amc_instance_info, get_headers, run_amc_api_request_test
):
    expected_amc_response = {
        "sourceS3Bucket": "some_bucket",
        "sourceManifestS3Key": "some_key",
        "status": ["Succeeded"],
    }

    upload_id = "123456"

    @contextlib.contextmanager
    def upload_status_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/upload_status",
                headers=get_headers,
                body=json.dumps(
                    {
                        **get_amc_instance_info,
                        "user_id": user_id,
                        "dataSetId": test_configs["data_set_id"],
                        "uploadId": upload_id,
                    }
                ),
            )
            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": f"/uploads/{test_configs['data_set_id']}/{upload_id}",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "GET",
    }

    run_amc_api_request_test(
        api_client=upload_status_api,
        mock_params=mock_params,
        test_response=test_response,
    )

@mock_aws
def test_get_etl_jobs(
        test_configs, get_amc_instance_info, get_headers, run_amc_api_request_test
):
    content_type = test_configs["content_type"]

    data_set_id = test_configs["data_set_id"]
    solution_config = json.loads(os.environ["botoConfig"])
    from botocore import config

    config = config.Config(**solution_config)
    glue_client = boto3.client("glue", config=config)

    glue_client.create_job(
        Name=os.environ["AMC_GLUE_JOB_NAME"],
        Role="Glue_DefaultRole",
        Command={
            "Name": "glueetl",
            "ScriptLocation": "s3://my_script_bucket/scripts/my_etl_script.py",
        },
    )
    glue_response = glue_client.start_job_run(
        JobName=os.environ["AMC_GLUE_JOB_NAME"],
        Arguments={"--dataset_id": data_set_id},
    )
    job_run_data = glue_client.get_job_run(
        JobName=os.environ["AMC_GLUE_JOB_NAME"],
        RunId=glue_response["JobRunId"],
    )
    with patch("app.boto3.client") as mock_get_job_runs:
        job_run_data["JobRun"]["Arguments"].update(
            {"--dataset_id": data_set_id}
        )
        job_runs_data = {"JobRuns": [job_run_data["JobRun"]]}
        mock_get_job_runs.return_value.get_job_runs.return_value = (
            job_runs_data
        )
        with Client(app.app) as client:
            response = client.http.get(
                "/get_etl_jobs",
                headers={"Content-Type": content_type},
            )
            assert response.status_code == 200
            assert data_set_id == response.json_body["JobRuns"][0].pop(
                "DatasetId"
            )
            assert response.json_body["JobRuns"] == json.loads(
                json.dumps(job_runs_data["JobRuns"], default=str)
            )


@mock_aws
def test_create_dataset(
    test_configs, get_amc_instance_info, get_headers, run_amc_api_request_test
):
    @contextlib.contextmanager
    def create_dataset_api(user_id):
        payload = {
            "body": {
                "dataSetId": test_configs["data_set_id"],
                "dataSetType": "DIMENSION",
                "compressionFormat": "GZIP",
                "columns": [],
                "period": "autodetect",
            },
        }

        with Client(app.app) as client:
            response = client.http.post(
                "/create_dataset",
                headers=get_headers,
                body=json.dumps(
                    {
                        "user_id": user_id,
                        **payload,
                        **get_amc_instance_info,
                    }
                ),
            )

        yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == {}

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": "/dataSets",
        "mock_amc_response": {},
        "mock_http_method": "POST",
    }

    run_amc_api_request_test(
        api_client=create_dataset_api,
        mock_params=mock_params,
        test_response=test_response,
    )


@mock_aws
def test_start_amc_transformation(
    test_configs, get_headers, run_amc_api_request_test
):
    with mock_aws():
        solution_config = json.loads(os.environ["botoConfig"])
        from botocore import config

        config = config.Config(**solution_config)
        glue_client = boto3.client("glue", config=config)

        glue_client.create_job(
            Name=os.environ["AMC_GLUE_JOB_NAME"],
            Role="Glue_DefaultRole",
            Command={
                "Name": "glueetl",
                "ScriptLocation": "s3://my_script_bucket/scripts/my_etl_script.py",
            },
        )

        mock_params = {
            "test_configs": test_configs,
            "is_mock_amc_response": False,
            "mock_amc_path": None,
            "mock_amc_response": None,
            "mock_http_method": None,
        }

        @contextlib.contextmanager
        def start_amc_transformation_api(user_id):
            with Client(app.app) as client:
                response = client.http.post(
                    "/start_amc_transformation",
                    headers=get_headers,
                    body=json.dumps(
                        {
                            "sourceBucket": test_configs["s3bucket"],
                            "sourceKey": test_configs["source_key"],
                            "outputBucket": test_configs["outputBucket"],
                            "piiFields": '[{"column_name":"first_name","pii_type":"FIRST_NAME"},{"column_name":"last_name","pii_type":"LAST_NAME"},{"column_name":"email","pii_type":"EMAIL"}]',
                            "deletedFields": "[]",
                            "timestampColumn": "timestamp",
                            "datasetId": test_configs["data_set_id"],
                            "fileFormat": "JSON",
                            "period": test_configs["period"],
                            "countryCode": "USA",
                            "updateStrategy": "ADDITIVE",
                            "user_id": user_id,
                            "state": test_configs["state"],
                            "amc_instances": json.dumps(
                                [{"instance_id": test_configs["instance_id"]}]
                            ),
                        }
                    ),
                )

                yield response

        def test_response(response):
            assert response.status_code == 200
            assert response.json_body["JobRunId"]
            glue_resp = glue_client.get_job_run(
                JobName=os.environ["AMC_GLUE_JOB_NAME"],
                RunId=response.json_body["JobRunId"],
            )
            assert glue_resp["JobRun"]["Id"] == response.json_body["JobRunId"]

        run_amc_api_request_test(
            api_client=start_amc_transformation_api,
            mock_params=mock_params,
            test_response=test_response,
        )

@mock_aws
def test_system_configuration(test_configs, get_amc_instance_info):
    content_type = test_configs["content_type"]

    s3 = boto3.client("s3", region_name="us-east-1")

    s3.create_bucket(Bucket=test_configs["s3_artifact_bucket"])
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3_object = s3.Object(
        test_configs["s3_artifact_bucket"], test_configs["source_key"]
    )
    s3_object.put(Body="{}", ContentType=content_type)

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Some Bucket Policy",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": f'arn:aws:s3:::{test_configs["s3_artifact_bucket"]}/*',
            }
        ],
    }

    # Convert the policy from JSON dict to string
    bucket_policy = json.dumps(bucket_policy)
    s3 = boto3.client("s3")
    s3.put_bucket_policy(
        Bucket=test_configs["s3_artifact_bucket"], Policy=bucket_policy
    )

    dynamodb = boto3.client(
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
    dynamodb.create_table(**params)

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/system/configuration",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "Name": "AmcInstances",
                    "Value": [
                        {
                            "data_upload_account_id": test_configs[
                                "data_upload_account_id"
                            ],
                            "tag_list": "testCom, test_tester",
                            "tags": [
                                {"value": "testCom", "key": ""},
                                {"value": "test_tester", "key": ""},
                            ],
                            **get_amc_instance_info,
                        }
                    ],
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {}

    with Client(app.app) as client:
        response = client.http.get(
            "/system/configuration",
            headers={"Content-Type": content_type},
        )

        assert response.status_code == 200
        assert response.json_body[0]["Name"] == "AmcInstances"
        assert (
            response.json_body[0]["Value"][0]["data_upload_account_id"]
            == test_configs["data_upload_account_id"]
        )
        assert (
            response.json_body[0]["Value"][0]["instance_id"]
            == test_configs["instance_id"]
        )
        assert (
            response.json_body[0]["Value"][0]["advertiser_id"]
            == test_configs["advertiser_id"]
        )
        assert (
            response.json_body[0]["Value"][0]["marketplace_id"]
            == test_configs["marketplace_id"]
        )
        assert response.json_body[0]["Value"][0]["tag_list"] is not None
        assert response.json_body[0]["Value"][0]["tags"] is not None


@mock_aws
def test_describe_secret(test_configs):
    user_id = "user_12345"
    secret_id = f"{test_configs['stack_name']}-{user_id}"
    session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
    client = session.client("secretsmanager")
    client.create_secret(
        Name=secret_id,
        SecretString=json.dumps(
            {
                "client_id": test_configs["client_id"],
                "client_secret": test_configs["client_secret"],
            }
        ),
    )
    with Client(app.app) as client_web:
        response = client_web.http.post(
            "/describe_secret",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps(
                {
                    "user_id": user_id,
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {"secret_string_keys":["client_id", "client_secret"]}

    res = client.get_secret_value(
        SecretId=secret_id,
    )

    if not res.get("SecretString"):
        raise AssertionError("/reset_token failed.")
    else:
        secret_object = json.loads(res["SecretString"])
        secret_object["refresh_token"] = "TOKEN_DELETED"


@mock_aws
def test_validate_amc_request(test_configs, get_headers):
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

        # Validate that unauthorized requests return an authorize_url
        with Client(app.app) as client_web:
            response = client_web.http.post(
                "/validate_amc_request",
                headers=get_headers,
                body=json.dumps(
                    {
                        "user_id": user_id,
                        "auth_code": None,
                        "state": test_configs["state"],
                    }
                ),
            )
            assert response.status_code == 200
            assert (
                response.json_body["authorize_url"]
                == f"https://www.amazon.com/ap/oa?client_id={test_configs['client_id']}&scope={test_configs['ads_scope']}&response_type=code&redirect_uri={test_configs['redirect_uri']}/redirect&state={test_configs['state']}"
            )

        # Validate the functionality of an authorized request
        refresh_token = f"refresh-token-{uuid.uuid4()}"
        access_token = f"access_token-{uuid.uuid4()}"
        redirect_uri = f"{test_configs['redirect_uri']}/redirect"
        auth_code = "ANtnblrzQXgrhnyJlWmV"
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
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": redirect_uri,
                        "client_id": test_configs["client_id"],
                        "client_secret": test_configs["client_secret"],
                    }
                ),
                matchers.header_matcher({}),
            ],
        )
        with Client(app.app) as client_web:
            response = client_web.http.post(
                "/validate_amc_request",
                headers=get_headers,
                body=json.dumps({"user_id": user_id, "auth_code": auth_code}),
            )
            assert response.status_code == 200
            assert response.json_body["refresh_token"] == refresh_token
            assert response.json_body["access_token"] == access_token
            assert response.json_body["client_id"] == test_configs["client_id"]

            res = client.get_secret_value(
                SecretId=secret_id,
            )

            if not res.get("SecretString"):
                raise AssertionError("/validate_amc_request failed.")
            else:
                secret_object = json.loads(res["SecretString"])
                secret_object["refresh_token"] = refresh_token
                secret_object["client_id"] = test_configs["client_id"]
                secret_object["client_secret"] = test_configs["client_secret"]


@mock_aws
def test_get_amc_instances(
    test_configs, get_headers, run_amc_api_request_test
):
    expected_amc_response = {
        "instances": [
            {
                "instanceId": test_configs["instance_id"],
                "dataUploadAwsAccountId": test_configs[
                    "data_upload_account_id"
                ],
                "creationStatus": "COMPLETED",
                "creationDatetime": "2022-06-08T23:53:03.974Z",
                "s3BucketName": "amc-123467",
                "awsAccountId": test_configs["aws_account_id"],
            }
        ],
    }

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": "/amc/instances",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "GET",
        "is_amc_report": False,
    }

    @contextlib.contextmanager
    def get_amc_instances_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/get_amc_instances",
                headers=get_headers,
                body=json.dumps(
                    {
                        "user_id": user_id,
                        "advertiser_id": test_configs["advertiser_id"],
                        "marketplace_id": test_configs["marketplace_id"],
                        "state": test_configs["state"],
                    }
                ),
            )
            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    run_amc_api_request_test(
        api_client=get_amc_instances_api,
        mock_params=mock_params,
        test_response=test_response,
    )


@mock_aws
def test_get_amc_accounts(test_configs, get_headers, run_amc_api_request_test):
    expected_amc_response = {
        "amcAccounts": [
            {
                "accountId": test_configs["advertiser_id"],
                "accountName": "AMC Test Account",
                "marketplaceId": test_configs["marketplace_id"],
            }
        ]
    }

    mock_params = {
        "test_configs": test_configs,
        "mock_amc_path": "/amc/accounts",
        "mock_amc_response": expected_amc_response,
        "mock_http_method": "GET",
        "is_amc_report": False,
        "override_match_amc_req_headers": {
            "Amazon-Advertising-API-ClientId": test_configs["client_id"],
            "Content-Type": "application/json",
        },
    }

    @contextlib.contextmanager
    def get_amc_accounts_api(user_id):
        with Client(app.app) as client:
            response = client.http.post(
                "/get_amc_accounts",
                headers=get_headers,
                body=json.dumps(
                    {
                        "user_id": user_id,
                        "state": test_configs["state"],
                    }
                ),
            )
            yield response

    def test_response(response):
        assert response.status_code == 200
        assert response.json_body == expected_amc_response

    run_amc_api_request_test(
        api_client=get_amc_accounts_api,
        mock_params=mock_params,
        test_response=test_response,
    )


def test_log_request_parameters():
    
    request_id = str(uuid.uuid4())
    mock_current_request = MagicMock(
        context={
            "requestId": request_id,
            "resourcePath": "some/resource/path"
        },
        method="GET",
        uri_params={"some": "uri-params"},
        query_params={"some": "query-params"},
    )

    with (
        patch("api.app.app", MagicMock(current_request=mock_current_request)) as mock_app,
        patch("api.app.logger", MagicMock()) as mock_logger
    ):
        from api.app import log_request_parameters
        log_request_parameters()

        mock_logger.info.assert_any_call("Processing the following request:\n")
        mock_logger.info.assert_any_call(
            "resource path: " + mock_app.current_request.context["resourcePath"]
        )
        mock_logger.info.assert_any_call("method: " + mock_app.current_request.method)
        mock_logger.info.assert_any_call("uri parameters: " + str(mock_app.current_request.uri_params))
        mock_logger.info.assert_any_call("query parameters: " + str(mock_app.current_request.query_params))
        mock_logger.info.assert_any_call("request body: " + mock_app.current_request.raw_body.decode())
        mock_logger.debug.assert_any_call(mock_app.current_request.to_dict())

        with pytest.raises(AssertionError):
            # check if request ID is in the log with .info calls.
            mock_logger.info.assert_any_call(
                "request ID: " + (mock_app.current_request.context.get("requestId", ""))
            )

        mock_logger.debug.assert_any_call(
            "request ID: " + (mock_app.current_request.context.get("requestId", ""))
        )
        # check if request ID is in any .info calls.
        assert len([item for item in mock_logger.info.mock_calls if request_id in str(item)]) == 0
