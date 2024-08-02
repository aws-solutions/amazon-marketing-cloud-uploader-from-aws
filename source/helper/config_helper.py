# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
This custom resource creates and writes the configuration file for the web application after
most other resources have been created.

For 'Create' and 'Update' events, this function combines configuration parameters (including
AWS Cognito and S3 resource details) into a JSON structure and uploads it to an S3 bucket.
For 'Delete' events, it removes the file.

Parameters:
- event (Dict): Contains CloudFormation event data, including request type and resource properties.
- context (Any): Provides AWS Lambda runtime information.

The event data must include specific properties such as API_ENDPOINT, AWS_REGION, USER_POOL_ID,
and others relevant to the AWS resources in use. This function assumes IAM permissions to write
to the specified S3 bucket and prefix are in place.
"""

import json
import logging
from typing import Any, Dict

import boto3
from cf_helper import send_response

WEB_RUNTIME_CONFIG = "runtimeConfig.json"


def handler(event: Dict[str, Any], context: Any) -> None:
    """Handles CloudFormation custom resource requests."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    try:
        request_type = event["RequestType"]
        properties = event["ResourceProperties"]
        response_data = {"Message": ""}
        logger.info(
            f"Resource properties: {json.dumps(properties, default=str)}, request_type: {request_type}"
        )
        s3 = boto3.client("s3")
        if request_type in ["Create", "Update"]:
            data = {
                k: properties[k]
                for k in [
                    "API_ENDPOINT",
                    "AWS_REGION",
                    "USER_POOL_ID",
                    "USER_POOL_CLIENT_ID",
                    "IDENTITY_POOL_ID",
                    "DATA_BUCKET_NAME",
                    "HOSTED_UI_DOMAIN",
                    "COGNITO_CALLBACK_URL",
                    "COGNITO_LOGOUT_URL",
                    "ARTIFACT_BUCKET_NAME",
                    "ENCRYPTION_MODE"
                ]
            }
            s3.put_object(
                Bucket=properties["WEBSITE_BUCKET"],
                Key=WEB_RUNTIME_CONFIG,
                Body=json.dumps(data, indent=4),
            )
            response_data = {"Message": f"Put {WEB_RUNTIME_CONFIG}"}

        # Send success response back to CloudFormation for Create/Update and Delete
        send_response(event, context, "SUCCESS", response_data)

    except Exception as handler_exception:
        logger.exception(handler_exception)
        send_response(event, context, "FAILED", {"Message": str(handler_exception)})
