# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import logging
import os
import re

import awswrangler as wr
import boto3
from aws_xray_sdk.core import patch_all
from botocore import config
from chalice import (
    BadRequestError,
    Chalice,
    ChaliceViewError,
    IAMAuthorizer,
    Response,
)
from chalicelib.sigv4 import sigv4

solution_config = json.loads(os.environ["botoConfig"])
config = config.Config(**solution_config)

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

# Patch libraries to instrument downstream calls
patch_all()

# Initialization
app = Chalice(app_name="amcufa_api")
authorizer = IAMAuthorizer()

# Environment variables
VERSION = os.environ["VERSION"]
AMC_GLUE_JOB_NAME = os.environ["AMC_GLUE_JOB_NAME"]
CUSTOMER_MANAGED_KEY = os.environ["CUSTOMER_MANAGED_KEY"]
AMC_API_ROLE_ARN = os.environ["AMC_API_ROLE_ARN"]
ARTIFACT_BUCKET = os.environ["ARTIFACT_BUCKET"]
SYSTEM_TABLE_NAME = os.environ["SYSTEM_TABLE_NAME"]
UPLOAD_FAILURES_TABLE_NAME = os.environ["UPLOAD_FAILURES_TABLE_NAME"]

APPLICATION_JSON = "application/json"
DATA = "/data/"


