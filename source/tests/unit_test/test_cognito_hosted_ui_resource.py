# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Regression test for cognito_hosted_ui_resource/.
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name test_cognito_hosted_ui_resource.py
###############################################################################

import os
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_variable():
    os.environ["USER_POOL_ID"] = "123456"


@patch("cognito_hosted_ui_resource.cognito_hosted_ui_resource.boto3.client")
@patch("cognito_hosted_ui_resource.cognito_hosted_ui_resource.cfnresponse")
def test_handler(mock_cfnresponse, mock_boto3_client, mock_env_variable):

    from cognito_hosted_ui_resource.cognito_hosted_ui_resource import handler, get_file, DIR_PATH

    handler({}, None)
    expected_test_args = {
        "UserPoolId": os.environ["USER_POOL_ID"],
        "CSS": get_file(f"{DIR_PATH}/login.css", "r"),
        "ImageFile": get_file(f"{DIR_PATH}/amcufa-logo.png", "rb")
    }
    mock_boto3_client.assert_called_once_with("cognito-idp")
    mock_boto3_client("cognito-idp").set_ui_customization.assert_called_once_with(**expected_test_args)
    mock_cfnresponse.send.assert_called_once_with({}, None, mock_cfnresponse.SUCCESS, {"response": mock_boto3_client("cognito-idp").set_ui_customization(**expected_test_args)})