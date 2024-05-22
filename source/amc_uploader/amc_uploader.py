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
#   Input files are expected to be in the following s3 key pattern:
#     s3://[bucket_name]/amc/[dataset_id]/[update_strategy]/[file_format]/[country_code]/[instance_id|user_id]/[datafile]
###############################################################################

import json
import logging
import os
import urllib.parse
from datetime import datetime

import boto3

# Patch libraries to instrument downstream calls
from aws_xray_sdk.core import patch_all
from boto3.dynamodb.conditions import Key
from botocore import config
from lib.tasks import tasks

patch_all()

# Environment variables
solution_config = json.loads(os.environ["botoConfig"])
config = config.Config(**solution_config)
UPLOAD_FAILURES_TABLE_NAME = os.environ["UPLOAD_FAILURES_TABLE_NAME"]
SYSTEM_TABLE_NAME = os.environ["SYSTEM_TABLE_NAME"]

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
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])
    if _is_dataset(key):
        upload_res_info = _start_upload(bucket=bucket, key=key)
        logger.debug(upload_res_info)


def _is_dataset(key):
    return key.endswith(".gz")


def get_dynamo_table(table_name):
    dynamo_resource = boto3.resource(
        "dynamodb", region_name=os.environ["AWS_REGION"]
    )
    return dynamo_resource.Table(table_name), dynamo_resource


def get_amc_instance(instance_id):
    system_table, _ = get_dynamo_table(SYSTEM_TABLE_NAME)
    response = system_table.query(
        KeyConditionExpression=Key("Name").eq("AmcInstances")
    )

    for item in response["Items"]:
        for instance in item["Value"]:
            if instance.get("instance_id") == instance_id:
                if not (instance.get("marketplace_id") and instance.get("advertiser_id")):
                    raise ValueError(
                        f"AMC instances: marketplace_id and advertiser_id required for {instance_id}."
                    )
                return instance
    raise ValueError(f"AMC instances: {instance_id} not found.")


def verify_amc_request(**kwargs):
    # Verify AMC requests
    ads_kwargs = tasks.get_ads_token(**kwargs, redirect_uri="None")
    if ads_kwargs.get("authorize_url"):
        raise RuntimeError("Unauthorized AMC request.")
    return ads_kwargs


def update_upload_failures_table(response, dataset_id, instance_id):
    logger.info(f"Response code: {response.status_code}\n")
    logger.info("Response: " + response.text)
    upload_failures_table, dynamo_resource = get_dynamo_table(
        UPLOAD_FAILURES_TABLE_NAME
    )
    item_key = {"dataset_id": dataset_id, "instance_id": instance_id}
    # Clear previously recorded failure item.
    try:
        upload_failures_table.delete_item(Key=item_key)
    except dynamo_resource.meta.client.exceptions.ConditionalCheckFailedException:
        pass
    # If this upload failed then record that failure.
    if response.status_code != 200:
        item = item_key
        item["Value"] = response.text
        upload_failures_table.put_item(Item=item)

def safe_json_loads(val):
    try:
        return json.loads(val)
    except Exception:
        return val


def _start_upload(**kwargs):
    try:
        logger.info("Uploading dataset")
        bucket = kwargs["bucket"]
        key = kwargs["key"]

        # s3Key must be in the following format:
        #   amc/[dataset_id]/[update_strategy]/[country_code]/[instance_id|user_id]/[datafile].gz

        _, dataset_id, update_strategy, file_format, country_code, instance_id_user_id, filename_quoted = key.split('/')
        instance_id, user_id = instance_id_user_id.split("|")
        filename = urllib.parse.unquote_plus(filename_quoted)
        ads_kwargs = verify_amc_request(**kwargs, user_id=user_id)
        amc_instance = get_amc_instance(instance_id=instance_id)
        kwargs["marketplace_id"] = amc_instance["marketplace_id"]
        kwargs["advertiser_id"] = amc_instance["advertiser_id"]
        kwargs["instance_id"] = instance_id
        kwargs["user_id"] = user_id

        logger.info("key: " + key)
        logger.info("dataset_id: " + dataset_id)
        logger.info("update_strategy: " + update_strategy)
        logger.info("country_code: " + country_code)
        logger.info("filename: " + filename)
        logger.info("instance_id: " + instance_id)
        logger.info(
            "Uploading s3://"
            + bucket
            + "/"
            + key
            + " to dataSetId "
            + dataset_id
        )
        # the glue script will always output a GZIP-compressed file
        data = {
            "countryCode": safe_json_loads(country_code),
            "updateStrategy": update_strategy,
            "compressionFormat": "GZIP",
            "dataSource": {
                "sourceS3Bucket": bucket,
                "sourceFileS3Key": key,
            },
            "fileFormat": {
                "jsonDataFormat": "LINES"
            }
        }
        if file_format == "CSV":
            data["fileFormat"] = {
                "csvDataFormat": {
                    "fieldDelimiter": ","
                }
            }
        elif file_format == "JSON":
            data["fileFormat"] = {
                "jsonDataFormat": "LINES"
            }

        path = f"/uploads/{dataset_id}"
        amc_request = tasks.AMCRequests(
            amc_path=path,
            http_method="POST",
            payload=json.dumps(data)
        )
        response = amc_request.process_request(**kwargs, **ads_kwargs)
        update_upload_failures_table(response, dataset_id, instance_id)
        return response.text

    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": ex}


