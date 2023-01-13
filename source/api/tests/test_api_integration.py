# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 
# ###############################################################################
# PURPOSE:
#   * Integration test for project api endpoints and workflow.
#
###############################################################################

"""
To run integ test
python3 -m venv .venv &&
source .venv/bin/activate &&
cd tests &&
pip install -r requirements-test.txt &&
export AMC_API_ENDPOINT="" &&
export AMC_API_ROLE_ARN="" &&
export SOLUTION_NAME="" &&
export VERSION="" &&
export botoConfig="{}" &&
export AWS_XRAY_CONTEXT_MISSING=LOG_ERROR &&
export AMC_GLUE_JOB_NAME="" &&
export CUSTOMER_MANAGED_KEY="" &&
export AWS_DEFAULT_PROFILE="" &&
export AWS_REGION="" &&
export TEST_S3_BUCKET_NAME="" &&
export TEST_S3_KEY_NAME="" &&
export TEST_S3_KEY_NAME_CSV="" &&
export TEST_OUTPUT_BUCKET="" &&
export TEST_S3_KEY_NAME_SUB_DIR="" &&
pytest test_api_integration.py -vv
"""





import os
import app
import json
import time
import logging
import pytest
from chalice.test import Client
from chalicelib import sigv4

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_test_configs = {
    "s3bucket": os.environ['TEST_S3_BUCKET_NAME'],
    "s3key": os.environ['TEST_S3_KEY_NAME'],
    "s3key_csv": os.environ['TEST_S3_KEY_NAME_CSV'],
    "s3key_sub_dir": os.environ['TEST_S3_KEY_NAME_SUB_DIR'],
    "outputBucket": os.environ['TEST_OUTPUT_BUCKET'],
}

@pytest.fixture
def test_configs():
   return _test_configs


def test_version():
    with Client(app.app) as client:
        response = client.http.get(
            '/version',
            headers={'Content-Type': 'application/json'},
        )
        assert response.status_code == 200
        assert response.json_body["version"] == os.environ["VERSION"]


def test_list_bucket(test_configs):
    with Client(app.app) as client:
        response = client.http.post(
            '/list_bucket',
            headers={'Content-Type': 'application/json'},
            body=json.dumps({"s3bucket": test_configs["s3bucket"]})
        )
        assert response.status_code == 200
        assert len(response.json_body) > 0


def test_get_data_columns(test_configs):

    payload_default = {
        "s3bucket": test_configs["s3bucket"],
        "s3key": test_configs["s3key"],
    }
    with Client(app.app) as client:

        # JSON
        response = client.http.post(
            '/get_data_columns',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(
            {
                **payload_default,
                "file_format": 'JSON'
            })
        )
        assert response.json_body == {'columns': ['first_name', 'last_name', 'email', 'timestamp', 'product_quantity', 'product_name']}

        # CSV
        response = client.http.post(
            '/get_data_columns',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(
            {
                **payload_default,
                "file_format": 'CSV'
            })
        )
        assert response.json_body == {'columns': ['{"first_name":"Caroline"', 'last_name:"Crane"', 'email:"funis@example.com"', 'timestamp:"2020-04-01 21:07:30-0400"', 'product_quantity:67', 'product_name:"Product C"}']}
        

@pytest.fixture
def get_etl_data_by_job_id():
    def _method(job_id):
        with Client(app.app) as client:
            response = client.http.get(
                '/get_etl_jobs',
                headers={'Content-Type': 'application/json'},
            )

            for job_run in response.json_body["JobRuns"]:
                if job_id == job_run["Id"]:
                    return job_run

    return _method

