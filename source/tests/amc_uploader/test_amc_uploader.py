# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import os

@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["AMC_ENDPOINT_URL"] = "AmcEndpointUrl"
    os.environ["AMC_API_ROLE_ARN"] = "AmcApiRoleArn"
    os.environ["botoConfig"] = '{"region_name": "us-east-1"}'

def test_is_dataset():
    from amc_uploader.amc_uploader import _is_dataset
    assert _is_dataset("text.gz") == True
    assert _is_dataset("text.zip") == False

def test_is_timeseries():
    from amc_uploader.amc_uploader import _is_timeseries
    assert _is_timeseries("amc/dataset_id/timeseries_partition_size/filename") == False
    assert _is_timeseries("amc/dataset_id/PT1M/filename") == True
    assert _is_timeseries("amc/dataset_id/PT1H/filename") == True
    assert _is_timeseries("amc/dataset_id/P1D/filename") == True
    assert _is_timeseries("amc/dataset_id/P7D/filename") == True
