# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Unit test for project api endpoints and workflow.
#
# USAGE:
#   ./run_test.sh --run_unit_test
###############################################################################

import json
import os
from unittest.mock import MagicMock, patch

import app
import boto3
import pytest
from chalice.test import Client
from moto import mock_dynamodb, mock_glue, mock_iam, mock_s3, mock_sts


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
        "destination_endpoint": "https://example123.execute-api.us-east-1.amazonaws.com/prod/",
        "amc_endpoint": "https://test-endpoint.test/beta",
        "data_upload_account_id": "123456789012",
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


def test_version(test_configs):
    with Client(app.app) as client:
        response = client.http.get(
            "/version",
            headers={"Content-Type": test_configs["content_type"]},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]


def test_list_bucket(test_configs):
    with mock_s3():
        s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        s3.create_bucket(Bucket=test_configs["s3bucket"])
        s3 = boto3.resource("s3")
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


def test_get_data_columns(test_configs, get_amc_json, test_data):
    content_type = test_configs["content_type"]
    with mock_s3():
        s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        s3.create_bucket(Bucket=test_configs["s3bucket"])
        s3 = boto3.resource("s3")
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
                    }
                ),
            )
            assert response.status_code == 200
            assert response.json_body["columns"] is not None
            for expected_key in list(test_data[0].keys()):
                assert expected_key in response.json_body["columns"]


@mock_sts
@patch("chalicelib.sigv4.sigv4.requests.Session")
def test_delete_dataset(mock_session_response, test_configs):
    mock_session_response.mount = MagicMock()
    mock_session_response.return_value.delete.return_value = MagicMock(
        status_code=200, text="{}"
    )

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/delete_dataset",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "destination_endpoint": test_configs[
                        "destination_endpoint"
                    ],
                    "dataSetId": test_configs["data_set_id"],
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {}


@mock_sts
@patch("chalicelib.sigv4.sigv4.requests.Session")
def test_list_datasets(mock_session_response, test_configs):
    mock_session_response.mount = MagicMock()
    test_body = {
                    "destination_endpoint": test_configs[
                        "destination_endpoint"
                    ],
                }
    expected_response = {
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
          "requiresOneWayHashing": False
        },
        {
          "dataType": "STRING",
          "description": "The customer resolved type",
          "isMainEventTime": False,
          "isMainUserId": False,
          "isMainUserIdType": True,
          "isNullable": True,
          "name": "user_type",
          "requiresOneWayHashing": False
        },
        {
          "dataType": "STRING",
          "description": "hashed First name",
          "externalUserIdType": {
            "type": "HashedIdentifier",
            "identifierType": "FIRST_NAME"
          },
          "isMainEventTime": False,
          "isMainUserId": False,
          "isMainUserIdType": False,
          "isNullable": True,
          "name": "first_name",
          "requiresOneWayHashing": False
        },
        {
          "dataType": "STRING",
          "description": "hashed Last name",
          "externalUserIdType": {
            "type": "HashedIdentifier",
            "identifierType": "LAST_NAME"
          },
          "isMainEventTime": False,
          "isMainUserId": False,
          "isMainUserIdType": False,
          "isNullable": True,
          "name": "last_name",
          "requiresOneWayHashing": False
        },
        {
          "dataType": "TIMESTAMP",
          "description": "Timestamp",
          "isMainEventTime": True,
          "isMainUserId": False,
          "isMainUserIdType": False,
          "isNullable": False,
          "name": "timestamp",
          "requiresOneWayHashing": False
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
          "requiresOneWayHashing": False
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
          "requiresOneWayHashing": False
        }
      ],
      "compressionFormat": "GZIP",
      "createdTime": "2023-03-14T20:39:19.043Z",
      "dataSetId": "iantest12",
      "dataSetType": "FACT",
      "fileFormat": "JSON",
      "owner": "CUSTOMER",
      "period": "P1D",
      "updatedTime": "2023-03-14T20:39:19.043Z"
    },
  ]
    }
    mock_session_response.return_value.get.return_value = MagicMock(
        status_code=200, text=json.dumps(expected_response)
    )

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/list_datasets",
            headers={"Content-Type": content_type},
            body=json.dumps(
                test_body
            ),
        )
        assert response.status_code == 200
        assert response.json_body == expected_response


@mock_sts
@patch("chalicelib.sigv4.sigv4.requests.Session")
def test_describe_dataset(mock_session_response, test_configs):
    mock_session_response.mount = MagicMock()
    test_body = {
                    "destination_endpoint": test_configs[
                        "destination_endpoint"
                    ],
                    "dataSetId": test_configs["data_set_id"],
                }
    expected_response = {
        "columns": [
            {
            "dataType": "STRING",
            "description": "The customer resolved id",
            "isMainEventTime": False,
            "isMainUserId": True,
            "isMainUserIdType": False,
            "isNullable": True,
            "name": "user_id",
            "requiresOneWayHashing": False
            },
            {
            "dataType": "STRING",
            "description": "The customer resolved type",
            "isMainEventTime": False,
            "isMainUserId": False,
            "isMainUserIdType": True,
            "isNullable": True,
            "name": "user_type",
            "requiresOneWayHashing": False
            },
            {
            "dataType": "STRING",
            "description": "hashed First name",
            "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": "FIRST_NAME"
            },
            "isMainEventTime": False,
            "isMainUserId": False,
            "isMainUserIdType": False,
            "isNullable": True,
            "name": "first_name",
            "requiresOneWayHashing": False
            },
            {
            "dataType": "STRING",
            "description": "hashed Last name",
            "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": "LAST_NAME"
            },
            "isMainEventTime": False,
            "isMainUserId": False,
            "isMainUserIdType": False,
            "isNullable": True,
            "name": "last_name",
            "requiresOneWayHashing": False
            },
            {
            "dataType": "STRING",
            "description": "hashed Email",
            "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": "EMAIL"
            },
            "isMainEventTime": False,
            "isMainUserId": False,
            "isMainUserIdType": False,
            "isNullable": True,
            "name": "email",
            "requiresOneWayHashing": False
            },
            {
            "dataType": "STRING",
            "description": "Product quantity",
            "externalUserIdType": {
                "type": "LiveRamp"
            },
            "isMainEventTime": False,
            "isMainUserId": False,
            "isMainUserIdType": False,
            "isNullable": False,
            "name": "product_quantity",
            "requiresOneWayHashing": False
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
            "requiresOneWayHashing": False
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
            "requiresOneWayHashing": False
            }
        ],
        "compressionFormat": "GZIP",
        "createdTime": "2023-03-22T19:26:35.034Z",
        "dataSetId": "imgeo-normal",
        "dataSetType": "DIMENSION",
        "fileFormat": "JSON",
        "owner": "CUSTOMER",
        "period": "P1D",
        "updatedTime": "2023-03-22T19:26:35.034Z"
        }
    mock_session_response.return_value.get.return_value = MagicMock(
        status_code=200, text=json.dumps(expected_response)
    )

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/describe_dataset",
            headers={"Content-Type": content_type},
            body=json.dumps(
                test_body
            ),
        )
        assert response.status_code == 200
        assert response.json_body == expected_response


