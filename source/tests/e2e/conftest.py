# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import boto3
import pytest

# Fixture for retrieving env variables


@pytest.fixture(scope="session")
def test_environment():
    print("Setting variables for tests")
    try:
        test_env_vars = {
            'REGION': os.environ['REGION'],
            'STACK_NAME': os.environ['STACK_NAME'],
            'ACCESS_KEY': os.environ['AWS_ACCESS_KEY_ID'],
            'SECRET_KEY': os.environ['AWS_SECRET_ACCESS_KEY'],
            'EMAIL': os.environ['EMAIL'],
            'PASSWORD': os.environ['PASSWORD'],
            'DATA_BUCKET_NAME': os.environ['DATA_BUCKET_NAME']
        }

    except KeyError as e:
        logging.error(
            "ERROR: Missing a required environment variable for testing: {variable}".format(
                variable=e
            )
        )
        raise Exception(e)
    else:
        return test_env_vars


# Fixture for stack resources
@pytest.fixture(scope="session")
def stack_resources(test_environment):
    print("Getting stack outputs")
    resources = {}
    client = boto3.client(
        "cloudformation", region_name=test_environment["REGION"]
    )
    response = client.describe_stacks(StackName=test_environment["STACK_NAME"])
    outputs = response["Stacks"][0]["Outputs"]
    for output in outputs:
        resources[output["OutputKey"]] = output["OutputValue"]
    return resources
