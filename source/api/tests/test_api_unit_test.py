# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Unit test for project api endpoints and workflow.
#
# USAGE:
#   ./run_api_test.sh --run_unit_test
###############################################################################

import os
import pytest
import json
from unittest.mock import patch, MagicMock
from moto import mock_s3, mock_sts, mock_glue
import boto3
import app
from chalice.test import Client


@pytest.fixture
def test_configs():
    return {
        "s3bucket": "fake_s3_bucket",
        "outputBucket": "fake_output_bucket",
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


def test_version():
    with Client(app.app) as client:
        response = client.http.get(
            "/version",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]


def test_list_bucket(test_configs):
    content_type = "application/json"
    with mock_s3():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=test_configs["s3bucket"])
        s3 = boto3.resource("s3")
        s3_object = s3.Object(test_configs["s3bucket"], "some_file.json")
        s3_object.put(Body="{}", ContentType=content_type)

        with Client(app.app) as client:
            response = client.http.post(
                "/list_bucket",
                headers={"Content-Type": content_type},
                body=json.dumps({"s3bucket": test_configs["s3bucket"]}),
            )
            assert response.status_code == 200
            assert response.json_body[0]["key"] == 'some_file.json'
            assert response.json_body[0]["size"] == 2


def test_get_data_columns(test_configs, get_amc_json, test_data):
    content_type = "application/json"
    with mock_s3():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=test_configs["s3bucket"])
        s3 = boto3.resource("s3")
        s3_object = s3.Object(test_configs["s3bucket"], "some_file.json")
        s3_object.put(Body=get_amc_json, ContentType=content_type)

        with Client(app.app) as client:
            response = client.http.post(
                "/get_data_columns",
                headers={"Content-Type": content_type},
                body=json.dumps({"s3bucket": test_configs["s3bucket"], "s3key": "some_file.json"}),
            )
            assert response.status_code == 200
            assert response.json_body["columns"] is not None
            for expected_key in list(test_data[0].keys()):
                assert expected_key in response.json_body["columns"]


@mock_sts
@patch('chalicelib.sigv4.requests.delete')
def test_delete_dataset(mock_delete_response):
    mock_delete_response.return_value = MagicMock(status_code=200, text="{}")

    content_type = "application/json"
    with Client(app.app) as client:
        response = client.http.post(
            "/delete_dataset",
            headers={"Content-Type": content_type},
            body=json.dumps({"dataSetId": "test_data_set_id"}),
        )
        assert response.status_code == 200
        assert response.json_body == {}


@mock_sts
@patch('chalicelib.sigv4.requests.get')
def test_upload_status(mock_delete_response):
    expected_data = {
        "sourceS3Bucket": "some_bucket",
        "sourceFileS3Key": "some_key",
        "status": ["Succeeded"]
    }
    mock_delete_response.return_value = MagicMock(status_code=200, text=json.dumps(expected_data))

    content_type = "application/json"
    with Client(app.app) as client:
        response = client.http.post(
            "/upload_status",
            headers={"Content-Type": content_type},
            body=json.dumps({"dataSetId": "test_data_set_id", "uploadId": "123456"}),
        )
        assert response.status_code == 200
        assert response.json_body == expected_data


def test_get_etl_jobs():
    content_type = "application/json"
    with mock_glue():
        data_set_id = "some_data_test_id"
        solution_config = json.loads(os.environ["botoConfig"])
        from botocore import config
        config = config.Config(**solution_config)
        glue_client = boto3.client("glue", config=config)
       
        glue_client.create_job(Name=os.environ["AMC_GLUE_JOB_NAME"], Role='Glue_DefaultRole', Command={'Name': 'glueetl',
                               'ScriptLocation': 's3://my_script_bucket/scripts/my_etl_script.py'})
        glue_response = glue_client.start_job_run(JobName=os.environ["AMC_GLUE_JOB_NAME"], Arguments = {"--dataset_id": data_set_id})
        job_run_data = glue_client.get_job_run(JobName=os.environ["AMC_GLUE_JOB_NAME"], RunId=glue_response["JobRunId"])
        with patch('app.boto3.client') as mock_get_job_runs:
            job_run_data["JobRun"]["Arguments"].update(
                {"--dataset_id": data_set_id}
            )
            job_runs_data = {
                "JobRuns": [job_run_data["JobRun"]]
            }
            mock_get_job_runs.return_value.get_job_runs.return_value = job_runs_data
            with Client(app.app) as client:
                response = client.http.get(
                    "/get_etl_jobs",
                    headers={"Content-Type": content_type},
                )
                assert response.status_code == 200
                assert data_set_id == response.json_body["JobRuns"][0].pop("DatasetId")
                assert response.json_body["JobRuns"] == json.loads(json.dumps(job_runs_data["JobRuns"], default=str))
       
    