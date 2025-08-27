# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Integration test for project api endpoints and workflow.
#
# USAGE:
#   $ ./run_test.sh -run_integ_test
###############################################################################

import datetime
import json
import logging
import os
import time
import random

import app
import boto3
import pandas as pd
import pytest
import requests_mock
from contextlib import contextmanager
from chalice.test import Client

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SKIP_REASON = "Optimize tests to prevent timeouts."
RUN_DEEP_TEST = os.environ.get("DEEP_TEST", False)
TEST_USER_ID = os.environ.get("USER_POOL_ID", f"{os.environ['AWS_REGION']}_{random.choice([1000, 9999])}")
COUNTRIES = ["US", "CA", "FR", "DE", "IN", "IT", "JP", "ES", "GB"]
PERIOD_SELECTION = ["P1D", "PT1H", "P1M"]
S3_SUB_DIR = "integ_test_data/"

_test_data = [
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
    {
        "first_name": "Reed",
        "last_name": "Hunt",
        "email": "yourwrite@example.com",
        "product_quantity": 175,
        "product_name": "Product D",
    },
    {
        "first_name": "Gordon",
        "last_name": "Priolo",
        "email": "thefrom@example.com",
        "product_quantity": 75,
        "product_name": "Product F",
    },
    {
        "first_name": "Phillip",
        "last_name": "Dale",
        "email": "ofmoney@example.com",
        "product_quantity": 56,
        "product_name": "Product G",
    },
    {
        "first_name": "Brenda",
        "last_name": "Correll",
        "email": "ohwe@example.com",
        "product_quantity": 81,
        "product_name": "Product Y",
    },
    {
        "first_name": "Mollie",
        "last_name": "Gaines",
        "email": "gmollie@example.com",
        "product_quantity": 101,
        "product_name": "Product J",
    },
    {
        "first_name": "Mary",
        "last_name": "Chancellor",
        "email": "ion@example.com",
        "product_quantity": 24,
        "product_name": "Product A",
    },
    {
        "first_name": "Rhonda",
        "last_name": "Kelly",
        "email": "themthat@example.com",
        "product_quantity": 105,
        "product_name": "Product Z",
    },
    {
        "first_name": "Rhonda",
        "last_name": "Kelly",
        "email": "This is an invalid email.",
        "product_quantity": 105,
        "product_name": "Product J",
    },  # test invalid email
    {
        "first_name": "Rhonda",
        "last_name": "Kelly",
        "email": "te$s-t@te^st.c()om",
        "product_quantity": 105,
        "product_name": "Product B",
    },  # test invalid email
    {
        "first_name": "Rhonda",
        "last_name": "Kelly",
        "email": "te-st@tEsT.CoM",
        "product_quantity": 105,
        "product_name": "Product P",
    },  # test invalid email
]


@pytest.fixture
def mock_advertising_api():
    """Mock requests to advertising-api.amazon.com domain with custom response body."""
    @contextmanager
    def _mock(response_body, status_code=200, method="GET"):
        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                method,
                requests_mock.ANY,
                json=response_body,
                status_code=status_code,
                additional_matcher=lambda request: "advertising-api.amazon.com" in request.url
            )
            yield m
            # Assert the expected call was made
            assert m.called
            assert any("advertising-api.amazon.com" in req.url for req in m.request_history)
    
    return _mock


def _get_secret(secret_id, region, client=None):
    session = boto3.session.Session(region_name=region)
    client = client or session.client("secretsmanager")
    res = client.get_secret_value(
        SecretId=secret_id,
    )
    if not res.get("SecretString"):
        raise AssertionError(f"SecretID - {secret_id} does not exist.")
    return res


@pytest.fixture
def get_secret():
    def _method(secret_id, region, client=None):
        return _get_secret(secret_id=secret_id, region=region, client=client)
    return _method


