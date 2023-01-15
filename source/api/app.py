# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from chalice import Chalice, IAMAuthorizer, Response
from chalicelib import sigv4
import boto3
from botocore import config
import json
import os
from dateutil.tz import tzlocal
import datetime
import logging

solution_config = json.loads(os.environ['botoConfig'])
config = config.Config(**solution_config)

# format log messages like this:
formatter = logging.Formatter('{%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Remove the default logger in order to avoid duplicate log messages
# after we attach our custom logging handler.
logging.getLogger().handlers.clear()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Patch libraries to instrument downstream calls
from aws_xray_sdk.core import patch_all
patch_all()

# Initialization
app = Chalice(app_name='amcufa_api')
authorizer = IAMAuthorizer()

# Environment variables
VERSION = os.environ['VERSION']
AMC_GLUE_JOB_NAME = os.environ['AMC_GLUE_JOB_NAME']
CUSTOMER_MANAGED_KEY = os.environ['CUSTOMER_MANAGED_KEY']

# Resolve sonarqube code smells
application_json = 'application/json'
data = '/data/'

@app.route('/list_datasets', cors=True, methods=['GET'], authorizer=authorizer)
def list_datasets():
    """
    List datasets in AMC.

    Returns:

    .. code-block:: python

        {"dataSets": [...]}
    """
    log_request_parameters()
    try:
        path = '/dataSets'
        response = sigv4.get(path)
        return Response(body=response.text,
                        status_code=response.status_code,
                        headers={'Content-Type': application_json})
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/create_dataset', cors=True, methods=['POST'], authorizer=authorizer)
def create_dataset():
    """
    Create a dataset in AMC.

    Returns AMC response:

    .. code-block:: python

        {}
    """
    log_request_parameters()
    try:
        body = app.current_request.json_body['body']
        if body['period'] == 'autodetect':
            # Initialize the dataset period to P1D. This will be updated later
            # when the AWS Glue job measures the actual dataset period.
            body['period'] = 'P1D'
        # If customer provided a CMK, then use the key to encrypt this dataset in AMC.
        if CUSTOMER_MANAGED_KEY != '':
            body['customerEncryptionKeyArn'] = CUSTOMER_MANAGED_KEY
        path = '/dataSets'
        response = sigv4.post(path, json.dumps(body))
        return Response(body=response.text,
                        status_code=response.status_code,
                        headers={'Content-Type': application_json})
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/start_amc_transformation', cors=True, methods=['POST'], authorizer=authorizer)
def start_amc_transformation():
    """
    Invoke Glue job to prepare data for uploading into AMC.

    Returns AMC response:

    .. code-block:: python

        {"JobRunId": string}
    """
    log_request_parameters()
    try:
        source_bucket = app.current_request.json_body['sourceBucket']
        source_key = app.current_request.json_body['sourceKey']
        output_bucket = app.current_request.json_body['outputBucket']
        pii_fields = app.current_request.json_body['piiFields']
        deleted_fields = app.current_request.json_body['deletedFields']
        timestamp_column = app.current_request.json_body['timestampColumn']
        dataset_id = app.current_request.json_body['datasetId']
        period = app.current_request.json_body['period']
        session = boto3.session.Session(region_name=os.environ['AWS_REGION'])
        client = session.client('glue', config=config)
        args = {
            "--source_bucket": source_bucket,
            "--output_bucket": output_bucket,
            "--source_key": source_key,
            "--pii_fields": pii_fields,
            "--deleted_fields": deleted_fields,
            "--timestamp_column": timestamp_column,
            "--dataset_id": dataset_id,
            "--period": period
        }
        logger.info('Starting Glue job:')
        logger.info('Equivalent AWS CLI command: ')
        # We've intentionally omitted a value for --profile in the
        # following command so the CLI reminds users to specify it.
        logger.info('aws glue start-job-run --region ' + os.environ['AWS_REGION'] + ' --job-name ' + AMC_GLUE_JOB_NAME + ' --arguments \'' + json.dumps(args) + '\' --profile ')
        response = client.start_job_run(JobName=AMC_GLUE_JOB_NAME, Arguments=args)
        return {'JobRunId': response['JobRunId']}
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}


@app.route('/get_etl_jobs', cors=True, methods=['GET'], authorizer=authorizer)
def get_etl_jobs():
    """
    Retrieves metadata for all runs of a given Glue ETL job definition.

    Returns:

    .. code-block:: python

        {'JobRuns': [...]}
    """
    log_request_parameters()
    try:
        client = boto3.client('glue', config=config)
        response = client.get_job_runs(JobName=AMC_GLUE_JOB_NAME)
        for i in range(len(response['JobRuns'])):
            if 'Arguments' in response['JobRuns'][i]:
                if response['JobRuns'][i]['Arguments'].get('--dataset_id'):
                    response['JobRuns'][i]['DatasetId'] = response['JobRuns'][i]['Arguments']['--dataset_id']
        return json.loads(json.dumps(response, default=str))
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}


