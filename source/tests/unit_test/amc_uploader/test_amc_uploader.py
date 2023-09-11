# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# ###############################################################################
# PURPOSE:
#   * Regression test for amc_uploader.
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name amc_uploader/test_amc_uploader.py
###############################################################################

import json
from unittest.mock import MagicMock, patch
import os
import boto3
import pytest
from moto import mock_sts, mock_dynamodb

BASE64_ENCODED_AMC_ENDPOINT = "aHR0cHM6Ly9hYmNkZTEyMzQ1LmV4ZWN1dGUtYXBpLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3Byb2Q="


@pytest.fixture
def test_configs():
    return {
        "s3_bucket": "fake_s3_bucket",
        "s3_fact_key": "amc/dataset_id/PT1M/"
        + BASE64_ENCODED_AMC_ENDPOINT
        + "/etl_output_data.json-2022_01_06-09:01:00.gz",
        "s3_fact_key2": "amc/dataset_id/PT1M/"
        + BASE64_ENCODED_AMC_ENDPOINT
        + "/invalid_filename",
        "s3_fact_key3": "amc/dataset_id/P1D/"
        + BASE64_ENCODED_AMC_ENDPOINT
        + "/etl_output_data.json-2022_01_06-09:01:00.gz",
        "s3_dimension_key": "amc/dataset_id/dimension/"
        + BASE64_ENCODED_AMC_ENDPOINT
        + "/filename.gz",
    }


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


def test_is_dataset():
    from amc_uploader.amc_uploader import _is_dataset

    assert _is_dataset("text.gz") is True
    assert _is_dataset("text.zip") is False


def test_is_timeseries():
    from amc_uploader.amc_uploader import _is_timeseries

    assert (
        _is_timeseries(
            "amc/dataset_id/timeseries_partition_size/"
            + BASE64_ENCODED_AMC_ENDPOINT
            + "/filename"
        )
        is False
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/PT1M/" + BASE64_ENCODED_AMC_ENDPOINT + "/filename"
        )
        is True
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/PT1H/" + BASE64_ENCODED_AMC_ENDPOINT + "/filename"
        )
        is True
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/P1D/" + BASE64_ENCODED_AMC_ENDPOINT + "/filename"
        )
        is True
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/P7D/" + BASE64_ENCODED_AMC_ENDPOINT + "/filename"
        )
        is True
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/P7D/"
            + BASE64_ENCODED_AMC_ENDPOINT
            + "/etl_output_data.json-2022_01_06-09:01:00"
        )
        is True
    )
    assert (
        _is_timeseries(
            "amc/dataset_id/"
            + BASE64_ENCODED_AMC_ENDPOINT
            + "etl_output_data.json-2022_01_06-09:01:00"
        )
        is False
    )


@patch("amc_uploader.amc_uploader._start_dimension_upload")
def test_lambda_handler_dimension(
    mock_start_dimension, fake_event, fake_context, test_configs
):
    mock_start_dimension.return_value = {}
    from amc_uploader.amc_uploader import lambda_handler

    fake_event["Records"][0]["s3"].update(
        {"object": {"key": test_configs["s3_dimension_key"]}}
    )

    lambda_handler(fake_event, fake_context)
    mock_start_dimension.assert_called_with(
        bucket=test_configs["s3_bucket"],
        key=fake_event["Records"][0]["s3"]["object"]["key"],
    )


@patch("amc_uploader.amc_uploader._start_fact_upload")
def test_lambda_handler_fact(
    mock_start_fact_upload, fake_event, fake_context, test_configs
):
    mock_start_fact_upload.return_value = {}
    from amc_uploader.amc_uploader import lambda_handler

    fake_event["Records"][0]["s3"].update(
        {"object": {"key": test_configs["s3_fact_key"]}}
    )

    lambda_handler(fake_event, fake_context)
    mock_start_fact_upload.assert_called_with(
        bucket=test_configs["s3_bucket"],
        key=fake_event["Records"][0]["s3"]["object"]["key"],
    )


@mock_sts
@patch("amc_uploader.lib.sigv4.sigv4.requests.post")
def test_start_dimension_upload(mock_response_post, test_configs):
    from amc_uploader.amc_uploader import _start_dimension_upload

    expected_data = {"upload": [{"some_upload": "data"}]}

    mock_response_post.return_value = MagicMock(
        status_code=200, text=json.dumps(expected_data)
    )
    assert expected_data == json.loads(
        _start_dimension_upload(
            test_configs["s3_bucket"], test_configs["s3_dimension_key"]
        )
    )


@mock_sts
@mock_dynamodb
@patch("amc_uploader.lib.sigv4.sigv4.requests.put")
@patch("amc_uploader.lib.sigv4.sigv4.requests.post")
@patch("amc_uploader.lib.sigv4.sigv4.requests.Session")
def test_start_fact_upload(
    mock_session_response, mock_response_post, mock_response_put, test_configs
):
    from amc_uploader.amc_uploader import _start_fact_upload

    # The following test exercises the logic for handling invalid filenames.
    # Filenames should look like this, "etl_output_data.json-2022_01_06-09:01:00.gz"
    data = _start_fact_upload(
        test_configs["s3_bucket"], test_configs["s3_fact_key2"]
    )
    assert data["Status"] == "Error"
    assert str(data["Message"]) == "list index out of range"

    # Uploads are performed asynchronously by the amc_uploader.py Lambda function.
    # That function is triggered by S3 when the Glue ETL job saves its results.
    # If an upload fails, then amc_uploader.py saves the error message to DynamoDB
    # so that the front-end can show the error message to the user.
    #
    # The following test exercises that logic by trying to upload a dataset with an
    # invalid time period, called "PT1M_FAIL".
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    params = {
        "TableName": os.environ["UPLOAD_FAILURES_TABLE_NAME"],
        "KeySchema": [
            {"AttributeName": "destination_endpoint", "KeyType": "HASH"},
            {"AttributeName": "dataset_id", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "destination_endpoint", "AttributeType": "S"},
            {"AttributeName": "dataset_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    }
    dynamodb.create_table(**params)
    mock_session_response.mount = MagicMock()
    mock_session_response.return_value.get.return_value = MagicMock(
        status_code=200, text=json.dumps({"period": "PT1M_FAIL"})
    )
    mock_response_put.return_value = MagicMock(
        status_code=200, text=json.dumps("Looks good")
    )
    data = _start_fact_upload(
        test_configs["s3_bucket"], test_configs["s3_fact_key"]
    )
    assert data["Status"] == "Error"
    assert str(data["Message"]) == "Failed to update dataset time period."

    # The following test exercises the logic for uploading a valid dataset.
    mock_session_response.return_value.get.return_value = MagicMock(
        status_code=200, text=json.dumps({"period": "P1D"})
    )
    mock_response_put.return_value = None  # this is not called
    expected_data = {"upload": [{"some_upload": "data"}]}
    mock_response_post.return_value = MagicMock(
        status_code=200, text=json.dumps(expected_data)
    )
    assert expected_data == json.loads(
        _start_fact_upload(
            test_configs["s3_bucket"], test_configs["s3_fact_key3"]
        )
    )

    # The following test exercises the logic for an AMC server error.
    expected_data = {"message": "fake server error"}
    mock_response_post.return_value = MagicMock(
        status_code=500, text=json.dumps(expected_data)
    )
    assert expected_data == json.loads(
        _start_fact_upload(
            test_configs["s3_bucket"], test_configs["s3_fact_key3"]
        )
    )