def get_test_variables():
    if os.getenv("TEST_PARAMS_SECRET_NAME"):
        logger.warning("Running NW Test")
        secret_id = os.environ.get("TEST_PARAMS_SECRET_NAME") or "amcufa_integ_test_secret"
        region = os.environ.get("TEST_PARAMS_SECRET_NAME_REGION") or "us-east-1"
        return json.loads(_get_secret(secret_id=secret_id, region=region)["SecretString"])

    logger.warning("Running Integ Test")
    return {
        "instance_id": os.environ["AMC_INSTANCE_ID"],
        "advertiser_id": os.environ["AMC_ADVERTISER_ID"],
        "marketplace_id": os.environ["AMC_MARKETPLACE_ID"],
        "data_upload_account_id": os.environ["TEST_DATA_UPLOAD_ACCOUNT_ID"],
        "data_bucket_name": os.environ["DATA_BUCKET_NAME"],
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "refresh_token": os.environ["REFRESH_TOKEN"],
        "auth_code": os.environ["AUTH_CODE"],
    }


_test_configs = {
    "outputBucket": os.environ["ARTIFACT_BUCKET"],
    "account_id": os.environ["TEST_ACCOUNT_ID"],
    "user_id": os.environ.get("USER_POOL_ID", TEST_USER_ID),
    "stack_name": os.environ["STACK_NAME"],
    "region": os.environ["AWS_REGION"],
    "ui_url": os.environ["USER_INTERFACE"],
    "secret_id": f"{os.environ['STACK_NAME']}-{TEST_USER_ID}",
    "state": "test_state",
    "content_type": "application/json",
    **get_test_variables()
}

_required_variables = [
    "region",
    "outputBucket",
    "ui_url",
    "instance_id",
    "advertiser_id",
    "marketplace_id",
    "data_upload_account_id",
    "client_id",
    "client_secret",
    "refresh_token",
    "data_bucket_name"
]


@pytest.mark.dependency()
@pytest.mark.run(order=1)
def test_test_configs(test_configs):
    try:
        for required_variable in _required_variables:
            assert test_configs[required_variable] is not None
    except AssertionError:
        logger.exception(f"All variables are required: {_required_variables}")
        raise



@pytest.fixture
def generate_random_test_files_to_s3_bucket():
    def _method(s3_key):
        file_format = s3_key.split(".")[-1].upper()
        output = ""
        for index, item in enumerate(_test_data):
            current_time_index_mins_ago = (
                datetime.datetime.now() - datetime.timedelta(minutes=index)
            )
            item["timestamp"] = str(current_time_index_mins_ago)
            _test_data[index]["timestamp"] = item["timestamp"]
            output += json.dumps(item) + "\n"

        content_type = _test_configs["content_type"]
        if file_format == "CSV":
            content_type = "text/csv"
            output = pd.read_json(json.dumps(_test_data)).to_csv(
                encoding="utf-8",
                index=False,
                header=True,
            )

        s3 = boto3.resource("s3", region_name=_test_configs["region"])
        s3_object = s3.Object(_test_configs["data_bucket_name"], s3_key)
        s3_object.put(Body=output, ContentType=content_type)

        payload_default = {
            "s3bucket": _test_configs["data_bucket_name"],
            "s3key": s3_key,
        }

        with Client(app.app) as client:
            response = client.http.post(
                "/get_data_columns",
                headers={"Content-Type": _test_configs["content_type"]},
                body=json.dumps(
                    {**payload_default, "file_format": file_format}
                ),
            )
            assert response.status_code == 200
            assert response.json_body["columns"] is not None
            for expected_key in list(_test_data[0].keys()):
                assert expected_key in response.json_body["columns"]

    return _method


@pytest.fixture
def test_configs():
    return _test_configs


@pytest.fixture
def get_origin_headers(test_configs):
    return {"Origin": test_configs["ui_url"]}