@app.route('/upload_status', cors=True, methods=['POST'], authorizer=authorizer)
def upload_status():
    """
    Get the status of an AMC data upload operation.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body['dataSetId']
        upload_id = app.current_request.json_body['uploadId']
        path = data + data_set_id + '/uploads/' + upload_id
        response = sigv4.get(path)
        return Response(body=response.text,
                        status_code=response.status_code,
                        headers={'Content-Type': application_json})
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/list_uploads', cors=True, methods=['POST'], authorizer=authorizer)
def list_uploads():
    """
    List all the uploads for an AMC dataset.

    Returns AMC response:

    .. code-block:: python

        { dict }

    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body['dataSetId']
        next_token = ''
        if "nextToken" in app.current_request.json_body:
            next_token = app.current_request.json_body['nextToken']
        path = data + data_set_id + '/uploads/'
        response = sigv4.get(path, request_parameters="nextToken="+next_token)
        return Response(body=response.text,
                        status_code=response.status_code,
                        headers={'Content-Type': application_json})
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/delete_dataset', cors=True, methods=['POST'], authorizer=authorizer)
def delete_dataset():
    """
    Delete an AMC dataset and all the records uploaded to it.

    Returns AMC response:

    .. code-block:: python

        {}

    """
    log_request_parameters()
    try:
        data_set_id = app.current_request.json_body['dataSetId']
        # Step 1/2: delete uploaded data
        # This should delete any data files that customers uploaded for either FACT or DIMENSION datasets
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        path = data + data_set_id + '?timeWindowStart=1970-01-01T00:00:00Z&timeWindowEnd=' + current_datetime
        sigv4.delete(path)
        # Step 2/2: delete the dataset definition
        path = '/dataSets/' + data_set_id
        response = sigv4.delete(path)
        return Response(body=response.text,
                        status_code=response.status_code,
                        headers={'Content-Type': application_json})
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/version', cors=True, methods=['GET'], authorizer=authorizer)
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


@app.route('/list_bucket', cors=True, methods=['POST'], content_types=[application_json], authorizer=authorizer)
def list_bucket():
    """ List the contents of a user-specified S3 bucket

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
        s3 = boto3.resource('s3', config=config)
        bucket = json.loads(app.current_request.raw_body.decode())['s3bucket']
        results = []
        for s3object in s3.Bucket(bucket).objects.all():
            results.append({"key": s3object.key, "last_modified": s3object.last_modified.isoformat(), "size": s3object.size})
        return json.dumps(results)
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}

@app.route('/get_data_columns', cors=True, methods=['POST'], content_types=[application_json], authorizer=authorizer)
def get_data_columns():
    """ Get the column names of a user-specified JSON or CSV file

    Body:

    .. code-block:: python

        {
            "s3bucket": string,
            "s3key": string
            "file_format": ['CSV', 'JSON']
        }


    Returns:
        List of column names and data types found in the first row of
        the user-specified data file.

        .. code-block:: python

            {
                "object": {
                }
            }

    Raises:
        500: ChaliceViewError - internal server error
    """
    import awswrangler as wr
    log_request_parameters()
    try:
        bucket = json.loads(app.current_request.raw_body.decode())['s3bucket']
        key = json.loads(app.current_request.raw_body.decode())['s3key']
        file_format = json.loads(app.current_request.raw_body.decode())['file_format']
        if file_format != 'CSV' and file_format != 'JSON':
            raise TypeError('File format must be CSV or JSON')
        # Read first row
        logger.info("Reading " + 's3://'+bucket+'/'+key)
        if file_format == 'JSON':
            dfs = wr.s3.read_json(path=['s3://'+bucket+'/'+key], chunksize=1, lines=True)
        elif file_format == 'CSV':
            dfs = wr.s3.read_csv(path=['s3://'+bucket+'/'+key], chunksize=1)
        chunk = next(dfs)
        columns = list(chunk.columns.values)
        result = json.dumps({'columns': columns})
        return result
    except Exception as e:
        logger.error(e)
        return {"Status": "Error", "Message": e}


def log_request_parameters():
    logger.info("Processing the following request:\n")
    logger.info("resource path: " + app.current_request.context['resourcePath'])
    logger.info("method: " + app.current_request.method)
    logger.info("uri parameters: " + str(app.current_request.uri_params))
    logger.info("query parameters: " + str(app.current_request.query_params))
    logger.info("request ID: " + app.current_request.context.get('requestId'))
    logger.info('request body: ' + app.current_request.raw_body.decode())
    logger.info(app.current_request.to_dict())
