# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import pytest


@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["AMC_ENDPOINT_URL"] = "AmcEndpointUrl"
    os.environ["AMC_API_ROLE_ARN"] = "AmcApiRoleArn"
    os.environ["botoConfig"] = '{"region_name": "us-east-1"}'
    os.environ["SOLUTION_VERSION"] = "0.0.0"
    os.environ["SOLUTION_NAME"] = "amc_test"


def test_is_dataset(mock_env_variables):
    from amc_uploader.amc_uploader import _is_dataset

    assert _is_dataset("text.gz") is True
    assert _is_dataset("text.zip") is False


def test_is_timeseries(mock_env_variables):
    from amc_uploader.amc_uploader import _is_timeseries

    assert (
        _is_timeseries("amc/dataset_id/timeseries_partition_size/filename")
        is False
    )
    assert _is_timeseries("amc/dataset_id/PT1M/filename") is True
    assert _is_timeseries("amc/dataset_id/PT1H/filename") is True
    assert _is_timeseries("amc/dataset_id/P1D/filename") is True
    assert _is_timeseries("amc/dataset_id/P7D/filename") is True
