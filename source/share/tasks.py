# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###########################################################################
# This file contains functions for constructing sigv4 signed HTTP requests
# Reference:
# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
#
# The requests package is not included in the default AWS Lambda env
# be sure that it has been provided in a Lambda layer.
#
##########################################################################

import json
import logging
import os
import urllib.parse
from functools import wraps
from chalice import Response
import boto3
import requests
from botocore import config
from botocore.exceptions import ClientError
from requests.adapters import HTTPAdapter, Retry

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

# Environment variables
AMC_API_ROLE = os.environ["AMC_API_ROLE_ARN"]
SOLUTION_NAME = os.environ["SOLUTION_NAME"]
SOLUTION_VERSION = os.environ.get(
    "VERSION", os.environ.get("SOLUTION_VERSION")
)
solution_config = json.loads(os.environ["botoConfig"])
config = config.Config(**solution_config)
NO_ACCESS_KEY_ERROR = "No access key is available."
DELETE_STRING = "TOKEN_DELETED"
ADS_SCOPE = "profile%20advertising::campaign_management"


def safe_json_loads(obj):
    try:
        return json.loads(obj)
    except json.decoder.JSONDecodeError:
        return obj


def send_request(
    request_url, headers, http_method, data=None, params=None
):
    logger.info("\nBEGIN REQUEST+++++++++++++++++++++++++++++++++++")
    logger.info(f"Request URL = {request_url}")
    logger.info(f"HTTP_METHOD: {http_method}")

    # Retry requests that receive server error (5xx) or throttling errors 429.
    with (requests.Session() as session_request):
        max_retry = 10
        retries = Retry(
            total=max_retry,
            backoff_factor=0.5,
            status_forcelist=[504, 500, 429],
            allowed_methods=frozenset(["GET", "DELETE", "POST", "PUT"]),
        )
        session_request.mount("https://", HTTPAdapter(max_retries=retries))
        logger.info(f"Retry: {max_retry}")

        response = session_request.request(
            method=http_method,
            url=request_url,
            headers=headers,
            data=data,
            params=params
        )

        logger.info("\nRESPONSE+++++++++++++++++++++++++++++++++++")
        logger.info(f"Response code: {response.status_code}\n")
        logger.info(f"Response keys: {response.json().keys()}\n")
        return response


def create_update_secret(secret_id, secret_string):
    session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
    client = session.client(service_name="secretsmanager", config=config)
    if isinstance(secret_string, dict):
        secret_string = json.dumps(secret_string)
    client.update_secret(SecretId=secret_id, SecretString=secret_string)


def get_secret(secret_id):
    session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
    client = session.client(service_name="secretsmanager", config=config)
    res = client.get_secret_value(
        SecretId=secret_id,
    )
    return safe_json_loads(res["SecretString"])

# This function returns CLIENT_ID and CLIENT_SECRET from env variables or None if they don't exist.
def get_client_id_secret_env():
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")
    logger.info(
        f"Retrieved client_id {client_id} and secret {client_secret} from env declared variables."
    )
    return client_id, client_secret


def format_client_secret_id(user_id):
    return f"{os.environ['STACK_NAME']}-{user_id}"


