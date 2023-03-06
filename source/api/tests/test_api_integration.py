# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Integration test for project api endpoints and workflow.
#
# USAGE:
#   $ ./run_api_test.sh -rit
###############################################################################

import datetime
import json
import logging
import os
import time

import app
import boto3
import pandas as pd
import pytest
from chalice.test import Client

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_test_configs = {
    "s3bucket": os.environ["DATA_BUCKET_NAME"],
    "outputBucket": os.environ["ARTIFACT_BUCKET"],
    "destination_endpoint": os.environ["AMC_API_ENDPOINT"],
    "account_id": os.environ["TEST_ACCOUNT_ID"],
    "data_upload_account_id": os.environ["TEST_DATA_UPLOAD_ACCOUNT_ID"],
}

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
        "product_name": "Product B",
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
        "product_name": "Product B",
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
        "product_name": "Product B",
    },
    {
        "first_name": "Rhonda",
        "last_name": "Kelly",
        "email": "This is an invalid email.",
        "product_quantity": 105,
        "product_name": "Product B",
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
        "product_name": "Product B",
    },  # test invalid email
]


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

        content_type = "application/json"
        if file_format == "CSV":
            content_type = "text/csv"
            output = pd.read_json(json.dumps(_test_data)).to_csv(
                encoding="utf-8",
                index=False,
                header=True,
            )

        s3 = boto3.resource("s3")
        s3_object = s3.Object(_test_configs["s3bucket"], s3_key)
        s3_object.put(Body=output, ContentType=content_type)

        payload_default = {
            "s3bucket": _test_configs["s3bucket"],
            "s3key": s3_key,
        }
        with Client(app.app) as client:
            response = client.http.post(
                "/get_data_columns",
                headers={"Content-Type": "application/json"},
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


@pytest.mark.run(order=1)
def test_setup_amc_instance(test_configs):
    # This test must run before all other test
    endpoint = test_configs["destination_endpoint"]
    data_upload_account_id = test_configs["data_upload_account_id"]
    with Client(app.app) as client:
        response = client.http.post(
            "/system/configuration",
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "Name": "AmcInstances",
                    "Value": [
                        {
                            "data_upload_account_id": data_upload_account_id,
                            "endpoint": endpoint,
                            "tag_list": "integ_test, integ_test_tester",
                            "tags": [
                                {"value": "integ_test", "key": ""},
                                {"value": "integ_test", "key": ""},
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
            headers={"Content-Type": "application/json"},
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
        if "endpoint" not in expected_item:
            raise AssertionError(
                "AmcInstance value must contain key, 'endpoint'"
            )
        if "data_upload_account_id" not in expected_item:
            raise AssertionError(
                "AmcInstance value must contain key, 'data_upload_account_id'"
            )
        assert (
            expected_item["data_upload_account_id"] == data_upload_account_id
        )
        assert expected_item["endpoint"] == endpoint
        time.sleep(10) # Allow some time for iam roles to be provisioned.


def test_version():
    with Client(app.app) as client:
        response = client.http.get(
            "/version",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]


def test_list_bucket(test_configs):
    with Client(app.app) as client:
        response = client.http.post(
            "/list_bucket",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"s3bucket": test_configs["s3bucket"]}),
        )
        assert response.status_code == 200
        assert len(response.json_body) > 0


@pytest.fixture
def get_etl_data_by_job_id():
    def _method(job_id):
        with Client(app.app) as client:
            response = client.http.get(
                "/get_etl_jobs",
                headers={"Content-Type": "application/json"},
            )

            for job_run in response.json_body["JobRuns"]:
                if job_id == job_run["Id"]:
                    return job_run

    return _method


@pytest.fixture
def test_data_set_type():
    def _method(
        data_set_type,
        file_format,
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
        s3_key_sub_dir="",
        test_columns=None,
    ):
        is_data_set_created = False
        try:
            data_set_id = f"amc_integ_test_{int(time.time())}_{data_set_type}_{file_format}"
            period = "autodetect"
            logger.info(f"DATA_SET_TYPE: {data_set_type}")
            logger.info(f"TEST_CONFIGS: {test_configs}")
            logger.info(f"FILE_FORMAT: {file_format}")
            logger.info(f"DATA_SET_ID: {data_set_id}")

            test_source_key = f"{s3_key_sub_dir}{data_set_id}.json"  # JSON
            if file_format == "CSV":
                test_source_key = f"{data_set_id}-csv.csv"
            logger.info(f"TEST_SOURCE_KEY: {test_source_key}")
            generate_random_test_files_to_s3_bucket(s3_key=test_source_key)

            time_stamp_data_set_type = {
                "dataType": "STRING",
                "columnType": "DIMENSION",
            }  # DIMENSION
            if data_set_type == "FACT":
                time_stamp_data_set_type = {
                    "dataType": "TIMESTAMP",
                    "isMainEventTime": True,
                }
            logger.info(
                f"TIME_STAMP_DATA_SET_TYPE: {time_stamp_data_set_type}"
            )
            test_columns = test_columns or [
                {
                    "name": "user_id",
                    "description": "The customer resolved id",
                    "dataType": "STRING",
                    "nullable": True,
                    "isMainUserId": True,
                },
                {
                    "name": "user_type",
                    "description": "The customer resolved type",
                    "dataType": "STRING",
                    "nullable": True,
                    "isMainUserIdType": True,
                },
                {
                    "name": "first_name",
                    "description": "hashed First name",
                    "dataType": "STRING",
                    "externalUserIdType": {
                        "type": "HashedIdentifier",
                        "identifierType": "FIRST_NAME",
                    },
                    "nullable": True,
                },
                {
                    "name": "last_name",
                    "description": "hashed Last name",
                    "dataType": "STRING",
                    "externalUserIdType": {
                        "type": "HashedIdentifier",
                        "identifierType": "LAST_NAME",
                    },
                    "nullable": True,
                },
                {
                    "name": "email",
                    "description": "hashed Email",
                    "dataType": "STRING",
                    "externalUserIdType": {
                        "type": "HashedIdentifier",
                        "identifierType": "EMAIL",
                    },
                    "nullable": True,
                },
                {
                    "name": "timestamp",
                    "description": "Timestamp",
                    **time_stamp_data_set_type,
                },
                {
                    "name": "product_quantity",
                    "description": "Product quantity",
                    "dataType": "STRING",
                    "columnType": "DIMENSION",
                },
                {
                    "name": "product_name",
                    "description": "Product name",
                    "dataType": "STRING",
                    "columnType": "DIMENSION",
                },
            ]
            with Client(app.app) as client:
                # create_dataset
                response = client.http.post(
                    "/create_dataset",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "destination_endpoint": test_configs[
                                "destination_endpoint"
                            ],
                            "body": {
                                "dataSetId": data_set_id,
                                "fileFormat": file_format,
                                "period": "P1D",
                                "dataSetType": data_set_type,
                                "compressionFormat": "GZIP",
                                "columns": test_columns,
                            },
                        }
                    ),
                )
                assert response.status_code == 200
                assert response.json_body == {}

                time.sleep(5)  # give dataset time to be created

                # check if it exists in AMC
                response = client.http.post(
                    "/describe_dataset",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "dataSetId": data_set_id,
                            "destination_endpoint": test_configs[
                                "destination_endpoint"
                            ],
                        }
                    ),
                )
                assert response.status_code == 200
                is_data_set_created = True
                assert response.json_body["dataSetId"] == data_set_id
                assert response.json_body["dataSetType"] == data_set_type
                assert response.json_body["fileFormat"] == file_format

                # start_amc_transformation
                response = client.http.post(
                    "/start_amc_transformation",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "sourceBucket": test_configs["s3bucket"],
                            "sourceKey": test_source_key,
                            "outputBucket": test_configs["outputBucket"],
                            "piiFields": '[{"column_name":"first_name","pii_type":"FIRST_NAME"},{"column_name":"last_name","pii_type":"LAST_NAME"},{"column_name":"email","pii_type":"EMAIL"}]',
                            "deletedFields": "[]",
                            "timestampColumn": "timestamp",
                            "datasetId": data_set_id,
                            "period": period,
                            "countryCode": "US",
                            "destination_endpoints": str(
                                [test_configs["destination_endpoint"]]
                            ).replace("'", '"'),
                        }
                    ),
                )
                assert response.status_code == 200
                assert response.json_body["JobRunId"] is not None
                assert (
                    get_etl_data_by_job_id(response.json_body["JobRunId"])
                    is not None
                )

                while (
                    get_etl_data_by_job_id(response.json_body["JobRunId"])[
                        "JobRunState"
                    ]
                    != "SUCCEEDED"
                ):
                    logger.info(
                        get_etl_data_by_job_id(response.json_body["JobRunId"])[
                            "JobRunState"
                        ]
                    )
                    if (
                        get_etl_data_by_job_id(response.json_body["JobRunId"])[
                            "JobRunState"
                        ]
                        == "SUCCEEDED"
                    ):
                        break
                    else:
                        assert (
                            get_etl_data_by_job_id(
                                response.json_body["JobRunId"]
                            )["JobRunState"]
                            != "FAILED"
                        )

                time.sleep(5)  # give dataset time to upload

                response = client.http.get(
                    "/get_etl_jobs",
                    headers={"Content-Type": "application/json"},
                )
                assert response.status_code == 200
                assert len(response.json_body["JobRuns"]) > 0
                assert (
                    response.json_body["JobRuns"][0]["JobName"]
                    == os.environ["AMC_GLUE_JOB_NAME"]
                )

                response = client.http.post(
                    "/list_datasets",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "destination_endpoint": test_configs[
                                "destination_endpoint"
                            ]
                        }
                    ),
                )
                assert response.status_code == 200
                assert len(response.json_body["dataSets"]) > 0
                assert len(response.json_body["dataSets"][0]["columns"]) > 0

                # list_upload
                response = client.http.post(
                    "/list_uploads",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "dataSetId": data_set_id,
                            "destination_endpoint": test_configs[
                                "destination_endpoint"
                            ],
                        }
                    ),
                )
                assert response.status_code == 200
                assert len(response.json_body["uploads"]) > 0
                assert (
                    response.json_body["uploads"][0]["sourceFileS3Key"]
                    is not None
                )
                assert response.json_body["uploads"][0]["uploadId"] is not None
                assert response.json_body["uploads"][0]["status"] in [
                    "Pending",
                    "Succeeded",
                ]

                # upload_status
                response = client.http.post(
                    "/upload_status",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(
                        {
                            "uploadId": str(
                                response.json_body["uploads"][0]["uploadId"]
                            ),
                            "dataSetId": data_set_id,
                            "destination_endpoint": test_configs[
                                "destination_endpoint"
                            ],
                        }
                    ),
                )
                assert response.status_code == 200
                assert response.json_body["sourceS3Bucket"] is not None
                assert response.json_body["sourceFileS3Key"] is not None
                assert response.json_body["status"] in ["Pending", "Succeeded"]
        except Exception as e:
            logger.error(e)
            raise
        finally:
            logger.debug(f"Cleaning up s3 {test_source_key}.")

            s3 = boto3.resource("s3")
            s3.Object(test_configs["s3bucket"], test_source_key).delete()

            logger.debug(f"Cleaning up dataset {data_set_id}.")

            # # delete_dataset
            if is_data_set_created:
                with Client(app.app) as client:
                    response = client.http.post(
                        "/delete_dataset",
                        headers={"Content-Type": "application/json"},
                        body=json.dumps(
                            {
                                "dataSetId": data_set_id,
                                "destination_endpoint": test_configs[
                                    "destination_endpoint"
                                ],
                            }
                        ),
                    )
                    assert response.status_code == 200
                    assert response.json_body == {}

    return _method


