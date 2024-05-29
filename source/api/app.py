# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

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
from chalicelib.tasks import tasks

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

DATA = "/data/"
JSON_CONTENT_TYPE = "application/json"
CSV_CONTENT_TYPE = "text/csv"
PLAIN_TEXT_CONTENT_TYPE = "text/plain"
GZIP_CONTENT_TYPE = "application/x-gzip"


@app.route(
    "/list_datasets", cors=True, methods=["POST"], authorizer=authorizer
)
@tasks.authorize_amc_request(app=app)
def list_datasets(**kwargs):
    """
    List datasets in AMC.

    Returns:

    .. code-block:: python

        {"dataSets": [...]}
    """
    log_request_parameters()
    try:
        amc_request = tasks.AMCRequests(
            amc_path="/dataSets/list",
            http_method="POST",
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        response_json = response.json()

        datasets = response_json.get('dataSets', [])
        while 'nextToken' in response_json:
            amc_request = tasks.AMCRequests(
                amc_path="/dataSets/list",
                http_method="POST",
                request_parameters={'nextToken': response_json['nextToken']}
            )
            response_json = amc_request.process_request(
                **kwargs, **app.current_request.json_body
            ).json()
            datasets.extend(response_json.get('dataSets', []))

        return Response(
            body=json.dumps({'dataSets': datasets}),
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/describe_dataset", cors=True, methods=["POST"], authorizer=authorizer
)
@tasks.authorize_amc_request(app=app)
def describe_dataset(**kwargs):
    """
    Describe the schema and properties of an existing AMC dataset.

    Returns:

    .. code-block:: python

        {"dataSets": [...]}
    """
    log_request_parameters()
    try:
        amc_request = tasks.AMCRequests(
            amc_path=f"/dataSets/{app.current_request.json_body.pop('dataSetId')}",
            http_method="GET",
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": str(e)}


@app.route(
    "/create_dataset", cors=True, methods=["POST"], authorizer=authorizer
)
@tasks.authorize_amc_request(app=app)
def create_dataset(**kwargs):
    """
    Create a dataset in AMC.

    Returns AMC response:

    .. code-block:: python

        {}
    """
    log_request_parameters()
    try:
        body = app.current_request.json_body["body"]
        # If customer provided a CMK, then use the key to encrypt this dataset in AMC.
        if CUSTOMER_MANAGED_KEY != "":
            body["customerEncryptionKeyArn"] = CUSTOMER_MANAGED_KEY

        amc_request = tasks.AMCRequests(
            amc_path="/dataSets",
            http_method="POST",
            payload=json.dumps(body),
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )

        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
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
@tasks.authorize_amc_request(app=app)
def start_amc_transformation(**_):
    """
    Invoke Glue job to prepare data for uploading into AMC.
    This function is called from the GUI. It may also be called
    directly (e.g. from an S3 trigger function).

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
        dataset_id = app.current_request.json_body["datasetId"]
        country_code = app.current_request.json_body.get("countryCode")
        update_strategy = app.current_request.json_body["updateStrategy"]
        session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
        amc_instances = json.loads(
            app.current_request.json_body["amc_instances"]
        )
        user_id = app.current_request.json_body["user_id"]

        # The fileFormat parameter is optional.
        # If this function  is called from the GUI then the payload will
        # include fileFormat. If it is called directly, then it might not include
        # fileFormat since that is an optional argument. If fileFormat is not
        # provided then this function will attempt to infer it from the file
        # content_type.
        #
        # At the end of this function, fileFormat is required so that it can be
        # passed to the Glue ETL job.
        file_format = app.current_request.json_body.get("fileFormat", "")
        if file_format not in ("", "JSON", "CSV"):
            logger.error("Unexpected fileFormat value: " + file_format)
            logger.error("fileFormat must be \"CSV\" or \"JSON\".")
            raise BadRequestError("Unexpected file format: " + file_format)
        if file_format == "":
            file_format = get_file_format(source_bucket, source_key)

        client = session.client("glue", config=config)
        args = {
            "--source_bucket": source_bucket,
            "--output_bucket": output_bucket,
            "--source_key": source_key,
            "--pii_fields": pii_fields,
            "--deleted_fields": deleted_fields,
            "--dataset_id": dataset_id,
            "--file_format": file_format,
            "--update_strategy": update_strategy,
            "--user_id": user_id,
            "--amc_instances": json.dumps(
                [instance["instance_id"] for instance in amc_instances]
            ),
        }

        # countryCode is optional
        if country_code:
            args["--country_code"] = country_code

        # timestampColumn is optional and will only be present for FACT datasets
        if app.current_request.json_body.get("timestampColumn", "") != "":
            args["--timestamp_column"] = app.current_request.json_body["timestampColumn"]

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
@tasks.authorize_amc_request(app=app)
def upload_status(**kwargs):
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

        amc_request = tasks.AMCRequests(
            amc_path=f"/uploads/{data_set_id}/{upload_id}",
            http_method="GET",
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": str(e)}


@app.route("/list_uploads", cors=True, methods=["POST"], authorizer=authorizer)
@tasks.authorize_amc_request(app=app)
def list_uploads(**kwargs):
    """
    List all the uploads for an AMC dataset.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        request_parameters = {
            "dataSetId": app.current_request.json_body["dataSetId"]
        }
        if "nextToken" in app.current_request.json_body:
            request_parameters["nextToken"] = app.current_request.json_body["nextToken"]

        amc_request = tasks.AMCRequests(
            amc_path="/uploads/list",
            http_method="POST",
            request_parameters=request_parameters,
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/get_amc_instances", cors=True, methods=["POST"], authorizer=authorizer
)
@tasks.authorize_amc_request(app=app)
def get_amc_instances(**kwargs):
    """
    List all the AMC instances.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        amc_request = tasks.AMCRequests(
            amc_path="/amc/instances",
            http_method="GET",
            is_amc_report=False,
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/get_amc_accounts", cors=True, methods=["POST"], authorizer=authorizer
)
@tasks.authorize_amc_request(app=app)
def get_amc_accounts(**kwargs):
    """
    List all the AMC accounts.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        amc_request = tasks.AMCRequests(
            amc_path="/amc/accounts",
            http_method="GET",
            is_amc_report=False,
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route(
    "/list_upload_failures", cors=True, methods=["POST"], authorizer=authorizer
)
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
        dataset_id = app.current_request.json_body["dataSetId"]
        instance_id = app.current_request.json_body["instance_id"]
        item_key = {"instance_id": instance_id, "dataset_id": dataset_id}
        upload_failures_table = dynamo_resource.Table(
            UPLOAD_FAILURES_TABLE_NAME
        )
        item = upload_failures_table.get_item(
            Key=item_key, ConsistentRead=True
        )
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
@tasks.authorize_amc_request(app=app)
def delete_dataset(**kwargs):
    """
    Delete an AMC dataset and all the records uploaded to it.

    Returns AMC response:

    .. code-block:: python

        {}

    """
    log_request_parameters()
    try:
        dataset_id = app.current_request.json_body["dataSetId"]
        # Step 1/2: delete uploaded data
        # This should delete any data files that customers uploaded for either FACT or DIMENSION datasets

        amc_request = tasks.AMCRequests(
            amc_path=f"/dataSets/{dataset_id}",
            http_method="DELETE",
        )
        response = amc_request.process_request(
            **kwargs, **app.current_request.json_body
        )
        if response.status_code == 200:
            dynamo_resource = boto3.resource("dynamodb", config=config)
            item_key = {
                "instance_id": app.current_request.json_body["instance_id"],
                "dataset_id": dataset_id,
            }
            logger.info(
                "Removing upload record from "
                + UPLOAD_FAILURES_TABLE_NAME
                + " if the following key exists:"
                + json.dumps(item_key)
            )
            upload_failures_table = dynamo_resource.Table(
                UPLOAD_FAILURES_TABLE_NAME
            )
            try:
                upload_failures_table.delete_item(Key=item_key)
            except dynamo_resource.meta.client.exceptions.ConditionalCheckFailedException:
                pass
        return Response(
            body=response.text,
            status_code=response.status_code,
            headers={"Content-Type": JSON_CONTENT_TYPE},
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
    content_types=[JSON_CONTENT_TYPE],
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
    content_types=[JSON_CONTENT_TYPE],
    authorizer=authorizer,
)
def get_data_columns():
    """Get the column names and content_type of a user-specified JSON or CSV file.

       This function is used by the front-end to generate a web form where
       users can specify attributes for each column in the input file.

       This function is also used to raise errors in the front-end when:
         - the user inputs a list of more than 200 files
         - the user inputs a file that is not formatted as CSV or JSON
         - the user inputs files that have different content_types
         - the user inputs files that have different columns

    Body:
        The fileFormat parameter is optional. Accepted values are "JSON" or
        "CSV". If it is not specified then fileFormat will be inferred from
        the content_type specified by S3.

        .. code-block:: python

            {
                "s3bucket": string,
                "s3key": string
                "fileFormat": string
            }


    Returns:
        List of column names and content_type common to each input file.

        .. code-block:: python

            {
                "columns": [string, string, ...],
                "content_type": string
            }

    Raises:
        500: ChaliceViewError - internal server error
    """

    log_request_parameters()
    current_request = json.loads(app.current_request.raw_body.decode())
    try:
        # Validate and extract request parameters:
        s3bucket, keys, file_format = extract_request_parameters(current_request)

        # Return an error if the user inputs more than 200 files because
        # AWS Glue service quota allows maximum of 200 concurrent glue jobs
        # per account.
        if len(keys) > 200:
            raise BadRequestError("Number of files selected cannot exceed 200.")

        # If file format is unspecified then infer it from the first file:
        if file_format == "":
            file_format = get_file_format(s3bucket, keys[0])

        # Get the list of data fields from the first file:
        first_file_description = describe_file(s3bucket, keys[0], file_format)

        # Make sure all files have the same format and data fields:
        for key in keys[1:]:
            if describe_file(s3bucket, key, file_format) != first_file_description:
                raise BadRequestError("Every file must have the same format and data fields.")

        return first_file_description

    except Exception as e:
        logger.error(e)
        raise e


# This function extracts request parameters for /get_data_columns
def extract_request_parameters(request):
    s3bucket = request.get("s3bucket")
    keys = [x.strip() for x in request.get("s3key", "").split(",")]
    file_format = request.get("fileFormat", "")
    if not s3bucket:
        raise BadRequestError("Missing parameter s3bucket")
    if not keys:
        raise BadRequestError("Missing parameter s3key")
    if file_format not in ("", "JSON", "CSV"):
        logger.error("Unexpected fileFormat value: " + file_format)
        logger.error("fileFormat must be \"CSV\" or \"JSON\".")
        raise BadRequestError("Unexpected file format: " + file_format)
    return s3bucket, keys, file_format


# This function determines whether the input file contains data formatted as
# CSV or JSON.
def get_file_format(bucket, key):
    s3_obj = boto3.client("s3", config=config)
    head_object_response = s3_obj.head_object(Bucket=bucket, Key=key)
    content_type = head_object_response["ContentType"]
    if content_type == JSON_CONTENT_TYPE:
        file_format = "JSON"
    elif content_type == CSV_CONTENT_TYPE:
        file_format = "CSV"
    elif content_type == GZIP_CONTENT_TYPE:
        if re.search(r"\.json\.gz$", key):
            file_format = "JSON"
        elif re.search(r"\.csv\.gz$", key):
            file_format = "CSV"
        else:
            message = "Cannot infer file format of gzipped file."
            logger.error(message)
            raise BadRequestError(message)
    else:
        message = "Unsupported content type " + str(content_type)
        logger.error(message)
        raise BadRequestError(message)
    return file_format


# This function reads the first row of the input file and returns the data
# fields present in that row along with the content_type of the file.
def describe_file(bucket, key, file_format):
    try:
        file_description = None
        if file_format == "JSON":
            dfs = wr.s3.read_json(
                path=["s3://" + bucket + "/" + key],
                chunksize=1,
                lines=True,
            )
            chunk = next(dfs)
            columns = chunk.columns.to_list()
            file_description = json.dumps(
                {"columns": columns, "content_type": JSON_CONTENT_TYPE}
            )
        elif file_format == "CSV":
            dfs = wr.s3.read_csv(
                path=["s3://" + bucket + "/" + key], chunksize=1
            )
            chunk = next(dfs)
            columns = chunk.columns.to_list()
            file_description = json.dumps(
                {"columns": columns, "content_type": CSV_CONTENT_TYPE}
            )
        return file_description
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}

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
        for key_check in ["instance_id", "advertiser_id", "marketplace_id"]:
            if key_check not in amc_instances[i]:
                raise BadRequestError(
                    f"AmcInstance value must contain key, '{key_check}'"
                )


@app.route(
    "/system/configuration",
    cors=True,
    methods=["POST"],
    content_types=[JSON_CONTENT_TYPE],
    authorizer=authorizer,
)
def save_system_configuration():
    """Creates or updates values in the system configuration table.
    Body:
    .. code-block:: python
        {
            "Name": "ParameterName",
            "Value": "ParameterValue"
        }
    Supported parameters:
        "Name": "AmcInstances",
        "Value": {"instance_id": string, "data_upload_account_id": string, "marketplace_id": string, ...}
            Saves a list of AMC instances and their associated attributes.
    Returns:
        None
    Raises:
        500: ChaliceViewError - internal server error
    """
    log_request_parameters()
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
    tasks.apply_amc_bucket_permission()
    return {}


@app.route(
    "/system/configuration", cors=True, methods=["GET"], authorizer=authorizer
)
def get_system_configuration():
    """Get the current system configuration.
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
    logger.debug(
        "request ID: " + (app.current_request.context.get("requestId", ""))
    )
    logger.info("request body: " + app.current_request.raw_body.decode())
    logger.debug(app.current_request.to_dict())


@app.route(
    "/validate_amc_request", cors=True, methods=["POST"], authorizer=authorizer
)
def validate_amc_request():
    try:
        redirect_uri = tasks.get_redirect_uri(app.current_request)
        return tasks.get_ads_token(
            **app.current_request.json_body, redirect_uri=redirect_uri
        )
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route("/save_secret", cors=True, methods=["POST"], authorizer=authorizer)
def save_secret():
    """Saves OAuth client ID and client secret to Secrets Manager.
    Body:
    .. code-block:: python
        {
            "user_id": "user pool id value",
            "client_id": "client id value",
            "client_secret": "client secret value"
        }
    Returns:
        {}
    Raises:
        500: ChaliceViewError - internal server error
    """
    user_id = app.current_request.json_body["user_id"]
    client_id = app.current_request.json_body["client_id"]
    client_secret = app.current_request.json_body["client_secret"]
    client_token = {"client_id": client_id, "client_secret": client_secret}

    try:
        secret_key = tasks.format_client_secret_id(user_id)
        refresh_token = tasks.get_secret(secret_key)["refresh_token"]
        if refresh_token:
            # Invalidate the refresh_token so that it will regenerate
            # with the new client secret.
            client_token["refresh_token"] = tasks.DELETE_STRING
    except Exception:
        pass
    try:
        # Return error if client_id or client_secret contain an invalid character
        lwa_oauth_pattern = r"^[a-zA-Z0-9\-\.]+$"
        if not re.match(lwa_oauth_pattern, client_id):
            raise ValueError("Client ID must contain only letters, numbers, dashes, and periods.")
        if not re.match(lwa_oauth_pattern, client_secret):
            raise ValueError("Client Secret must contain only letters, numbers, dashes, and periods.")

        tasks.create_update_secret(
            tasks.format_client_secret_id(user_id),
            client_token,
        )
        return {}
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}


@app.route("/describe_secret", cors=True, methods=["POST"], authorizer=authorizer)
def describe_secret():
    """Retrieves the list of dictionary keys contained in the user's LwA secret. This does not include any secret value.
    Body:
    .. code-block:: python
        {
            "user_id": "user pool id value",
        }
    Returns:
        {
            "secret_string_keys": [
                "client_id", "client_secret", "refresh_token"
            ]
        }
    Raises:
        500: ChaliceViewError - internal server error
    """
    log_request_parameters()
    try:
        user_id = app.current_request.json_body["user_id"]
        secret_string = tasks.get_secret(tasks.format_client_secret_id(user_id))
        secret_string_keys = list(secret_string.keys())
        response = {"secret_string_keys": secret_string_keys}
        return response
    except Exception as ex:
        logger.error(ex)
        return {"Status": "Error", "Message": str(ex)}
