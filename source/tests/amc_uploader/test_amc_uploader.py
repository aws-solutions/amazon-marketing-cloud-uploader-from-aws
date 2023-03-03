# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# ###############################################################################
# PURPOSE:
#   * Regression test for amc_uploader.
# USAGE:
#   ./run_test.sh --run_unit_test
###############################################################################

import json
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_sts

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
        + "/filename",
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
@patch("amc_uploader.lib.sigv4.requests.post")
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
@patch("amc_uploader.lib.sigv4.requests.put")
@patch("amc_uploader.lib.sigv4.requests.post")
@patch("amc_uploader.lib.sigv4.requests.get")
def test_start_fact_upload(
    mock_response_get, mock_response_post, mock_response_put, test_configs
):
    from amc_uploader.amc_uploader import _start_fact_upload

    mock_response_get.return_value = MagicMock(
        status_code=200, text=json.dumps({"period": "PT1M_FAIL"})
    )
    mock_response_put.return_value = None  # this is not called

    # test invalid file names
    # Filenames should look like this, "etl_output_data.json-2022_01_06-09:01:00.gz"
    data = _start_fact_upload(
        test_configs["s3_bucket"], test_configs["s3_fact_key2"]
    )
    assert data["Status"] == "Error"
    assert str(data["Message"]) == "list index out of range"

    mock_response_get.return_value = MagicMock(
        status_code=200, text=json.dumps({"period": "PT1M_FAIL"})
    )
    mock_response_put.return_value = MagicMock(
        status_code=200, text=json.dumps("Looks good")
    )

    # test invalid dataset time period
    data = _start_fact_upload(
        test_configs["s3_bucket"], test_configs["s3_fact_key"]
    )
    assert data["Status"] == "Error"
    assert str(data["Message"]) == "Failed to update dataset time period."

    mock_response_get.return_value = MagicMock(
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