def test_create_upload_delete_dataset_DIMENSION_JSON(
    test_configs,
    test_data_set_type,
    get_etl_data_by_job_id,
    generate_random_test_files_to_s3_bucket,
):
    test_data_set_type(
        "DIMENSION",
        "JSON",
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
    )


def test_create_upload_delete_dataset_DIMENSION_CSV(
    test_configs,
    test_data_set_type,
    get_etl_data_by_job_id,
    generate_random_test_files_to_s3_bucket,
):
    test_data_set_type(
        "DIMENSION",
        "CSV",
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
    )


def test_create_upload_delete_dataset_FACT_JSON_SUB_DIRECTORY(
    test_configs,
    test_data_set_type,
    get_etl_data_by_job_id,
    generate_random_test_files_to_s3_bucket,
):
    test_data_set_type(
        "FACT",
        "JSON",
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
        s3_key_sub_dir="integ_test_data/",
    )


def test_create_upload_delete_dataset_DIMENSION_JSON_LIVE_RAMP(
    test_configs,
    test_data_set_type,
    get_etl_data_by_job_id,
    generate_random_test_files_to_s3_bucket,
):
    test_columns = [
        {
            "name": "user_id",
            "description": "The customer resolved id",
            "dataType": "STRING",
            "nullable": True,
            "isMainUserId": True,
        },
        {
            "name": "user_type",
            "description": "The customer resolved type",
            "dataType": "STRING",
            "nullable": True,
            "isMainUserIdType": True,
        },
        {
            "name": "first_name",
            "description": "hashed First name",
            "dataType": "STRING",
            "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": "FIRST_NAME",
            },
            "nullable": True,
        },
        {
            "name": "ramp_id",
            "description": "The user's LiveRamp ID",
            "dataType": "STRING",
            "nullable": True,
            "externalUserIdType": {"type": "LiveRamp"},
        },
    ]
    test_data_set_type(
        "DIMENSION",
        "JSON",
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
        test_columns=test_columns,
    )


