# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   Upload data files to AMC.
#   Data file must be in the format required by AMC. i.e. transformation is done.
#
# USAGE:
#   Start this Lambda with an S3 CreateObject trigger on the bucket where
#   transformed data files are saved.
#
# REQUIREMENTS:
#   Input files should be in a location like this:
#     s3://[bucket_name]/[dataset_id]/[timeseries_partition_size]/[destination_endpoint]/[filename]
#   Such as,
#     s3://my_etl_artifacts/myDataset123/P1D/aHR0cHM6Ly9hYmNkZTEyMzQ1LmV4ZWN1dGUtYXBpLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3Byb2Q=/amc-data-mid.json-2014_03_12-19:06:00.gz
###############################################################################

import json
import logging
import os
import urllib.parse
from datetime import datetime

# Patch libraries to instrument downstream calls
from aws_xray_sdk.core import patch_all
from botocore import config
import boto3
from dateutil.relativedelta import relativedelta
from lib.sigv4 import sigv4

patch_all()

# Environment variables
solution_config = json.loads(os.environ["botoConfig"])
config = config.Config(**solution_config)
UPLOAD_FAILURES_TABLE_NAME = os.environ["UPLOAD_FAILURES_TABLE_NAME"]

# format log messages like this:
formatter = logging.Formatter(
    "{%(pathname)s:%(lineno)d} %(levelname)s - %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Remove the default logger in order to avoid duplicate log messages
# after we attach our custom logging handler.
logging.getLogger().handlers.clear()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def lambda_handler(event, context):
    logger.info("We got the following event:\n")
    logger.info("event:\n {s}".format(s=event))
    logger.info("context:\n {s}".format(s=context))
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote(event["Records"][0]["s3"]["object"]["key"])
    if _is_dataset(key):
        if _is_timeseries(key):
            _start_fact_upload(bucket=bucket, key=key)
        else:
            _start_dimension_upload(bucket=bucket, key=key)


def _is_dataset(key):
    return key.endswith(".gz")


def _is_timeseries(key):
    supported_time_partitions = (
        "PT1M",
        "PT1H",
        "P1D",
        "P7D",
    )
    # Time series datasets will have the following s3key pattern:
    #   amc/[dataset_id]/[country_code]/[timeseries_partition_size]/[destination_endpoint][filename]
    return (len(key.split("/")) == 6) and (
        key.split("/")[3].endswith(supported_time_partitions)
    )


def _start_fact_upload(bucket, key):
    try:
        logger.info("Uploading FACT dataset")
        # Key parsing assume s3Key is in the following format:
        #   amc/[dataset_id]/[country_code]/[amc time resolution code]/[destination_endpoint]/[datafile].gz
        _, dataset_id, country_code, time_partition, destination_endpoint, filename_quoted = key.split('/')
        destination_endpoint_url = "https://" + destination_endpoint + "/prod"
        filename = urllib.parse.unquote(filename_quoted)
        # Parse the filename to get the time window for that data.
        # Filenames should look like this, "etl_output_data.json-2022_01_06-09:01:00.gz"
        dt_str = (
            filename.split(".")[-2].replace("csv-", "").replace("json-", "")
        )
        time_window_start = datetime.strptime(dt_str, "%Y_%m_%d-%H:%M:%S")
        # Format the time window like, "2022-01-06T09:01:00Z"
        if time_partition == "PT1M":
            time_window_end = time_window_start + relativedelta(minutes=1)
        if time_partition == "PT1H":
            time_window_end = time_window_start + relativedelta(hours=1)
        if time_partition == "P1D":
            time_window_end = time_window_start + relativedelta(days=1)
        if time_partition == "P7D":
            time_window_end = time_window_start + relativedelta(days=7)

        logger.info("key: " + key)
        logger.info("dataset_id " + dataset_id)
        logger.info("country_code " + country_code)
        logger.info("time_partition " + time_partition)
        logger.info("time_window_start " + time_window_start.isoformat() + "Z")
        logger.info("time_window_end " + time_window_end.isoformat() + "Z")
        logger.info("filename " + filename)
        # Datasets are defined with a default time period of P1D.
        # Here we update the dataset definition if the Glue ETL job
        # detected a different time period.
        path = "/dataSets/" + dataset_id
        logger.info("Validating dataset time period.")
        dataset_definition = json.loads(
            sigv4.get(destination_endpoint_url, path).text
        )
        if dataset_definition["period"] != time_partition:
            logger.info(
                "Changing dataset time period from "
                + dataset_definition["period"]
                + " to "
                + time_partition
            )
            dataset_definition["period"] = time_partition
            logger.info("PUT " + path + " " + json.dumps(dataset_definition))
            # Send request to update time period:
            sigv4.put(
                destination_endpoint_url, path, json.dumps(dataset_definition)
            )
            dataset_definition = json.loads(
                sigv4.get(destination_endpoint_url, path).text
            )
            # Validate updated time period:
            if dataset_definition["period"] != time_partition:
                raise AssertionError("Failed to update dataset time period.")
        logger.info(
            "Uploading s3://"
            + bucket
            + "/"
            + key
            + " to dataSetId "
            + dataset_id
        )
        data = {
            "sourceS3Bucket": bucket,
            "sourceFileS3Key": key,
            "countryCode": country_code,
            "timeWindowStart": time_window_start.isoformat() + "Z",
            "timeWindowEnd": time_window_end.isoformat() + "Z",
        }
        path = "/data/" + dataset_id + "/uploads"
        logger.info("POST " + path + " " + json.dumps(data))
        response = sigv4.post(destination_endpoint_url, path, json.dumps(data))
        logger.info(f"Response code: {response.status_code}\n")
        logger.info("Response: " + response.text)
        # Record error message if upload failed.
        dynamo_resource = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
        upload_failures_table = dynamo_resource.Table(UPLOAD_FAILURES_TABLE_NAME)
        item_key = {"dataset_id": dataset_id, "destination_endpoint": destination_endpoint_url}
        try:
            upload_failures_table.delete_item(Key=item_key)
        except dynamo_resource.meta.client.exceptions.ConditionalCheckFailedException:
            pass
        if response.status_code != 200:
            error_message = json.loads(response.text)["message"]
            item = item_key
            item["Value"] = error_message
            upload_failures_table.put_item(Item=item)
        return response.text
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": ex}


def _start_dimension_upload(bucket, key):
    try:
        logger.info("Uploading DIMENSION dataset")
        # Key parsing assume s3Key is in the following format:
        #   amc/[dataset_id]/[country_code]/dimension/destination_endpoint/[datafile].gz
        _, dataset_id, country_code, dimension_constant, destination_endpoint, filename_quoted = key.split('/')
        dataset_id = key.split("/")[1]
        country_code = key.split("/")[2]
        destination_endpoint_url = "https://" + destination_endpoint + "/prod"
        filename = urllib.parse.unquote(filename_quoted)
        logger.info("key: " + key)
        logger.info("dataset_id " + dataset_id)
        logger.info("country_code " + country_code)
        logger.info("filename " + filename)
        logger.info("Uploading s3://" + bucket + "/" + key)
        data = {
            "sourceS3Bucket": bucket,
            "sourceFileS3Key": key,
            "countryCode": country_code
        }
        path = "/data/" + dataset_id + "/uploads"
        logger.info("POST " + path + " " + json.dumps(data))
        response = sigv4.post(destination_endpoint_url, path, json.dumps(data))
        return response.text
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": ex}