def get_ads_token(**kwargs):
    #
    # This function is used to add oAuth authentication to a wrapped function.
    # Every function that performs an AMC request should be wrapped by this
    # function.
    #
    # Inputs:
    #  - kwargs will include all the kwarg values which were passed to the
    #    wrapped function. authorize_amc_request() will insert new values into
    #    the wrapped function's kwargs so that it can construct oAuth headers.
    #
    # Outputs:
    #   - Returns authorize_url in kwargs if refresh_token is missing or invalid
    #     and auth_code is not present.
    #   - Saves client_id, client_secret, and refresh_token to Secrets Manager if
    #     auth_code is present and returns dict containing client_id and
    #     refresh_token.
    #
    user_id = kwargs.get("user_id")
    secret_key = format_client_secret_id(user_id)
    try:
        secrets = get_secret(secret_key)
        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]
    except Exception as ex:
        logger.error(f"Error: {ex=}")
        return {"status_code": 400, "error_description": "Client Id and Client Secret are undefined."}

    redirect_uri = kwargs["redirect_uri"]
    state_params = ""
    if kwargs.get("state"):
        state_params = f'&state={kwargs.get("state")}'
    auth_code = kwargs.get("auth_code")
    if not auth_code:
        # Request access token from refresh token.
        if ("refresh_token" not in secrets or
                secrets["refresh_token"] == DELETE_STRING):
            # If refresh_token is absent then return the authorize_url
            # so client can initiate the authorization grant process.
            return {
                "authorize_url": f"https://www.amazon.com/ap/oa?client_id={client_id}&scope={ADS_SCOPE}&response_type=code&redirect_uri={redirect_uri}{state_params}"
            }

        refresh_token = secrets["refresh_token"]
        code_payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    else:
        # Request access token from auth grant code.
        code_payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
        }

    response = send_request(
        http_method="POST",
        request_url="https://api.amazon.com/auth/o2/token",
        headers=None,
        data={
            **code_payload,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    if "refresh_token" in response.json():
        secret_value = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": response.json()["refresh_token"]
        }
        create_update_secret(secret_key, secret_value)

    return {"client_id": client_id, "status_code": response.status_code, **response.json()}


def get_redirect_uri(current_request):
    return f"{current_request.headers['origin']}/redirect"


def handle_app_requests(**kwargs):
    # kwargs will include a chalice.app.Chalice object
    app = kwargs.get("app")
    if hasattr(app, "current_request"):
        request_body = app.current_request.json_body
        request_body["redirect_uri"] = get_redirect_uri(app.current_request)
        return request_body
    if app:
        kwargs.pop("app")
    return kwargs


def authorize_amc_request(**app_kwargs):
    #
    # This decorator adds oAuth functionality to wrapped functions.
    #
    def authorize_amc_request_decorator(func):
        @wraps(func)
        def wrapper(**kwargs):
            try:
                ads_kwargs = get_ads_token(
                    **handle_app_requests(**app_kwargs), **kwargs
                )
                # Return oAuth errors to client. Reference:
                # https://developer.amazon.com/docs/app-submission-api/auth.html#3--handle-any-error-responses
                if "error_description" in ads_kwargs:
                    return Response(body={"message": ads_kwargs["error_description"]},
                                    headers={'Content-Type': 'application/json'},
                                    status_code=int(ads_kwargs["status_code"]))
                if ads_kwargs.get("authorize_url"):
                    return ads_kwargs
                return func(**kwargs, **ads_kwargs)
            except Exception as ex:
                return {"status": "error", "message": str(ex)}
        return wrapper
    return authorize_amc_request_decorator


class AMCRequests:
    def __init__(
        self,
        http_method,
        amc_path,
        payload=None,
        **kwargs,
    ) -> None:
        self.http_method = http_method.upper()
        self.amc_path = f"/{amc_path}".replace("//", "/")
        self.payload = payload or ""
        self.request_parameters = kwargs.get("request_parameters")
        self.is_amc_report = kwargs.get("is_amc_report", True)

    def process_request(self, **kwargs):

        amc_path = self.amc_path
        if self.is_amc_report:
            amc_path = f"/amc/advertiserData/{kwargs['instance_id']}{self.amc_path}"
        base_url = urllib.parse.urljoin(
            "https://advertising-api.amazon.com/", amc_path
        )

        headers = {
            "Amazon-Advertising-API-ClientId": kwargs["client_id"],
            "Authorization": f'Bearer {kwargs["access_token"]}',
            "Content-Type": "application/json",
            "x-amzn-service-name": "amazon-marketing-cloud-uploader-from-aws",
            "x-amzn-service-version": "v3.0.14"
        }

        if kwargs.get("advertiser_id"):
            headers["Amazon-Advertising-API-AdvertiserId"] = kwargs[
                "advertiser_id"
            ]
        if kwargs.get("marketplace_id"):
            headers["Amazon-Advertising-API-MarketplaceId"] = kwargs[
                "marketplace_id"
            ]

        logger.debug(f"AMC_REQUEST_URL: {base_url}")
        logger.debug(f"AMC_REQUEST_HEADERS: {headers}")
        logger.debug(f"AMC_REQUEST_PAYLOAD: {self.payload}")
        logger.debug(f"AMC_HTTP_METHOD: {self.http_method}")

        return send_request(
            request_url=base_url,
            headers=headers,
            http_method=self.http_method,
            data=self.payload,
            params=self.request_parameters,
        )


def apply_amc_bucket_permission():
    artifact_bucket = os.environ["ARTIFACT_BUCKET"]
    system_table_name = os.environ["SYSTEM_TABLE_NAME"]

    dynamo_resource = boto3.resource("dynamodb", config=config)
    system_table = dynamo_resource.Table(system_table_name)

    s3_client = boto3.client("s3", config=config)
    logger.info("reading bucket policy")
    # Get the bucket policy for the ArtifactBucket.
    result = s3_client.get_bucket_policy(Bucket=artifact_bucket)
    policy = json.loads(result["Policy"])
    # Get the AMC instances system configuration
    response = system_table.get_item(
        Key={"Name": "AmcInstances"}, ConsistentRead=True
    )
    # If there is at least one AMC instance...
    if "Item" in response and len(response["Item"]["Value"]) > 0:
        amc_instances = response["Item"]["Value"]
        # Get the list of data upload account ids associated with each AMC instance.
        # Use set type to avoid duplicates
        data_upload_account_ids = set([item["data_upload_account_id"] for item in amc_instances])
        # Construct a bucket policy statement with a principal that includes
        # each data upload account id.
        data_upload_accounts = [f"arn:aws:iam::{account_id}:root" for account_id in data_upload_account_ids]
        data_upload_statement = {
            "Sid": "AllowDataUploadFromAmc",
            "Effect": "Allow",
            "Principal": {"AWS": data_upload_accounts},
            "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket", "s3:GetObjectTagging", "s3:GetBucketTagging"],
            "Resource": [f"arn:aws:s3:::{artifact_bucket}/*", f"arn:aws:s3:::{artifact_bucket}"]
        }
        # Remove the old "AllowDataUploadFromAmc" statement from the bucket policy.
        other_statements = [
            x
            for x in policy["Statement"]
            if not ("Sid" in x and x["Sid"] == "AllowDataUploadFromAmc")
        ]
        # Add the new "AllowDataUploadFromAmc" statement to the bucket policy
        policy["Statement"] = [data_upload_statement] + other_statements
        # Save the new bucket policy
        logger.info("new bucket policy:")
        logger.info(json.dumps(policy))
        logger.info("saving bucket policy")
        try:
            result = s3_client.put_bucket_policy(
                Bucket=artifact_bucket, Policy=json.dumps(policy)
            )
            logger.info(json.dumps(result))
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'MalformedPolicy':
                print("Error: Invalid principal in policy. Please check the policy and try again.")
            else:
                print(f"An error occurred: {e}")