@pytest.mark.run(order=1)
@pytest.mark.dependency(depends=["test_test_configs"])
def test_save_secret(test_configs):
    # This should always run first
    # save client and secret to Aws secret.
    with Client(app.app) as client:
        response = client.http.post(
            "/save_secret",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps(
                {
                    "user_id": test_configs["user_id"],
                    "client_id": test_configs["client_id"],
                    "client_secret": test_configs["client_secret"],
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {}


@pytest.mark.run(order=2)
@pytest.mark.dependency(depends=["test_save_secret"])
def test_validate_amc_request(test_configs, get_origin_headers, get_secret):
    # Should run after client id and secret are stored.
    # Validate creds.

    class ValidateCreds():
        secret_id = test_configs["secret_id"]
        auth_code = test_configs.get("auth_code")
        refresh_token = test_configs.get("refresh_token")
        session = boto3.session.Session(region_name=test_configs["region"])
        client = session.client("secretsmanager")

        def test_auth_code(self):
            # create new refresh token with provide auth_token
            with Client(app.app) as client_web:
                response = client_web.http.post(
                    "/validate_amc_request",
                    headers={
                        "Content-Type": test_configs["content_type"],
                        **get_origin_headers,
                    },
                    body=json.dumps(
                        {
                            "user_id": test_configs["user_id"],
                            "auth_code": self.auth_code,
                        }
                    ),
                )
                assert response.status_code == 200
                assert response.json_body["client_id"] == test_configs["client_id"]
                assert response.json_body.get("refresh_token") is not None
                assert response.json_body.get("access_token") is not None

        def test_refresh_code(self):
            # update secret with refresh token
            res = get_secret(secret_id=self.secret_id, client=self.client, region=test_configs["region"])
            secret_string = json.loads(res["SecretString"])
            secret_string["refresh_token"] = self.refresh_token
            self.client.update_secret(
                SecretId=self.secret_id, SecretString=json.dumps(secret_string)
            )
            res = self.client.get_secret_value(
                SecretId=self.secret_id,
            )
            if not json.loads(res["SecretString"]).get("refresh_token"):
                raise AssertionError("Refresh token was not saved.")
            elif self.refresh_token != json.loads(res["SecretString"]).get(
                "refresh_token"
            ):
                raise AssertionError("Incorrect Refresh token.")
            
        def test_secret_refresh_token_client_sec_id(self):
            # check if secret exist and has all oAuth creds to continue testing.
            try:
                res = get_secret(secret_id=self.secret_id, client=self.client, region=test_configs["region"])
                for expected_item in [
                    "client_id",
                    "client_secret",
                    "refresh_token",
                ]:
                    if not json.loads(res["SecretString"]).get(expected_item):
                        raise AssertionError(
                            f"{expected_item} is not saved in client."
                        )
                    elif (
                        expected_item == "refresh_token"
                        and json.loads(res["SecretString"]).get(expected_item)
                        == "TOKEN_DELETED"
                    ):
                        raise AssertionError(f"{expected_item} is deleted.")

            except Exception as exception:
                if (
                    hasattr(exception, "response")
                    and exception.response.get("Error", {}).get("Code")
                    == "ResourceNotFoundException"
                ):
                    raise AssertionError(
                        "REFRESH_TOKEN or AUTH_CODE are required."
                    )
                else:
                    raise

        def run_test(self):

            if self.auth_code:
                self.test_auth_code()

            elif self.refresh_token:
                self.test_refresh_code()
                
            else:
                self.test_secret_refresh_token_client_sec_id()

    ValidateCreds().run_test()


@pytest.mark.run(order=3)
@pytest.mark.dependency(depends=["test_validate_amc_request"])
def test_setup_amc_instance(test_configs):
    # Test applies bucket policy to allow data upload from AMC.

    marketplace_id = test_configs["marketplace_id"]
    advertiser_id = test_configs["advertiser_id"]
    instance_id = test_configs["instance_id"]
    data_upload_account_id = test_configs["data_upload_account_id"]
    with Client(app.app) as client:
        response = client.http.post(
            "/system/configuration",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps(
                {
                    "Name": "AmcInstances",
                    "Value": [
                        {
                            "data_upload_account_id": data_upload_account_id,
                            "instance_id": instance_id,
                            "advertiser_id": advertiser_id,
                            "marketplace_id": marketplace_id,
                            "tag_list": "integ_test, integ_test_tester",
                            "tags": [
                                {
                                    "value": "integ_test",
                                    "key": "integ_test_key",
                                },
                                {
                                    "value": "integ_test_tester",
                                    "key": "integ_test_tester_key",
                                },
                            ],
                        }
                    ],
                }
            ),
        )
        assert response.status_code == 200
        assert response.json_body == {}

        response = client.http.get(
            "/system/configuration",
            headers={"Content-Type": test_configs["content_type"]},
        )
        assert response.status_code == 200
        expected_item = [
            item
            for item in [
                value_item for value_item in response.json_body[0]["Value"]
            ]
            if item.get("data_upload_account_id") == data_upload_account_id
        ]
        assert len(expected_item) >= 1
        expected_item = expected_item[0]
        if not isinstance(expected_item, dict):
            raise AssertionError("AmcInstance value must be of type dict")
        for expected_key in ["instance_id", "advertiser_id", "marketplace_id"]:
            if expected_key not in expected_item:
                raise AssertionError(
                    f"AmcInstance value must contain key, '{expected_key}'"
                )
        assert (
            expected_item["data_upload_account_id"] == data_upload_account_id
        )
        assert expected_item["instance_id"] == instance_id
        assert expected_item["marketplace_id"] == marketplace_id
        assert expected_item["advertiser_id"] == advertiser_id
        time.sleep(
            10
        )  # Allow some time for s3 bucket policy to be provisioned.


@pytest.mark.dependency(depends=["test_test_configs"])
def test_version(test_configs):
    with Client(app.app) as client:
        response = client.http.get(
            "/version",
            headers={"Content-Type": test_configs["content_type"]},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]


@pytest.mark.dependency(depends=["test_test_configs"])
def test_list_bucket(test_configs):
    with Client(app.app) as client:
        response = client.http.post(
            "/list_bucket",
            headers={"Content-Type": test_configs["content_type"]},
            body=json.dumps({"data_bucket_name": test_configs["data_bucket_name"]}),
        )
        assert response.status_code == 200
        assert len(response.json_body) > 0


@pytest.mark.dependency(depends=["test_setup_amc_instance"])
def test_get_amc_instances(test_configs, get_origin_headers, mock_advertising_api):
    mock_response = {
        "instances": [
            {
                "instanceId": 12345,
                "dataUploadAwsAccountId": test_configs["data_upload_account_id"],
                "instanceName": "Test Instance",
            }
        ]
    }
    with mock_advertising_api(mock_response, status_code=200):
        with Client(app.app) as client:
            response = client.http.post(
                "/get_amc_instances",
                headers={
                    "Content-Type": test_configs["content_type"],
                    **get_origin_headers,
                },
                body=json.dumps(
                    {
                        "user_id": test_configs["user_id"],
                        "marketplace_id": test_configs["marketplace_id"],
                        "advertiser_id": test_configs["advertiser_id"],
                        "state": test_configs["state"],
                    }
                ),
            )
            assert response.status_code == 200
            assert response.json_body["instances"]
            assert len(response.json_body["instances"]) > 0
        assert response.json_body["instances"][0]["instanceId"] == mock_response["instances"][0]["instanceId"]
        assert (
            response.json_body["instances"][0]["dataUploadAwsAccountId"]
            == mock_response["instances"][0]["dataUploadAwsAccountId"]
        )
        assert response.json_body["instances"][0]["instanceName"] == mock_response["instances"][0]["instanceName"]


@pytest.mark.dependency(depends=["test_setup_amc_instance"])
def test_get_amc_accounts(test_configs, get_origin_headers, mock_advertising_api):
    mock_response = {
        "amcAccounts": [
            {
                "accountId": "123456789012",
                "accountName": "Test Account",
                "marketplaceId": test_configs["marketplace_id"],
            }
        ]
    }

    with mock_advertising_api(mock_response, status_code=200):
        with Client(app.app) as client:
            response = client.http.post(
                "/get_amc_accounts",
                headers={
                    "Content-Type": test_configs["content_type"],
                    **get_origin_headers,
                },
                body=json.dumps(
                    {
                        "user_id": test_configs["user_id"],
                        "state": test_configs["state"],
                    }
                ),
            )
            assert response.status_code == 200
            assert response.json_body["amcAccounts"]
            assert len(response.json_body["amcAccounts"]) > 0
            assert response.json_body["amcAccounts"][0]["accountId"] == mock_response["amcAccounts"][0]["accountId"]
            assert (
                response.json_body["amcAccounts"][0]["accountName"]
                == mock_response["amcAccounts"][0]["accountName"]
            )
            assert (
                response.json_body["amcAccounts"][0]["marketplaceId"]
                == mock_response["amcAccounts"][0]["marketplaceId"]
            )


@pytest.fixture
def get_etl_data_by_job_id():
    def _method(job_id):
        with Client(app.app) as client:
            response = client.http.get(
                "/get_etl_jobs",
                headers={"Content-Type": _test_configs["content_type"]},
            )

            for job_run in response.json_body["JobRuns"]:
                if job_id == job_run["Id"]:
                    return job_run

    return _method

class TestDataSetType():

    data_set_id = None
    max_wait = 10
    uploads_to_delete = None

    def __init__(self, **kwargs) -> None:
        self.mock_advertising_api = kwargs["mock_advertising_api"]
        self.period_selection = kwargs.get("period_selection") or random.choice(PERIOD_SELECTION)
        self.country_selection = kwargs.get("country_selection") or random.choice(COUNTRIES)
        self.random_4d = random.randrange(1000, 9999)
        self.time_uuid = int(time.time())
        self.is_dimension = kwargs.get("is_dimension")
        self.file_format = kwargs["file_format"]
        self.s3_key_sub_dir = kwargs.get("s3_key_sub_dir") or ""
        self.get_origin_headers = kwargs["get_origin_headers"]
        self.generate_random_test_files_to_s3_bucket = kwargs["generate_random_test_files_to_s3_bucket"]
        self.test_configs = kwargs["test_configs"]
        self.user_id = self.test_configs["user_id"]
        self.marketplace_id = self.test_configs["marketplace_id"]
        self.advertiser_id = self.test_configs["advertiser_id"]
        self.instance_id = self.test_configs["instance_id"]
        self.get_etl_data_by_job_id = kwargs["get_etl_data_by_job_id"]
        self.data_set_id = self.get_data_set_id()
        self.test_columns = kwargs.get("test_columns") or self.get_test_columns()
        self.test_source_key = self.get_test_source_key()
        self.generate_random_test_files_to_s3_bucket(s3_key=self.test_source_key)
        self.uploads_to_delete = {}

    def get_default_headers(self):
        return {
            "Content-Type": self.test_configs["content_type"],
            **self.get_origin_headers
        }

    def get_auth_payload(self):
        return {
            "dataSetId": self.data_set_id,
            "user_id": self.user_id,
            "instance_id": self.instance_id,
            "advertiser_id": self.advertiser_id,
            "marketplace_id": self.marketplace_id,
        }

    def get_data_set_id(self):
        ds_tag = f"_{self.period_selection}"
        if not self.is_dimension:
            ds_tag = ""
        return f"integ_test_{self.time_uuid}_{self.random_4d}{ds_tag}_{self.file_format}_{self.country_selection}".lower()
    
    def get_test_source_key(self):
        test_source_key = f"{self.s3_key_sub_dir}{self.data_set_id}.json"  # JSON
        if self.file_format == "CSV":
            test_source_key = f"{self.data_set_id}.csv"
        logger.info(f"TEST_SOURCE_KEY: {test_source_key}")
        return test_source_key

    def get_time_stamp_data_set_type(self):
        time_stamp_data_set_type = {
            "dataType": "STRING",
        }  # DIMENSION
        if not self.is_dimension:
            time_stamp_data_set_type = {
                "dataType": "TIMESTAMP",
                "isMainEventTime": True,
            }
        logger.info(
            f"TIME_STAMP_DATA_SET_TYPE: {time_stamp_data_set_type}"
        )
        return time_stamp_data_set_type
    
    def get_period_object(self):
        period_object = {}
        if not self.is_dimension:
            period_object = {
                "period": self.period_selection
            }
        return period_object


    def get_test_columns(self):
        return [
            {
                "name": "user_id",
                "description": "The customer resolved id",
                "dataType": "STRING",
                "nullable": True,
                "isMainUserId": True,
                "columnType": "DIMENSION",
            },
            {
                "name": "user_type",
                "description": "The customer resolved type",
                "dataType": "STRING",
                "nullable": True,
                "isMainUserIdType": True,
                "columnType": "DIMENSION",
            },
            {
                "name": "first_name",
                "description": "hashed First name",
                "dataType": "STRING",
                "externalUserIdType": {
                    "hashedPii": "FIRST_NAME",
                },
                "nullable": True,
                "columnType": "DIMENSION",
            },
            {
                "name": "last_name",
                "description": "hashed Last name",
                "dataType": "STRING",
                "externalUserIdType": {
                    "hashedPii": "LAST_NAME",
                },
                "nullable": True,
                "columnType": "DIMENSION",
            },
            {
                "name": "email",
                "description": "hashed Email",
                "dataType": "STRING",
                "externalUserIdType": {
                    "hashedPii": "EMAIL",
                },
                "nullable": True,
                "columnType": "DIMENSION",
            },
            {
                "name": "timestamp",
                "description": "Timestamp",
                "columnType": "DIMENSION",
                **self.get_time_stamp_data_set_type(),
            },
            {
                "name": "product_quantity",
                "description": "Product quantity",
                "dataType": "STRING",
                "columnType": "METRIC",
            },
            {
                "name": "product_name",
                "description": "Product name",
                "dataType": "STRING",
                "columnType": "DIMENSION",
            },
        ]
    
    def test_create_data_set(self):
        mock_response = {"dataSetId": self.data_set_id, "instanceId": self.instance_id}
        with self.mock_advertising_api(mock_response, method="POST"):
            with Client(app.app) as client:
                # create_dataset
                response = client.http.post(
                    "/create_dataset",
                    headers=self.get_default_headers(),
                    body=json.dumps(
                        {
                            "body": {
                                "dataSet": {
                                    "dataSetId": self.data_set_id,
                                    "fileFormat": self.file_format,
                                    "countryCode": self.country_selection,
                                    "compressionFormat": "GZIP",
                                    "columns": self.test_columns,
                                    "description": f"AMCUFA Integration Tests @ {datetime.datetime.utcnow()} UTC for {self.data_set_id}.",
                                    **self.get_period_object()
                                }
                                
                            },
                            "user_id": self.user_id,
                            "instance_id": self.instance_id,
                            "advertiser_id": self.advertiser_id,
                            "marketplace_id": self.marketplace_id,
                        }
                    ),
                )
                assert response.status_code == 200
                assert response.json_body["dataSetId"] == self.data_set_id
                assert response.json_body["instanceId"] == self.instance_id

    def test_describe_dataset(self):
        # check if it exists in AMC
        mock_response = {"dataSet": {"dataSetId": self.data_set_id}}
        with self.mock_advertising_api(mock_response):
            with Client(app.app) as client:
                response = client.http.post(
                    "/describe_dataset",
                    headers=self.get_default_headers(),
                body=json.dumps(self.get_auth_payload()),
                )
                assert response.status_code == 200
                assert response.json_body["dataSet"]["dataSetId"] == self.data_set_id

    def test_start_transformation(self):
        # start_amc_transformation
        with Client(app.app) as client:
            response = client.http.post(
                "/start_amc_transformation",
                headers=self.get_default_headers(),
                body=json.dumps(
                    {
                        "sourceBucket": self.test_configs["data_bucket_name"],
                        "sourceKey": self.test_source_key,
                        "outputBucket": self.test_configs["outputBucket"],
                        "piiFields": '[{"column_name":"first_name","pii_type":"FIRST_NAME"},{"column_name":"last_name","pii_type":"LAST_NAME"},{"column_name":"email","pii_type":"EMAIL"}]',
                        "deletedFields": "[]",
                        "timestampColumn": "timestamp"
                        if not self.is_dimension
                        else "",
                        "datasetId": self.data_set_id,
                        "countryCode": self.country_selection,
                        "amc_instances": json.dumps(
                            [{"instance_id": self.instance_id}]
                        ),
                        "user_id": self.user_id,
                        "updateStrategy": "ADDITIVE",
                        **self.get_period_object(),
                    }
                ),
            )
            assert response.status_code == 200
            assert response.json_body["JobRunId"] is not None
            assert (
                self.get_etl_data_by_job_id(response.json_body["JobRunId"])
                is not None
            )

            while (
                self.get_etl_data_by_job_id(response.json_body["JobRunId"])[
                    "JobRunState"
                ]
                != "SUCCEEDED"
            ):
                logger.info(
                    self.get_etl_data_by_job_id(response.json_body["JobRunId"])[
                        "JobRunState"
                    ]
                )
                if (
                    self.get_etl_data_by_job_id(response.json_body["JobRunId"])[
                        "JobRunState"
                    ]
                    == "SUCCEEDED"
                ):
                    break
                else:
                    assert (
                        self.get_etl_data_by_job_id(
                            response.json_body["JobRunId"]
                        )["JobRunState"]
                        != "FAILED"
                    )

    def test_get_etl_jobs(self):
        with Client(app.app) as client:
            response = client.http.get(
                "/get_etl_jobs",
                headers={"Content-Type": self.test_configs["content_type"]},
            )
            assert response.status_code == 200
            assert len(response.json_body["JobRuns"]) > 0
            assert (
                response.json_body["JobRuns"][0]["JobName"]
                == os.environ["AMC_GLUE_JOB_NAME"]
            )

    def test_list_uploads(self):
        mock_response = {"uploads": [{"uploadId": "test123", "status": "SUCCESS"}]}
        with self.mock_advertising_api(mock_response, method="POST"):
            self.wait(3*60) # wait 3 minutes for upload to complete.
            with Client(app.app) as client:
                response = client.http.post(
                    "/list_uploads",
                    headers=self.get_default_headers(),
                    body=json.dumps(self.get_auth_payload()),
                )

                assert response.status_code == 200
                assert len(response.json_body["uploads"]) >= 1

                for upload_item in response.json_body["uploads"]:
                    self.uploads_to_delete[upload_item["uploadId"]] = False # set to False by default.

                for upload_item in response.json_body["uploads"]:
                    assert upload_item["uploadId"] is not None
                    assert upload_item["status"] in [
                        "IN_PROGRESS",
                        "SUBMITTED",
                        "SUCCESS",
                    ]
                    self.test_upload_status(upload_item["uploadId"])

    def test_upload_status(self, upload_id, wait_count=0):
        # upload_status
        mock_response = {"upload": {"status": "SUCCESS"}}
        with self.mock_advertising_api(mock_response, method="GET"):
            with Client(app.app) as client:
                response = client.http.post(
                    "/upload_status",
                    headers=self.get_default_headers(),
                    body=json.dumps(
                        {
                            "uploadId": str(
                                upload_id
                            ),
                            **self.get_auth_payload()
                        }
                    ),
                )
                assert response.status_code == 200
                upload_item_status = response.json_body["upload"]["status"]
                if upload_item_status in ["FAILED", "SUCCESS"]:
                    self.uploads_to_delete[upload_id] = True
                    if upload_item_status == "FAILED":
                        raise AssertionError(f"Upload failed during submission - {response.json_body}")
                else:
                    self.uploads_to_delete[upload_id] = False # Do not delete dataset with IN_PROGRESS upload status. 
                    logger.info(response.json_body)
                    if wait_count > self.max_wait:
                        logger.error(f"Failed to upload in {self.max_wait}mins.")
                        logger.warning(f"""
                            Upload still in {upload_item_status or 'IN_PROGRESS'} status; Integ test does not need to fail.
                            However, is good to know why it could take more than {self.max_wait or 'X'} mins to upload a dataset.
                            ToDo: Setup clean-up task to delete integ datasets.
                        """)
                        return

                    wait_count += 1
                    self.wait(seconds=60)
                    self.test_upload_status(upload_id)


    def test_delete_data_set(self):
        # delete source bucket
        s3 = boto3.resource("s3", region_name=self.test_configs["region"])
        s3.Object(self.test_configs["data_bucket_name"], self.test_source_key).delete()

        logger.debug(f"Cleaning up dataset {self.data_set_id}.")

        if self.delete_data_set():
            # test /delete_dataset
            mock_response = {"dataSetId": self.data_set_id, "instanceId": self.instance_id}
            with self.mock_advertising_api(mock_response, method="DELETE"):
                with Client(app.app) as client:
                    response = client.http.post(
                        "/delete_dataset",
                        headers=self.get_default_headers(),
                        body=json.dumps(self.get_auth_payload()),
                    )
                    assert response.status_code == 200
                    assert response.json_body["dataSetId"] == self.data_set_id
                    assert response.json_body["instanceId"] == self.instance_id
        else:
            logger.warning(f"Dataset: {self.data_set_id} not deleted.")

    def wait(self, seconds=20):
        for second in range(seconds, 0, -1):
            logger.info(f"waiting for {second}secs.")
            time.sleep(1)

    def delete_data_set(self):
        # if any uploads still in_progress, then don't delete dataset.
        for _, status in self.uploads_to_delete.items():
            if not status:
                return False
        return True

            


@pytest.fixture
def execute_dataset_steps(
    generate_random_test_files_to_s3_bucket,
    get_etl_data_by_job_id,
    get_origin_headers,
    test_configs,
    mock_advertising_api
):
    def _method(**test_parameters):
        process_wait_time = 30
        test_steps = [
            "test_create_data_set",
            "test_describe_dataset",
            "test_start_transformation",
            "test_get_etl_jobs",
            "test_list_uploads",
        ]

        test_data_set_type = TestDataSetType(
            generate_random_test_files_to_s3_bucket=generate_random_test_files_to_s3_bucket,
            get_etl_data_by_job_id=get_etl_data_by_job_id,
            get_origin_headers=get_origin_headers,
            test_configs=test_configs,
            mock_advertising_api=mock_advertising_api,
            **test_parameters

        )

        try:
            for test_step in test_steps:
                try:
                    getattr(test_data_set_type, test_step)()
                    test_data_set_type.wait(process_wait_time) # wait before processing next step.
                except Exception as ex:
                    logger.error(f"Error @ Step: {test_step}")
                    logger.exception(f"Error: {ex=}")
                    raise
        finally:
            test_data_set_type.test_delete_data_set()

    return _method


@pytest.mark.dependency(depends=["test_setup_amc_instance"])
def test_create_upload_delete_dataset_dimension_json_random_country(execute_dataset_steps):
    execute_dataset_steps(
        data_set_type="DIMENSION",
        file_format="JSON",
    )


@pytest.mark.dependency(depends=["test_create_upload_delete_dataset_dimension_json_random_country"])
def test_create_upload_delete_dataset_dimension_csv_random_country(
    execute_dataset_steps,
):
    execute_dataset_steps(
        data_set_type="DIMENSION",
        file_format="CSV",
    )


@pytest.mark.dependency(depends=["test_setup_amc_instance"])
def test_create_upload_delete_dataset_json_random_country_random_period_selection(
    execute_dataset_steps
):
    execute_dataset_steps(
        file_format="JSON",
    )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_setup_amc_instance"])
def test_create_upload_delete_dataset_csv_random_country_random_period_selection(
    execute_dataset_steps
):
    execute_dataset_steps(
        file_format="CSV",
    )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_create_upload_delete_dataset_csv_random_country_random_period_selection"])
def test_create_upload_delete_dataset_dimension_json_sub_directory_random_country(
    execute_dataset_steps
):
    execute_dataset_steps(
        data_set_type="DIMENSION",
        file_format="JSON",
        s3_key_sub_dir=S3_SUB_DIR,
    )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_create_upload_delete_dataset_json_random_country_random_period_selection"])
def test_create_upload_delete_dataset_json_sub_directory_random_country_random_period_selection(
    execute_dataset_steps
):
    execute_dataset_steps(
        file_format="JSON",
        s3_key_sub_dir=S3_SUB_DIR,
    )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_create_upload_delete_dataset_json_sub_directory_random_country_random_period_selection"])
def test_all_dimension(
    execute_dataset_steps
):
    for file_format in ["JSON", "CSV"]:
        for country in COUNTRIES:
            execute_dataset_steps(
                file_format=file_format,
                country=country
            )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_all_dimension"])
def test_all_period(
    execute_dataset_steps
):
    for file_format in ["JSON", "CSV"]:
        for period_selection in PERIOD_SELECTION:
            for country in COUNTRIES:
                execute_dataset_steps(
                    file_format=file_format,
                    country=country,
                    period_selection=period_selection
                )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_all_period"])
def test_all_dimension_sub_directory(
    execute_dataset_steps
):
    for file_format in ["JSON", "CSV"]:
            for country in COUNTRIES:
                execute_dataset_steps(
                    file_format=file_format,
                    country=country,
                    s3_key_sub_dir=S3_SUB_DIR,
                )


@pytest.mark.skipif(not RUN_DEEP_TEST, reason=SKIP_REASON)
@pytest.mark.dependency(depends=["test_all_dimension_sub_directory"])
def test_all_period_sub_directory(
    execute_dataset_steps
):
    for file_format in ["JSON", "CSV"]:
        for period_selection in PERIOD_SELECTION:
            for country in COUNTRIES:
                execute_dataset_steps(
                    file_format=file_format,
                    country=country,
                    period_selection=period_selection,
                    s3_key_sub_dir=S3_SUB_DIR,
                )
