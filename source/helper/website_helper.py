# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
PURPOSE:
  * Copy files for the website from a source build bucket to a deployment bucket.
  * This function starts as a CloudFormation custom resource in deployment/web.yaml.
"""


import json
import logging

import boto3
from cf_helper import send_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource("s3")
s3_client = boto3.client("s3")


def copy_source(event):
    """
    Copies source files for a web application from a source S3 bucket to a deployment S3 bucket.

    Parameters:
    - event (dict): The event triggering this function, expected to contain `ResourceProperties` with keys
      `WebsiteCodeBucket` (source S3 bucket), `WebsiteCodePrefix` (prefix in source bucket), and
      `DeploymentBucket` (deployment S3 bucket, domain name format).
    - context: The context in which the function is called, not used in this function.

    Notes:
    - The deployment bucket name is derived by stripping the domain part from the `DeploymentBucket` value.
    - It assumes that the `webapp-manifest.json` file is present in the root directory where the function is executed
      and contains a JSON object with keys representing the file paths to be copied.
    """

    source_bucket = event["ResourceProperties"]["WebsiteCodeBucket"]
    source_key = event["ResourceProperties"]["WebsiteCodePrefix"]
    # Assuming 'DeploymentBucket' always has a domain part to strip off.
    website_bucket = event["ResourceProperties"]["DeploymentBucket"].split(
        "."
    )[0]

    with open("./webapp-manifest.json", encoding="utf-8") as file:
        manifest = json.load(file)
        logger.info("UPLOADING FILES:")
        for key in manifest:
            logger.info(f"s3://{source_bucket}/{source_key}/{key}")
            s3.meta.client.copy(
                {"Bucket": source_bucket, "Key": f"{source_key}/{key}"},
                website_bucket,
                key,
            )


def lambda_handler(event, context):
    """
    Processes events from AWS Lambda, routing them based on request type.

    Parameters:
    - event (dict): The event dictionary received from AWS Lambda, containing details
      about the specific request, such as the request type and resource properties.
    - context: The context object provided by AWS Lambda, containing metadata about
      the invocation, function, and execution environment.

    The function logs both the received event and context for debugging purposes and
    ensures a response is sent back to the CloudFormation service, indicating the
    outcome of the operation.
    """
    try:
        # Log the received event and context for debugging.
        logger.info(f"REQUEST RECEIVED:\n {event}")
        logger.info(f"CONTEXT RECEIVED:\n {context}")

        # Determine the request type from the event and call the appropriate function.
        request_type = event["RequestType"]
        if request_type in ["Create", "Update"]:
            copy_source(event)

        # On successful execution, send a success response back.
        send_response(
            event, context, "SUCCESS", {"Message": "Operation successful"}
        )
    except Exception as handler_exception:
        # Log the exception and send a failure response back in case of errors.
        logger.exception(handler_exception)
        send_response(
            event,
            context,
            "FAILED",
            {"Message": f"Exception during processing: {handler_exception}"},
        )