@app.route(
    "/list_datasets", cors=True, methods=["POST"], authorizer=authorizer
)
def list_datasets():
    """
    List datasets in AMC.

    Returns:

    .. code-block:: python

        {"dataSets": [...]}
    """
    log_request_parameters()
    try:
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        path = "/dataSets"
        response = sigv4.get(destination_endpoint, path)
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/describe_dataset", cors=True, methods=["POST"], authorizer=authorizer
)
def describe_dataset():
    """
    Describe the schema and properties of an existing AMC dataset.

    Returns:

    .. code-block:: python

        {"dataSets": [...]}
    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body["dataSetId"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        path = "/dataSets/" + data_set_id
        response = sigv4.get(destination_endpoint, path)
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": str(e)}


@app.route(
    "/create_dataset", cors=True, methods=["POST"], authorizer=authorizer
)
def create_dataset():
    """
    Create a dataset in AMC.

    Returns AMC response:

    .. code-block:: python

        {}
    """
    log_request_parameters()
    try:
        body = app.current_request.json_body["body"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        if body["period"] == "autodetect":
            # Initialize the dataset period to P1D. This will be updated later
            # when the AWS Glue job measures the actual dataset period.
            body["period"] = "P1D"
        # If customer provided a CMK, then use the key to encrypt this dataset in AMC.
        if CUSTOMER_MANAGED_KEY != "":
            body["customerEncryptionKeyArn"] = CUSTOMER_MANAGED_KEY
        path = "/dataSets"
        response = sigv4.post(destination_endpoint, path, json.dumps(body))
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": str(e)}


@app.route(
    "/start_amc_transformation",
    cors=True,
    methods=["POST"],
    authorizer=authorizer,
)
def start_amc_transformation():
    """
    Invoke Glue job to prepare data for uploading into AMC.

    Returns AMC response:

    .. code-block:: python

        {"JobRunId": string}
    """
    log_request_parameters()
    try:
        source_bucket = app.current_request.json_body["sourceBucket"]
        source_key = app.current_request.json_body["sourceKey"]
        output_bucket = app.current_request.json_body["outputBucket"]
        pii_fields = app.current_request.json_body["piiFields"]
        deleted_fields = app.current_request.json_body["deletedFields"]
        timestamp_column = app.current_request.json_body["timestampColumn"]
        dataset_id = app.current_request.json_body["datasetId"]
        period = app.current_request.json_body["period"]
        country_code = app.current_request.json_body["countryCode"]
        session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
        destination_endpoints = app.current_request.json_body[
            "destination_endpoints"
        ]
        client = session.client("glue", config=config)
        args = {
            "--source_bucket": source_bucket,
            "--output_bucket": output_bucket,
            "--source_key": source_key,
            "--pii_fields": pii_fields,
            "--deleted_fields": deleted_fields,
            "--timestamp_column": timestamp_column,
            "--dataset_id": dataset_id,
            "--period": period,
            "--country_code": country_code,
            "--destination_endpoints": destination_endpoints,
        }
        logger.info("Starting Glue job:")
        logger.info("Equivalent AWS CLI command: ")
        # We've intentionally omitted a value for --profile in the
        # following command so the CLI reminds users to specify it.
        logger.info(
            "aws glue start-job-run --region "
            + os.environ["AWS_REGION"]
            + " --job-name "
            + AMC_GLUE_JOB_NAME
            + " --arguments '"
            + json.dumps(args)
            + "' --profile "
        )
        response = client.start_job_run(
            JobName=AMC_GLUE_JOB_NAME, Arguments=args
        )
        return {"JobRunId": response["JobRunId"]}
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route("/get_etl_jobs", cors=True, methods=["GET"], authorizer=authorizer)
def get_etl_jobs():
    """
    Retrieves metadata for all runs of a given Glue ETL job definition.

    Returns:

    .. code-block:: python

        {'JobRuns': [...]}
    """
    log_request_parameters()
    try:
        client = boto3.client("glue", config=config)
        response = client.get_job_runs(JobName=AMC_GLUE_JOB_NAME)
        for i in range(len(response["JobRuns"])):
            if "Arguments" in response["JobRuns"][i]:
                if response["JobRuns"][i]["Arguments"].get("--dataset_id"):
                    response["JobRuns"][i]["DatasetId"] = response["JobRuns"][
                        i
                    ]["Arguments"]["--dataset_id"]
        return json.loads(json.dumps(response, default=str))
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/upload_status", cors=True, methods=["POST"], authorizer=authorizer
)
def upload_status():
    """
    Get the status of an AMC data upload operation.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body["dataSetId"]
        upload_id = app.current_request.json_body["uploadId"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        path = DATA + data_set_id + "/uploads/" + upload_id
        response = sigv4.get(destination_endpoint, path)
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": str(e)}


@app.route("/list_uploads", cors=True, methods=["POST"], authorizer=authorizer)
def list_uploads():
    """
    List all the uploads for an AMC dataset.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body["dataSetId"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        next_token = ""
        if "nextToken" in app.current_request.json_body:
            next_token = app.current_request.json_body["nextToken"]
        path = DATA + data_set_id + "/uploads/"
        response = sigv4.get(
            destination_endpoint,
            path,
            request_parameters="nextToken=" + next_token,
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route("/list_upload_failures", cors=True, methods=["POST"], authorizer=authorizer)
def list_upload_failures():
    """
    List the upload failure message, if any exists, for a specified dataset and AMC instance.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    dynamo_resource = boto3.resource("dynamodb", config=config)
    try:
        dataset_id = app.current_request.json_body["dataset_id"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        item_key = {"destination_endpoint": destination_endpoint, "dataset_id": dataset_id}
        upload_failures_table = dynamo_resource.Table(UPLOAD_FAILURES_TABLE_NAME)
        item = upload_failures_table.get_item(Key=item_key, ConsistentRead=True)
        error_message = ""
        if "Item" in item:
            error_message = item["Item"]["Value"]
        return Response(
            body=error_message,
            status_code=200
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/delete_dataset", cors=True, methods=["POST"], authorizer=authorizer
)
def delete_dataset():
    """
    Delete an AMC dataset and all the records uploaded to it.

    Returns AMC response:

    .. code-block:: python

        {}

    """
    log_request_parameters()
    try:
        dataset_id = app.current_request.json_body["dataSetId"]
        destination_endpoint = app.current_request.json_body[
            "destination_endpoint"
        ]
        # Step 1/2: delete uploaded data
        # This should delete any data files that customers uploaded for either FACT or DIMENSION datasets
        current_datetime = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        path = (
            DATA
            + dataset_id
            + "?timeWindowStart=1970-01-01T00:00:00Z&timeWindowEnd="
            + current_datetime
        )
        sigv4.delete(destination_endpoint, path)
        path = "/dataSets/" + dataset_id
        response = sigv4.delete(destination_endpoint, path)
        if response.status_code == 200:
            dynamo_resource = boto3.resource("dynamodb", config=config)
            item_key = {"destination_endpoint": destination_endpoint, "dataset_id": dataset_id}
            logger.info("Removing upload record from " + UPLOAD_FAILURES_TABLE_NAME +
                        " if the following key exists:" +
                        json.dumps(item_key))
            upload_failures_table = dynamo_resource.Table(UPLOAD_FAILURES_TABLE_NAME)
            try:
                upload_failures_table.delete_item(Key=item_key)
            except dynamo_resource.meta.client.exceptions.ConditionalCheckFailedException:
                pass
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": APPLICATION_JSON},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route("/version", cors=True, methods=["GET"], authorizer=authorizer)
def version():
    """
    Get the solution version number.

    Returns:

    .. code-block:: python

        {"Version": string}
    """
    log_request_parameters()
    stack_version = {"version": VERSION}
    return stack_version


@app.route(
    "/list_bucket",
    cors=True,
    methods=["POST"],
    content_types=[APPLICATION_JSON],
    authorizer=authorizer,
)
def list_bucket():
    """List the contents of a user-specified S3 bucket

    Body:

    .. code-block:: python

        {
            "s3bucket": string
        }


    Returns:
        A list of S3 keys (i.e. paths and file names) for all objects in the bucket.

        .. code-block:: python

            {
                "objects": [{
                    "key": string
                    },
                    ...
            }

    Raises:
        500: ChaliceViewError - internal server error
    """
    log_request_parameters()
    try:
        s3_obj = boto3.resource("s3", config=config)
        bucket = json.loads(app.current_request.raw_body.decode())["s3bucket"]
        results = []
        for s3object in s3_obj.Bucket(bucket).objects.all():
            results.append(
                {
                    "key": s3object.key,
                    "last_modified": s3object.last_modified.isoformat(),
                    "size": s3object.size,
                }
            )
        return json.dumps(results)
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/get_data_columns",
    cors=True,
    methods=["POST"],
    content_types=[APPLICATION_JSON],
    authorizer=authorizer,
)
def get_data_columns():
    """Get the column names and file format of a user-specified JSON or CSV file

    Body:

    .. code-block:: python

        {
            "s3bucket": string,
            "s3key": string
        }


    Returns:
        List of column names and data types found in the first row of
        the user-specified data file.
        Also returns the content_type, "application/json" or  "text/csv", of the data file.

        .. code-block:: python

            {
                "columns": [string, string, ...],
                "content_type": string
            }

    Raises:
        500: ChaliceViewError - internal server error
    """

    log_request_parameters()
    try:
        bucket = json.loads(app.current_request.raw_body.decode())["s3bucket"]
        keys = json.loads(app.current_request.raw_body.decode())["s3key"]
        keys_to_validate = [x.strip() for x in keys.split(",")]

        json_content_type = APPLICATION_JSON
        csv_content_type = "text/csv"
        plain_text_content_type = "text/plain"
        gzip_content_type = "application/x-gzip"
        input_gzip_content_type = ""
        content_type = ""

        # for concurrent glue jobs, can only run a max of 200 per account
        if len(keys_to_validate) > 200:
            return Response(
                body={
                    "message": "Number of files selected cannot exceed 200."
                },
                status_code=400,
                headers={"Content-Type": plain_text_content_type},
            )
        # get first columns to compare against to ensure all files have same schema
        base_key = keys_to_validate[0]

        for key in keys_to_validate:
            s3_obj = boto3.client("s3", config=config)
            response = s3_obj.head_object(Bucket=bucket, Key=key)
            is_gzip_file = bool(response["ContentType"] == gzip_content_type)

            # determine if .json.gz or .csv.gz
            if is_gzip_file:
                input_gzip_content_type = check_input_gzip_content_type(
                    key=key
                )

            # Return an error if user selected a combination
            # of CSV and JSON files.
            content_type = validate_file_format_match(
                response=response,
                content_type=content_type,
                is_gzip_file=is_gzip_file,
                input_gzip_content_type=input_gzip_content_type,
            )

            # Read first row
            logger.info("Reading " + "s3://" + bucket + "/" + key)

            if json_content_type in (content_type, gzip_content_type):
                dfs = wr.s3.read_json(
                    path=["s3://" + bucket + "/" + key],
                    chunksize=1,
                    lines=True,
                )
            elif csv_content_type in (content_type, gzip_content_type):
                dfs = wr.s3.read_csv(
                    path=["s3://" + bucket + "/" + key], chunksize=1
                )
            else:
                return Response(
                    body={"message": "File format must be CSV or JSON."},
                    status_code=400,
                    headers={"Content-Type": plain_text_content_type},
                )
            chunk = next(dfs)
            columns = list(chunk.columns.values)

            if key == base_key:
                base_columns = columns
                result = json.dumps(
                    {"columns": base_columns, "content_type": content_type}
                )

            if set(columns) != set(base_columns):
                error_text = (
                    "Schemas must match for each file. The schemas in "
                    + key
                    + " and "
                    + base_key
                    + " do not match."
                )
                logger.error(error_text)
                return Response(
                    body={"message": error_text},
                    status_code=400,
                    headers={"Content-Type": plain_text_content_type},
                )

        return result
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


# Helper function to check if GZIP file is JSON or CSV format
def check_input_gzip_content_type(key):
    json_content_type = APPLICATION_JSON
    csv_content_type = "text/csv"

    # regex file name to see if json.gz
    if re.search(r"\.json\.gz$", key):
        input_gzip_content_type = json_content_type

    # regex file name to see if csv.gz
    elif re.search(r"\.csv\.gz$", key):
        input_gzip_content_type = csv_content_type

    return input_gzip_content_type


# Helper function to validate if file types are compatible for upload
def validate_file_format_match(
    response, content_type, is_gzip_file, input_gzip_content_type
):
    plain_text_content_type = "text/plain"

    if content_type == "":
        if is_gzip_file:
            content_type = input_gzip_content_type
        else:
            content_type = response["ContentType"]
    elif content_type not in (
        response["ContentType"],
        input_gzip_content_type,
    ):
        return Response(
            body={
                "message": "Files must all have the same format (CSV or JSON)."
            },
            status_code=400,
            headers={"Content-Type": plain_text_content_type},
        )
    return content_type


# Validate the AmcInstances parameter
def validate_amc_system_parameter(system_parameter):
    if "Name" not in system_parameter:
        raise BadRequestError("Missing system parameter Name")
    if system_parameter["Name"] != "AmcInstances":
        raise BadRequestError(
            "Unrecognized system parameter, " + system_parameter["Name"]
        )
    amc_instances = system_parameter["Value"]
    if not isinstance(amc_instances, list):
        raise BadRequestError("AmcInstances value must be of type list")
    if len(amc_instances) > 500:
        # We limit the number of registered AMC instances to 500 so that
        # the normalized S3 Bucket policy does not exceed maximum allowed length (20480 bytes)
        raise BadRequestError("AmcInstance list must be shorter than 500")
    for i in range(len(amc_instances)):
        if not isinstance(amc_instances[i], dict):
            raise BadRequestError("AmcInstance value must be of type dict")
        for key_check in ["endpoint", "data_upload_account_id"]:
            if key_check not in amc_instances[i]:
                raise BadRequestError(
                    f"AmcInstance value must contain key, '{key_check}'"
                )


@app.route(
    "/system/configuration",
    cors=True,
    methods=["POST"],
    content_types=[APPLICATION_JSON],
    authorizer=authorizer,
)
def save_system_configuration():
    """Add a new system configuration parameter
    - Updates the system configuration with a new parameter or changes the value of
      existing parameters
    Body:
    .. code-block:: python
        {
            "Name": "ParameterName",
            "Value": "ParameterValue"
        }
    Supported parameters:
        "Name": "AmcInstances",
        "Value": {"endpoint": string, "data_upload_account_id": string, ...}
            Saves a list of AMC instances and their associated attributes.
    Returns:
        None
    Raises:
        500: ChaliceViewError - internal server error
    """
    log_request_parameters()
    iam_client = boto3.client("iam", config=config)
    s3_client = boto3.client("s3", config=config)
    dynamo_resource = boto3.resource("dynamodb", config=config)

    try:
        system_parameter = json.loads(app.current_request.raw_body.decode())
        logger.info(json.loads(app.current_request.raw_body.decode()))
        system_table = dynamo_resource.Table(SYSTEM_TABLE_NAME)
        validate_amc_system_parameter(system_parameter=system_parameter)
    except Exception as ex:
        logger.error("Exception: {}".format(ex))
        return {"Status": "Error", "Message": str(ex)}

    system_table.put_item(Item=system_parameter)
    try:
        logger.info("reading bucket policy")
        # Get the bucket policy for the ArtifactBucket.
        result = s3_client.get_bucket_policy(Bucket=ARTIFACT_BUCKET)
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
            data_upload_account_ids = set()
            endpoints = set()
            for item in amc_instances:
                data_upload_account_ids.add(item["data_upload_account_id"])
                endpoints.add(item["endpoint"])
            data_upload_account_ids = list(data_upload_account_ids)
            endpoints = list(endpoints)
            # Construct a bucket policy statement with a principal that includes
            # each data upload account id.
            data_upload_statement = (
                '{"Sid": "AllowDataUploadFromAmc", '
                + '"Effect": "Allow", '
                + '"Principal": {"AWS": ['
            )
            for i in range(len(data_upload_account_ids) - 1):
                data_upload_statement += (
                    '"arn:aws:iam::' + data_upload_account_ids[i] + ':root", '
                )
            data_upload_statement += (
                '"arn:aws:iam::' + data_upload_account_ids[-1] + ':root"]'
            )
            data_upload_statement += (
                "}, "
                + '"Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket"], '
                + '"Resource": ["arn:aws:s3:::'
                + ARTIFACT_BUCKET
                + '/*", '
                + '"arn:aws:s3:::'
                + ARTIFACT_BUCKET
                + '"]}'
            )
            # Remove the old "AllowDataUploadFromAmc" statement from the bucket policy.
            other_statements = [
                x
                for x in policy["Statement"]
                if not ("Sid" in x and x["Sid"] == "AllowDataUploadFromAmc")
            ]
            # Add the new "AllowDataUploadFromAmc" statement to the bucket policy
            policy["Statement"] = [
                json.loads(data_upload_statement)
            ] + other_statements
            # Save the new bucket policy
            logger.info("new bucket policy:")
            logger.info(json.dumps(policy))
            logger.info("saving bucket policy")
            result = s3_client.put_bucket_policy(
                Bucket=ARTIFACT_BUCKET, Policy=json.dumps(policy)
            )
            logger.info(json.dumps(result))

            # Add permission to use the AMC API endpoint from the AMC_API_ROLE
            amc_endpoint_access_policy = iam_client.get_role_policy(
                RoleName=AMC_API_ROLE_ARN.split("/")[1],
                PolicyName="AmcApiAccess",
            )
            other_statements = [
                x
                for x in amc_endpoint_access_policy["PolicyDocument"][
                    "Statement"
                ]
                if not ("Sid" in x and x["Sid"] == "AmcEndpointAccessPolicy")
            ]
            endpoint_arns = [
                '"arn:aws:execute-api:*:*:'
                + x.split("/")[2].split(".")[0]
                + '/*"'
                for x in endpoints
            ]
            endpoint_arns_string = ", ".join(
                str(item) for item in endpoint_arns
            )
            amc_endpoint_statement = (
                '{"Sid": "AmcEndpointAccessPolicy", "Action": ["execute-api:Invoke"], "Resource": ['
                + endpoint_arns_string
                + '], "Effect": "Allow"}'
            )
            amc_endpoint_access_policy["PolicyDocument"][
                "Statement"
            ] = other_statements + [json.loads(amc_endpoint_statement)]
            iam_client.put_role_policy(
                RoleName=AMC_API_ROLE_ARN.split("/")[1],
                PolicyName="AmcApiAccess",
                PolicyDocument=json.dumps(
                    amc_endpoint_access_policy["PolicyDocument"]
                ),
            )
    except Exception as ex:
        logger.error("Exception {}".format(ex))
        return {"Status": "Error", "Message": str(ex)}
    return {}


@app.route(
    "/system/configuration", cors=True, methods=["GET"], authorizer=authorizer
)
def get_system_configuration():
    """Get the current system configuration
    - Gets the current system configuration parameter settings
    Returns:
        A list of dict containing the current system configuration key-value pairs.
        .. code-block:: python
            [
                {
                "Name": "Value"
                },
            ...]
    Raises:
        200: The system configuration was returned successfully.
        500: ChaliceViewError - internal server error
    """
    dynamodb_resource = boto3.resource("dynamodb", config=config)
    try:
        system_table = dynamodb_resource.Table(SYSTEM_TABLE_NAME)
        # Check if any configuration has been added yet
        response = system_table.scan(ConsistentRead=True)
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError from e
    return response["Items"]


def log_request_parameters():
    logger.info("Processing the following request:\n")
    logger.info(
        "resource path: " + app.current_request.context["resourcePath"]
    )
    logger.info("method: " + app.current_request.method)
    logger.info("uri parameters: " + str(app.current_request.uri_params))
    logger.info("query parameters: " + str(app.current_request.query_params))
    logger.info(
        "request ID: " + (app.current_request.context.get("requestId", ""))
    )
    logger.info("request body: " + app.current_request.raw_body.decode())
    logger.debug(app.current_request.to_dict())
