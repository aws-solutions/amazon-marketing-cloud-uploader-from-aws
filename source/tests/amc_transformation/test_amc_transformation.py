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

## TEST NORMALIZERS ##
# US
def test_US_address_normalizer():
    from glue.normalizers.address_normalizer import AddressNormalizer
    address_normalizer = AddressNormalizer("US")

    test = address_normalizer.normalize("8 Bluestem Terrace")
    assert test.normalizedAddress == "8bluestemter"

    test = address_normalizer.normalize("75012 TEXAS CENTER")
    assert test.normalizedAddress == "75012texasctr"

    test = address_normalizer.normalize("3932 new castle street")
    assert test.normalizedAddress == "3932newcastlest"
    
    test = address_normalizer.normalize("e&*3E[]%^&$#@!><.,Mf0-/\}{_")
    assert test.normalizedAddress == "e&*3e%^&$#@><.mf0-/\_"

def test_US_phone_normalizer():
    from glue.normalizers.phone_normalizer import PhoneNormalizer
    phone_normalizer = PhoneNormalizer("US")

    test = phone_normalizer.normalize("5714120599")
    assert test.normalizedPhone == "15714120599"
    
    test = phone_normalizer.normalize("571-981-5803")
    assert test.normalizedPhone == "15719815803"

    test = phone_normalizer.normalize("+1 (413) 871-4499")
    assert test.normalizedPhone == "14138714499"

    test = phone_normalizer.normalize("(916) 3979206")
    assert test.normalizedPhone == "19163979206"

    test = phone_normalizer.normalize("+1 818 456 6629")
    assert test.normalizedPhone == "18184566629"

    test = phone_normalizer.normalize("1(612)392-8346")
    assert test.normalizedPhone == "16123928346"

    test = phone_normalizer.normalize("invalid phone")
    assert test.normalizedPhone == ""

    test = phone_normalizer.normalize("1")
    assert test.normalizedPhone == ""

    test = phone_normalizer.normalize("123456789123456789")
    assert test.normalizedPhone == ""

def test_US_state_normalizer():
    from glue.normalizers.state_normalizer import StateNormalizer
    state_normalizer = StateNormalizer("US")

    test = state_normalizer.normalize("Texas")
    assert test.normalizedState == "TX"

    test = state_normalizer.normalize("fl")
    assert test.normalizedState == "FL"

    test = state_normalizer.normalize("VIRGINIA")
    assert test.normalizedState == "VA"

    test = state_normalizer.normalize("NM")
    assert test.normalizedState == "NM"

    test = state_normalizer.normalize("NewYork")
    assert test.normalizedState == "NY"

    test = state_normalizer.normalize("State")
    assert test.normalizedState == "ST"

    test = state_normalizer.normalize("S")
    assert test.normalizedState == "S"

    test = state_normalizer.normalize(">$%&*")
    assert test.normalizedState == ""

    test = state_normalizer.normalize("123456")
    assert test.normalizedState == ""

def test_US_zip_normalizer():
    from glue.normalizers.zip_normalizer import ZipNormalizer
    zip_normalizer = ZipNormalizer("US")

    test = zip_normalizer.normalize("75236-9599")
    assert test.normalizedZip == "75236"

    test = zip_normalizer.normalize("67236")
    assert test.normalizedZip == "67236"

    test = zip_normalizer.normalize(">$%&*67236")
    assert test.normalizedZip == "67236"

    test = zip_normalizer.normalize("123456789123456789")
    assert test.normalizedZip == "12345"

    test = zip_normalizer.normalize("1")
    assert test.normalizedZip == ""
    
    test = zip_normalizer.normalize("zip")
    assert test.normalizedZip == ""

    test = zip_normalizer.normalize(">$%&*")
    assert test.normalizedZip == ""
    