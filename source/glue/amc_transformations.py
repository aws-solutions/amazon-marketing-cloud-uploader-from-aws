# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# ###############################################################################
# PURPOSE:
#   Normalize and hash clear-text PII, and partition time series datasets for AMC.
#
# PREREQUISITES:
#   Timestamp columns must be formatted according to ISO 8601.
#
# INPUT:
#   --source_bucket: S3 bucket containing input file
#   --output_bucket: S3 bucket for output data
#   --source_key: S3 key of input file.
#   --timestamp_column: Column name containing timestamps for time series datasets (e.g. FACT). Leave blank for datasets that are not time series (e.g. DIMENSION).
#   --pii_fields: json formatted array containing column names that need to be hashed and the PII type of their data. The type must be FIRST_NAME, LAST_NAME, PHONE, ADDRESS, CITY, STATE, ZIP, or EMAIL.
#   --deleted_fields: array of strings indicating the names of columns which the user requested to be dropped from the dataset prior to uploading to AMC.
#   --dataset_id: name of dataset, used as the prefix folder for the output s3key.
#   --country_code: country-specific normalization to apply to all rows in the dataset (2-digit ISO country code).
#   --amc_instances: List of AMC instances to receive uploads
#
# OUTPUT:
#   - Transformed data files in user-specified output bucket,
#     partitioned according to AMC spec.
#
# SAMPLE COMMAND-LINE USAGE:
#
#    export JOB_NAME=mystack-GlueStack-12BSLR8H1F79M-amc-transformation-job
#    export SOURCE_BUCKET=mybucket
#    export SOURCE_KEY=mydata.json
#    export OUTPUT_BUCKET=mystack-etl-artifacts-zmtmhi
#    export TIMESTAMP_COLUMN=timestamp
#    export PII_FIELDS='[{\"column_name\": \"first_name\",\"pii_type\": \"FIRST_NAME\"},{\"column_name\": \"last_name\",\"pii_type\": \"LAST_NAME\"},{\"column_name\": \"address\",\"pii_type\": \"ADDRESS\"}]'
#    export DELETED_FIELDS='[\"customer_id\",\"purchase_id\"]'
#    export DATASET_ID='mytest123'
#    export REGION=us-east-1
#    aws glue start-job-run --job-name $JOB_NAME --arguments '{"--source_bucket": "'$SOURCE_BUCKET'", "--output_bucket": "'$OUTPUT_BUCKET'", "--source_key": "'$SOURCE_KEY'", "--pii_fields": "'$PII_FIELDS'",
#    "--deleted_fields": "'$DELETED_FIELDS'", "--timestamp_column": "'$TIMESTAMP_COLUMN'", "--dataset_id": "'$DATASET_ID'", "--country_code": "US"}' --region $REGION
#
###############################################################################

import sys

from awsglue.utils import GlueArgumentError, getResolvedOptions
from library import read_write as rw
from library import transform

REQUIRED_PARAMS = [
    "JOB_NAME",
    "solution_id",
    "uuid",
    "enable_anonymous_data",
    "anonymous_data_logger",
    "source_bucket",
    "source_key",
    "output_bucket",
    "pii_fields",
    "deleted_fields",
    "dataset_id",
    "user_id",
    "file_format",
    "amc_instances",
    "update_strategy"
]
OPTIONAL_PARAMS = ["timestamp_column", "country_code"]


def check_params(required: list, optional: list) -> dict:
    # assign required params
    try:
        args = getResolvedOptions(sys.argv, required)
    except GlueArgumentError as e:
        # If any required parameter is missing then stop execution.
        print(e)
        sys.exit(1)

    # assign optional params
    for parameter in optional:
        try:
            args.update(getResolvedOptions(sys.argv, [parameter]))
        except GlueArgumentError as e:
            # Continue execution if any optional parameter is missing.
            pass

    # strip whitespace on applicable fields
    for i in ("dataset_id", "timestamp_column"):
        if i in args.keys():
            args[i] = args[i].strip()
    if args.get("country_code") and args.get("country_code") not in (
        "US",
        "GB",
        "JP",
        "IN",
        "IT",
        "ES",
        "CA",
        "DE",
        "FR",
    ):
        print("ERROR: Invalid user-defined value for country:")
        print(args["country_code"])
        sys.exit(1)
    if args["file_format"] not in (
            "JSON",
            "CSV"
    ):
        print("ERROR: Invalid file format for input files:")
        print(args["file_format"])
        sys.exit(1)
    if len(args["amc_instances"]) == 0:
        print("amc_instances cannot be empty")
        sys.exit(1)
    return args


params = check_params(required=REQUIRED_PARAMS, optional=OPTIONAL_PARAMS)

print("Runtime args:")
print(params)

file = rw.DataFile(args=params)

file.read_bucket()
file.load_input_data()
file.remove_deleted_fields()

if file.country_code:
    file.data = transform.transform_data(
        data=file.data, pii_fields=file.pii_fields, country_code=file.country_code
    )
file.data = transform.hash_data(data=file.data, pii_fields=file.pii_fields)

if file.timestamp_column:
    file.timestamp_transform()
    
file.save_output()

if params.get("enable_anonymous_data", "false") == "true":
    file.save_performance_metrics()
