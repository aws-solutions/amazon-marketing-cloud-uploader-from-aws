# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import os


@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["AMC_ENDPOINT_URL"] = "AmcEndpointUrl"
    os.environ["AMC_API_ROLE_ARN"] = "AmcApiRoleArn"
    os.environ["botoConfig"] = '{"region_name": "us-east-1"}'

def test_is_valid_email_address():
    from glue.normalizers.email_normalizer import isValidEmailAddress

    assert isValidEmailAddress("test@test.com") is True
    assert isValidEmailAddress("this is an invalid email") is False

def test_email_normalizer():
    from glue.normalizers.email_normalizer import EmailNormalizer

    email_normalizer = EmailNormalizer("test@test.com")
    assert email_normalizer.normalize() == "test@test.com"

    email_normalizer = EmailNormalizer("this is an invalid email")
    assert email_normalizer.normalize() == ""

    email_normalizer = EmailNormalizer("not.an_e-mail")
    assert email_normalizer.normalize() == ""

    email_normalizer = EmailNormalizer("te$s-t@te^st.c()om")
    assert email_normalizer.normalize() == "tes-t@test.com"

    email_normalizer = EmailNormalizer("te-st@tEsT.CoM")
    assert email_normalizer.normalize() == "te-st@test.com"