@pytest.fixture
def test_data_set_type():
    def _method(data_set_type, file_format, test_configs, get_etl_data_by_job_id, override_s3_test_key=None):

        try:
            with Client(app.app) as client:
                data_set_id = f"amc_integ_test_{int(time.time())}_{data_set_type}_{file_format}"
                logger.info(f"DATA_SET_TYPE: {data_set_type}")
                logger.info(f"TEST_CONFIGS: {test_configs}")
                logger.info(f"FILE_FORMAT: {file_format}")
                logger.info(f"DATA_SET_ID: {data_set_id}")

                test_source_key = override_s3_test_key or test_configs["s3key"] # JSON
                if file_format == "CSV":
                    test_source_key = test_configs["s3key_csv"]
                logger.info(f"TEST_SOURCE_KEY: {test_source_key}")

                time_stamp_data_set_type = {
                    "dataType": "STRING",
                    "columnType": "DIMENSION"
                } # DIMENSION
                if data_set_type == "FACT":
                    time_stamp_data_set_type = {
                        "dataType": "TIMESTAMP",
                        "isMainEventTime": True
                    }
                logger.info(f"TIME_STAMP_DATA_SET_TYPE: {time_stamp_data_set_type}")

                # create_dataset
                response = client.http.post(
                    '/create_dataset',
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps(
                        {
                            "body": {
                                "dataSetId": data_set_id,
                                "fileFormat": file_format,
                                "period": "P1D",
                                "dataSetType": data_set_type,
                                "compressionFormat": "GZIP",
                                "columns": [
                                    {
                                        "name": "user_id",
                                        "description": "The customer resolved id",
                                        "dataType": "STRING",
                                        "nullable": True,
                                        "isMainUserId": True
                                    },
                                    {
                                        "name": "user_type",
                                        "description": "The customer resolved type",
                                        "dataType": "STRING",
                                        "nullable": True,
                                        "isMainUserIdType": True
                                    },
                                    {
                                        "name": "first_name",
                                        "description": "hashed First name",
                                        "dataType": "STRING",
                                        "externalUserIdType": {
                                        "type": "HashedIdentifier",
                                        "identifierType": "FIRST_NAME"
                                        },
                                        "nullable": True
                                    },
                                    {
                                        "name": "last_name",
                                        "description": "hashed Last name",
                                        "dataType": "STRING",
                                        "externalUserIdType": {
                                        "type": "HashedIdentifier",
                                        "identifierType": "LAST_NAME"
                                        },
                                        "nullable": True
                                    },
                                    {
                                        "name": "email",
                                        "description": "hashed Email",
                                        "dataType": "STRING",
                                        "externalUserIdType": {
                                        "type": "HashedIdentifier",
                                        "identifierType": "EMAIL"
                                        },
                                        "nullable": True
                                    },
                                    {
                                        "name": "timestamp",
                                        "description": "Timestamp",
                                        **time_stamp_data_set_type
                                    },
                                    {
                                        "name": "product_quantity",
                                        "description": "Product quantity",
                                        "dataType": "STRING",
                                        "columnType": "DIMENSION"
                                    },
                                    {
                                        "name": "product_name",
                                        "description": "Product name",
                                        "dataType": "STRING",
                                        "columnType": "DIMENSION"
                                    }
                                ]
                            }
                        }
                    )
                )
                assert response.status_code == 200
                assert response.json_body == {}

                time.sleep(5) # give dataset time to be created

                # check if it exists in AMC
                amc_data_set_resp = sigv4.get(f"/dataSets/{data_set_id}")
                assert amc_data_set_resp.status_code == 200
                assert amc_data_set_resp.json()["dataSetId"] == data_set_id
                assert amc_data_set_resp.json()["dataSetType"] == data_set_type
                assert amc_data_set_resp.json()["fileFormat"] == file_format

                # start_amc_transformation
                response = client.http.post(
                    '/start_amc_transformation',
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps(
                        {
                            "sourceBucket": test_configs["s3bucket"],
                            "sourceKey": test_source_key,
                            "outputBucket": test_configs["outputBucket"],
                            "piiFields": "[{\"column_name\":\"first_name\",\"pii_type\":\"FIRST_NAME\"},{\"column_name\":\"last_name\",\"pii_type\":\"LAST_NAME\"},{\"column_name\":\"email\",\"pii_type\":\"EMAIL\"}]",
                            "deletedFields": "[]",
                            "timestampColumn": "timestamp",
                            "datasetId": data_set_id
                        }
                    )
                )
                assert response.status_code == 200
                assert response.json_body["JobRunId"] is not None
                assert get_etl_data_by_job_id(response.json_body["JobRunId"]) is not None

                while get_etl_data_by_job_id(response.json_body["JobRunId"])["JobRunState"] != "SUCCEEDED":
                    logger.info(get_etl_data_by_job_id(response.json_body["JobRunId"])["JobRunState"])
                    if get_etl_data_by_job_id(response.json_body["JobRunId"])["JobRunState"] == "SUCCEEDED":
                        break
                    else:
                        assert get_etl_data_by_job_id(response.json_body["JobRunId"])["JobRunState"] != "FAILED"

                time.sleep(5) # give dataset time to upload

                response = client.http.get(
                    '/get_etl_jobs',
                    headers={'Content-Type': 'application/json'},
                )
                assert response.status_code == 200
                assert len(response.json_body["JobRuns"]) > 0
                assert response.json_body["JobRuns"][0]["JobName"] == os.environ["AMC_GLUE_JOB_NAME"]
               
                response = client.http.get(
                    '/list_datasets',
                    headers={'Content-Type': 'application/json'},
                )
                assert response.status_code == 200
                assert len(response.json_body["dataSets"]) > 0
                assert len(response.json_body["dataSets"][0]["columns"]) > 0


                # list_upload
                response = client.http.post(
                    '/list_uploads',
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps({"dataSetId": data_set_id})
                )
                assert response.status_code == 200
                assert len(response.json_body["uploads"]) > 0
                assert response.json_body["uploads"][0]["sourceFileS3Key"] is not None
                assert response.json_body["uploads"][0]["uploadId"] is not None
                assert response.json_body["uploads"][0]["status"] in ["Pending", "Succeeded"]

                # upload_status
                response = client.http.post(
                    '/upload_status',
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps(
                        {
                            "uploadId": str(response.json_body["uploads"][0]["uploadId"]),
                            "dataSetId": data_set_id,
                        })
                )
                assert response.status_code == 200
                assert response.json_body["sourceS3Bucket"] is not None
                assert response.json_body["sourceFileS3Key"] is not None
                assert response.json_body["status"] in ["Pending", "Succeeded"]
        except Exception as e:
            logger.error(e)
            raise
        finally:
            logger.debug(f"Cleaning up {data_set_id}.")

            # delete_dataset
            response = client.http.post(
                '/delete_dataset',
                headers={'Content-Type': 'application/json'},
                body=json.dumps(
                    {
                        "dataSetId": data_set_id,
                    })
            )
            assert response.status_code == 200
            assert response.json_body == {}
    return _method

def test_create_upload_delete_dataset_DIMENSION_JSON(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("DIMENSION", "JSON", test_configs, get_etl_data_by_job_id)

def test_create_upload_delete_dataset_DIMENSION_CSV(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("DIMENSION", "CSV", test_configs, get_etl_data_by_job_id)

def test_create_upload_delete_dataset_FACT_JSON(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("FACT", "JSON", test_configs, get_etl_data_by_job_id)

def test_create_upload_delete_dataset_FACT_CSV(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("FACT", "CSV", test_configs, get_etl_data_by_job_id)

def test_create_upload_delete_dataset_DIMENSION_JSON_SUB_DIRECTORY(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("DIMENSION", "JSON", test_configs, get_etl_data_by_job_id, override_s3_test_key=test_configs["s3key_sub_dir"])

def test_create_upload_delete_dataset_FACT_JSON_SUB_DIRECTORY(test_configs, test_data_set_type, get_etl_data_by_job_id):
   test_data_set_type("FACT", "JSON", test_configs, get_etl_data_by_job_id, override_s3_test_key=test_configs["s3key_sub_dir"])