def test_create_upload_delete_dataset_FACT_JSON_LIVE_RAMP(
    test_configs,
    test_data_set_type,
    get_etl_data_by_job_id,
    generate_random_test_files_to_s3_bucket,
):
    test_columns = [
        {
            "name": "user_id",
            "description": "The customer resolved id",
            "dataType": "STRING",
            "nullable": True,
            "isMainUserId": True,
        },
        {
            "name": "user_type",
            "description": "The customer resolved type",
            "dataType": "STRING",
            "nullable": True,
            "isMainUserIdType": True,
        },
        {
            "name": "first_name",
            "description": "hashed First name",
            "dataType": "STRING",
            "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": "FIRST_NAME",
            },
            "nullable": True,
        },
        {
            "name": "timestamp",
            "description": "Timestamp",
            "dataType": "TIMESTAMP",
            "isMainEventTime": True,
        },
        {
            "name": "ramp_id",
            "description": "The user's LiveRamp ID",
            "dataType": "STRING",
            "nullable": True,
            "externalUserIdType": {"type": "LiveRamp"},
        },
    ]
    test_data_set_type(
        "FACT",
        "JSON",
        test_configs,
        get_etl_data_by_job_id,
        generate_random_test_files_to_s3_bucket,
        test_columns=test_columns,
    )
