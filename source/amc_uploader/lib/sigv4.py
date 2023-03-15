# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###########################################################################
# Below are functions for constructing sigv4 signed HTTP requests
# Reference:
# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
#
# The requests package is not included in the default AWS Lambda env
# be sure that it has been provided in a Lambda layer.
#
##########################################################################

import hashlib
import hmac
import json
import logging
import os
import sys
from datetime import datetime

import boto3
import requests
from botocore import config
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
SOLUTION_VERSION = os.environ["SOLUTION_VERSION"]
solution_config = json.loads(os.environ["botoConfig"])
config = config.Config(**solution_config)
NO_ACCESS_KEY_ERROR = "No access key is available."
SIGNED_HEADERS = "host;x-amz-date;x-amz-security-token"


# This function gets authentication tokens for the AMC API
def get_amc_api_tokens():
    sts_client = boto3.client("sts", config=config)
    role_session_name = "amcufa_api_handler"
    logger.info("assuming role " + AMC_API_ROLE)
    assumed_role = sts_client.assume_role(
        RoleArn=AMC_API_ROLE, RoleSessionName=role_session_name
    )
    access_key = assumed_role["Credentials"]["AccessKeyId"]
    secret_key = assumed_role["Credentials"]["SecretAccessKey"]
    session_token = assumed_role["Credentials"]["SessionToken"]
    return access_key, secret_key, session_token


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key, date_stamp, region_name, service_name):
    kdate = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    kregion = sign(kdate, region_name)
    kservice = sign(kregion, service_name)
    ksigning = sign(kservice, "aws4_request")
    return ksigning


def send_request(
    request_url, headers, http_method, data=None, retry_on_500s=False
):
    logger.info("\nBEGIN REQUEST+++++++++++++++++++++++++++++++++++")
    logger.info(f"Request URL = {request_url}")

    http_method = http_method.lower()
    logger.info(f"HTTP_METHOD: {http_method}")

    session_requests = requests
    if retry_on_500s:
        max_retry = 5
        session_requests = requests.Session()
        retries = Retry(
            total=max_retry,
            backoff_factor=0.2,
            status_forcelist=[504],
            allowed_methods=frozenset(["GET", "DELETE", "POST", "PUT"]),
        )
        session_requests.mount("https://", HTTPAdapter(max_retries=retries))
        logger.info(f"Retry: {max_retry}")

    response = None
    if data:
        response = getattr(session_requests, http_method)(
            request_url, headers=headers, data=data
        )
    else:
        response = getattr(session_requests, http_method)(
            request_url, headers=headers
        )

    logger.info("\nRESPONSE+++++++++++++++++++++++++++++++++++")
    logger.info(f"Response code: {response.status_code}\n")
    logger.info(response.text)
    return response


def get_canonical_headers(domain_name, amzdate, session_token):
    return f"host:{domain_name}\nx-amz-date:{amzdate}\nx-amz-security-token:{session_token}\n"


def get_authorization_header(
    algorithm, access_key, credential_scope, signed_headers, signature
):
    return f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"


