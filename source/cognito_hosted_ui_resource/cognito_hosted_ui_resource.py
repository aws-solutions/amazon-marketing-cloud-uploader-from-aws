# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import logging

import boto3
import cfnresponse



logger = logging.getLogger()
logger.setLevel(logging.INFO)

USER_POOL_ID = os.environ["USER_POOL_ID"]
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

def handler(event, context):
    logger.info(f"Event {event}")

    try:
        client = boto3.client('cognito-idp')
        response = client.set_ui_customization(
            UserPoolId=USER_POOL_ID,
            CSS=get_file(f"{DIR_PATH}/login.css", "r"),
            ImageFile=get_file(f"{DIR_PATH}/amcufa-logo.png", "rb")
        )
        logger.info(response)
    except Exception as error:
        logger.error(error)
        cfnresponse.send(event, context, cfnresponse.FAILED, {"error": error})
        return
    
    cfnresponse.send(event, context, cfnresponse.SUCCESS, {"response": response})

def get_file(file_path, mode):
    with open(file_path, mode) as file:
        return file.read()