@mock_sts
@patch("chalicelib.sigv4.sigv4.requests.Session")
def test_upload_status(mock_session_response, test_configs):
    expected_data = {
        "sourceS3Bucket": "some_bucket",
        "sourceFileS3Key": "some_key",
        "status": ["Succeeded"],
    }
    mock_session_response.mount = MagicMock()
    mock_session_response.return_value.get.return_value = MagicMock(
        status_code=200, text=json.dumps(expected_data)
    )

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/upload_status",
            headers={"Content-Type": content_type},
            body=json.dumps(
                {
                    "destination_endpoint": test_configs[
                        "destination_endpoint"
                    ],
                    "dataSetId": test_configs["data_set_id"],
                    "uploadId": "123456",
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == expected_data


def test_get_etl_jobs(test_configs):
    content_type = test_configs["content_type"]
    with mock_glue():
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


@mock_sts
@patch("chalicelib.sigv4.sigv4.requests.post")
def test_create_dataset(mock_response, test_configs):
    payload = {
        "destination_endpoint": test_configs["destination_endpoint"],
        "body": {
            "period": "autodetect",
            "dataSetId": test_configs["data_set_id"],
            "dataSetType": "DIMENSION",
            "compressionFormat": "GZIP",
            "columns": [],
        },
    }
    mock_response.return_value = MagicMock(
        status_code=200, text="{}", data=payload
    )

    content_type = test_configs["content_type"]
    with Client(app.app) as client:
        response = client.http.post(
            "/create_dataset",
            headers={"Content-Type": content_type},
            body=json.dumps(payload),
        )
        assert response.status_code == 200
        assert response.json_body == {}


@mock_sts
def test_start_amc_transformation(test_configs):
    with mock_glue():
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

        content_type = test_configs["content_type"]
        with Client(app.app) as client:
            response = client.http.post(
                "/start_amc_transformation",
                headers={"Content-Type": content_type},
                body=json.dumps(
                    {
                        "sourceBucket": test_configs["s3bucket"],
                        "sourceKey": test_configs["source_key"],
                        "outputBucket": test_configs["outputBucket"],
                        "piiFields": '[{"column_name":"first_name","pii_type":"FIRST_NAME"},{"column_name":"last_name","pii_type":"LAST_NAME"},{"column_name":"email","pii_type":"EMAIL"}]',
                        "deletedFields": "[]",
                        "timestampColumn": "timestamp",
                        "datasetId": test_configs["data_set_id"],
                        "period": test_configs["period"],
                        "countryCode": "USA",
                        "destination_endpoints": test_configs[
                            "destination_endpoint"
                        ],
                    }
                ),
            )
            assert response.status_code == 200
            assert response.json_body["JobRunId"]
            glue_resp = glue_client.get_job_run(
                JobName=os.environ["AMC_GLUE_JOB_NAME"],
                RunId=response.json_body["JobRunId"],
            )
            assert glue_resp["JobRun"]["Id"] == response.json_body["JobRunId"]


@patch("chalicelib.sigv4.sigv4.requests.post")
def test_system_configuration(mock_response, test_configs):
    with mock_iam(), mock_s3(), mock_dynamodb():
        content_type = test_configs["content_type"]

        iam = boto3.client("iam", region_name=os.environ["AWS_REGION"])
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AmcEndpointAccessPolicy",
                    "Action": ["execute-api:Invoke"],
                    "Resource": ["arn:aws:execute-api:*:*:test/*"],
                    "Effect": "Allow",
                }
            ],
        }
        policy_name = "AmcApiAccess"
        role_name = test_configs["amc_role"].split("/")[1]
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=policy_name,
        )
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_doc),
        )

        s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])

        s3.create_bucket(Bucket=test_configs["s3_artifact_bucket"])
        s3 = boto3.resource("s3")
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
                                "endpoint": test_configs["amc_endpoint"],
                                "tag_list": "testCom, test_tester",
                                "tags": [
                                    {"value": "testCom", "key": ""},
                                    {"value": "test_tester", "key": ""},
                                ],
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
                response.json_body[0]["Value"][0]["endpoint"]
                == test_configs["amc_endpoint"]
            )
            assert response.json_body[0]["Value"][0]["tag_list"] is not None
            assert response.json_body[0]["Value"][0]["tags"] is not None