class Sigv4:
    def __init__(
        self,
        base_url,
        http_method,
        path,
        request_parameters=None,
        payload=None,
        **kwargs,
    ) -> None:
        self.base_url = base_url
        self.http_method = http_method.upper()
        self.payload = payload
        self.path = path
        self.payload = payload or ""
        self.request_parameters = request_parameters or ""
        self.retry_on_500s = kwargs.get("retry_on_500s", False)

    def process_request(self):
        # ************* REQUEST VALUES *************
        access_key, secret_key, session_token = get_amc_api_tokens()
        method = self.http_method
        service = "execute-api"
        region = os.environ["AWS_REGION"]
        endpoint = f"{self.base_url}{self.path}"
        domain_name = endpoint.split("/")[2]

        # Read AWS access key from env. variables or configuration file. Best practice is NOT
        # to embed credentials in code.
        if access_key is None or secret_key is None:
            logger.error(NO_ACCESS_KEY_ERROR)
            sys.exit()

        # Create a date for headers and the credential string
        t_date = datetime.utcnow()
        amzdate = t_date.strftime("%Y%m%dT%H%M%SZ")
        datestamp = t_date.strftime(
            "%Y%m%d"
        )  # Date w/o time, used in credential scope

        # ************* TASK 1: CREATE A CANONICAL REQUEST *************
        # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html

        # Step 1 is to define the verb (GET, POST, etc.)--already done.

        # Step 2: Create canonical URI--the part of the URI from domain to query
        # string (use '/' if no path)

        # ************* TASK 1: CREATE A CANONICAL REQUEST *************
        # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html

        # Step 1 is to define the verb (GET, POST, etc.)--already done.

        # Step 2: Create canonical URI--the part of the URI from domain to query
        # string (use '/' if no path)
        canonical_uri = "/" + "/".join(endpoint.split("/")[3:])

        # Step 3: Create the canonical query string. In this example (a GET request),
        # request parameters are in the query string. Query string values must
        # be URL-encoded (space=%20). The parameters must be sorted by name.
        # For this example, the query string is pre-formatted in the request_parameters variable.
        canonical_querystring = self.request_parameters

        # Step 4: Create the canonical headers and signed headers. Header names
        # must be trimmed and lowercase, and sorted in code point order from
        # low to high. Note that there is a trailing \n.
        canonical_headers = get_canonical_headers(
            domain_name, amzdate, session_token
        )

        # Step 5: Create the list of signed headers. This lists the headers
        # in the canonical_headers list, delimited with ";" and in alpha order.
        # Note: The request can include any headers; canonical_headers and
        # signed_headers lists those that you want to be included in the
        # hash of the request. "Host" and "x-amz-date" are always required.
        signed_headers = SIGNED_HEADERS

        # Step 6: Create payload hash (hash of the request body content). For GET
        # requests, the payload is an empty string ("").
        payload_hash = hashlib.sha256(self.payload.encode("utf-8")).hexdigest()

        # Step 7: Combine elements to create canonical request
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        # ************* TASK 2: CREATE THE STRING TO SIGN*************
        # Match the algorithm to the hashing algorithm you use, either SHA-1 or
        # SHA-256 (recommended)
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        # ************* TASK 3: CALCULATE THE SIGNATURE *************
        # Create the signing key using the function defined above.
        signing_key = get_signature_key(secret_key, datestamp, region, service)

        # Sign the string_to_sign using the signing_key
        signature = hmac.new(
            signing_key, (string_to_sign).encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # ************* TASK 4: ADD SIGNING INFORMATION TO THE REQUEST *************
        # The signing information can be either in a query string value or in
        # a header named Authorization. This code shows how to use a header.
        # Create authorization header and add to request headers
        authorization_header = get_authorization_header(
            algorithm, access_key, credential_scope, signed_headers, signature
        )

        # The request can include any headers, but MUST include "host", "x-amz-date",
        # and (for this scenario) "Authorization". "host" and "x-amz-date" must
        # be included in the canonical_headers and signed_headers, as noted
        # earlier. Order here is not significant.
        # Python note: The 'host' header is added automatically by the Python 'requests' library.
        headers = {
            "Authorization": authorization_header,
            "x-amz-date": amzdate,
            "x-amz-security-token": session_token,
            "x-amzn-service-name": SOLUTION_NAME,
            "x-amzn-service-version": SOLUTION_VERSION,
        }

        # ************* SEND THE REQUEST *************

        if canonical_querystring:
            endpoint = f"{endpoint}?{canonical_querystring}"

        return send_request(
            request_url=endpoint,
            headers=headers,
            http_method=method,
            data=self.payload,
            retry_on_500s=self.retry_on_500s,
        )


def delete(base_url, path):
    sig_response = Sigv4(
        base_url=base_url, path=path, http_method="DELETE", retry_on_500s=True
    )
    return sig_response.process_request()


def get(base_url, path, request_parameters=None):
    sig_response = Sigv4(
        base_url=base_url,
        path=path,
        http_method="GET",
        request_parameters=request_parameters,
        retry_on_500s=True,
    )
    return sig_response.process_request()


def put(base_url, path, body_data, **kwargs):
    sig_response = Sigv4(
        base_url=base_url,
        path=path,
        http_method="PUT",
        payload=body_data,
        retry_on_500s=kwargs.get("retry_on_500s", False),
    )
    return sig_response.process_request()


def post(base_url, path, body_data, **kwargs):
    sig_response = Sigv4(
        base_url=base_url,
        path=path,
        http_method="POST",
        payload=body_data,
        retry_on_500s=kwargs.get("retry_on_500s", False),
    )
    return sig_response.process_request()
