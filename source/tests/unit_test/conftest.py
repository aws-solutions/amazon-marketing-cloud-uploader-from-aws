# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "123456789"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "987654321"
    os.environ["AWS_SECURITY_TOKEN"] = "test_securitytoken"
    os.environ["AWS_SESSION_TOKEN"] = "test_session_token"
    os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
    os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]
