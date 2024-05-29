# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from urllib.request import HTTPHandler, Request, build_opener


def send_response(event, context, response_status, response_data) -> None:
    """
    Send a resource manipulation status response to CloudFormation
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    response_body = json.dumps(
        {
            "Status": response_status,
            "Reason": f"See the details in CloudWatch Log Stream: {context.log_stream_name}",
            "PhysicalResourceId": context.log_stream_name,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "Data": response_data,
        }
    )

    logger.info(f"ResponseURL: {event['ResponseURL']}")
    logger.info(f"ResponseBody: {response_body}")
    opener = build_opener(HTTPHandler)
    request = Request(event["ResponseURL"], data=response_body.encode("utf-8"))
    request.add_header("Content-Type", "")
    request.add_header("Content-Length", str(len(response_body)))
    # Ensure that the HTTP method can be determined at runtime, just before the request is executed
    # by setting get_method to a callable (like a lambda function).
    request.get_method = lambda: "PUT"
    response = opener.open(request)
    logger.info(f"Status code: {response.getcode}")
    logger.info(f"Status message: {response.msg}")
