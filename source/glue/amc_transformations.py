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
#   --period: time period of dataset, one of ["autodetect","PT1M","PT1H","P1D","P7D"]. Autodetect enabled by default. (optional)
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
#    aws glue start-job-run --job-name $JOB_NAME --arguments '{"--source_bucket": "'$SOURCE_BUCKET'", "--output_bucket": "'$OUTPUT_BUCKET'", "--source_key": "'$SOURCE_KEY'", "--pii_fields": "'$PII_FIELDS'", "--deleted_fields": "'$DELETED_FIELDS'", "--timestamp_column": "'$TIMESTAMP_COLUMN'", "--dataset_id": "'$DATASET_ID'", "--period": "autodetect"}' --region $REGION
#
###############################################################################

import sys
from normalizers.address_normalizer import AddressNormalizer
from normalizers.email_normalizer import EmailNormalizer
from normalizers.state_normalizer import StateNormalizer
from normalizers.zip_normalizer import ZipNormalizer
from normalizers.phone_normalizer import PhoneNormalizer
from awsglue.utils import getResolvedOptions, GlueArgumentError
import pandas as pd
import awswrangler as wr
import regex as re
import hashlib
import json
import boto3
import re
from datetime import datetime

# Hardcode country code for now.
country_code = 'US'

# Resolve sonarqube code smells
writing = "Writing "
rows_to = " rows to "

###############################
# DATA NORMALIZATION PATTERNS
###############################

addressNormalizer = AddressNormalizer(country_code)
stateNormalizer = StateNormalizer(country_code)
zipNormalizer = ZipNormalizer(country_code)
phoneNormalizer = PhoneNormalizer(country_code)

###############################
# PARSE ARGS
###############################

# Read required parameters
try:
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'solution_id', 'uuid', 'enable_anonymous_data', 'anonymous_data_logger', 'source_bucket', 'source_key', 'output_bucket', 'pii_fields', 'deleted_fields', 'dataset_id', 'period'])
except GlueArgumentError as e:
    print(e)
    exit(1)
finally:
    print("Runtime args:")
    print(args)
job_name = args['JOB_NAME']
job_run_id = args['JOB_RUN_ID']
enable_anonymous_data = args['enable_anonymous_data']
anonymous_data_logger = args['anonymous_data_logger']
solution_id = args['solution_id']
uuid = args['uuid']
if 'dataset_id' in args:
    dataset_id = args['dataset_id'].strip()
else:
    print("Missing required arg: dataset_id")
    exit(1)
pii_fields = []
if 'pii_fields' in args:
    pii_fields = json.loads(args['pii_fields'])
deleted_fields = []
if 'deleted_fields' in args:
    deleted_fields = json.loads(args['deleted_fields'])
if 'period' in args:
    user_defined_partition_size = args['period'].strip()
    if user_defined_partition_size not in ("autodetect", "PT1M", "PT1H", "P1D", "P7D"):
        print("ERROR: Invalid user-defined value for dataset period:")
        print(user_defined_partition_size)
        exit(1)

# Read optional parameters
try:
    timestamp_column = getResolvedOptions(sys.argv, ['timestamp_column'])['timestamp_column'].strip()
except GlueArgumentError as e:
    timestamp_column = None

###############################
# LOAD INPUT DATA
###############################

source_bucket = args['source_bucket']
key = args['source_key']
filename = key.split('/')[-1]
output_bucket = args['output_bucket']

s3 = boto3.client('s3')
response = s3.head_object(Bucket=source_bucket, Key=key)
content_type = response['ContentType']
print("CONTENT TYPE: " + content_type)
num_bytes = response['ContentLength']
print("FILE SIZE: " + str(num_bytes))
num_rows = 0

chunksize = 2000

df = pd.DataFrame()
json_content_type = "application/json"
csv_content_type = "text/csv"

# Configure all PII-designated fields to be read as strings
# This avoids reading phone or zip values as floats and dropping data or requiring additional transformation before normalization
pii_column_names = {}
for field in pii_fields:
    pii_column_names[field['column_name']] = str

if content_type == json_content_type:
    dfs = wr.s3.read_json(
        path=['s3://' + source_bucket + '/' + key], 
        chunksize=chunksize, 
        lines=True,
        dtype=pii_column_names
        )
elif content_type == csv_content_type:
    dfs = wr.s3.read_csv(
        path=['s3://' + source_bucket + '/' + key], 
        chunksize=chunksize,
        dtype=pii_column_names
        )
else:
    print("Unsupported content type: " + content_type)
    exit(1)

for chunk in dfs:
    # Save each chunk
    df = pd.concat([chunk, df])

###############################
# DATA CLEANSING
###############################

# Delete the columns that were indicated by the user to be deleted.
for column_name in deleted_fields:
    df.drop(column_name, axis=1, inplace=True)

# Define the column name to hold the timestamp in its full precision
timestamp_full_precision = 'timestamp_full_precision'

if timestamp_column:
    # Convert timestamp column to datetime type so we can use datetime methods
    try:
        df[timestamp_column] = pd.to_datetime(df[timestamp_column], utc=True)
    except ValueError as e:
        print(e)
        print('Failed to parse timeseries in column ' + timestamp_column)
        print('Verify that timeseries is formatted according to ISO 8601.')
        raise e
    except Exception as e:
        print(e)
        print('Failed to parse timeseries in column ' + timestamp_column)
        raise e

###############################
# DATA NORMALIZATION
###############################

def address_transformations(text):
    text = addressNormalizer.normalize(text).normalizedAddress
    return text

def state_transformations(text):
    text = stateNormalizer.normalize(text).normalizedState.lower()
    return text

def normalize_email(text):
    email_normalize = EmailNormalizer(text)
    return email_normalize.normalize()

def zip_transformations(text):
    text = zipNormalizer.normalize(text).normalizedZip
    return text

def phone_transformations(text):
    text = phoneNormalizer.normalize(text).normalizedPhone
    return text

# Use this function to flag records that are null or already hashed
# These records will skip normalization/hashing
def skip_record_flag(text):
    # This regex expression matches a sha256 hash value.
    # Sha256 hash codes are 64 consecutive hexadecimal digits, a-f and 0-9.
    sha256_pattern = "^[a-f0-9]{64}$"
    if pd.isnull(text) or re.match(sha256_pattern, text):
        return True

for field in pii_fields:
    column_name = field['column_name']
    if field['pii_type'] == "ADDRESS":
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else address_transformations(x))
    elif field['pii_type'] == "STATE":
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else state_transformations(x))
    elif field['pii_type'] == "ZIP":
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else zip_transformations(x))
    elif field['pii_type'] == "PHONE":
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else phone_transformations(x))
    elif field['pii_type'] == "EMAIL":
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else x.lower())
        df[column_name].replace("[^\w.@-]", "", inplace=True, regex=True)
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else normalize_email(x))
    else:
        df[column_name] = df[column_name].copy().apply(
            lambda x: x if skip_record_flag(x) else x.lower())
        # convert characters ß, ä, ö, ü, ø, æ 
        df[column_name].replace("ß", "ss", inplace=True)
        df[column_name].replace("ä", "ae", inplace=True)
        df[column_name].replace("ö", "oe", inplace=True)
        df[column_name].replace("ü", "ue", inplace=True)
        df[column_name].replace("ø", "o", inplace=True)
        df[column_name].replace("æ", "ae", inplace=True)
        # remove all symbols and whitespace
        df[column_name].replace("[^a-z0-9]", "", inplace=True, regex=True)

###############################
# PII HASHING
###############################

for field in pii_fields:
    column_name = field['column_name']
    df[column_name] = df[column_name].copy().apply(
        lambda x: x if skip_record_flag(x) else hashlib.sha256(x.encode()).hexdigest())

###############################
# TIME SERIES PARTITIONING
###############################

if timestamp_column:
    # AMC supports "Units of upload" of PT1M (minute-by-minute) granularity or longer
    # so we round timestamps to the nearest minute, below.
    # But before we write that data to AMC, we will want to restore the timestamp to full precision.
    # So we record that full precision here so that it can be restored later.
    df[timestamp_full_precision] = df[timestamp_column]
    df[timestamp_column] = df[timestamp_column].dt.round('Min')

    # Prepare to calculate time deltas by sorting on the timeseries column
    unique_timestamps = pd.DataFrame(df[timestamp_column].unique())
    unique_timestamps = unique_timestamps.rename(columns={0: 'timestamp'})
    unique_timestamps = unique_timestamps.sort_values(by='timestamp')

    if user_defined_partition_size in ("PT1M", "PT1H", "P1D", "P7D"):
        timeseries_partition_size = user_defined_partition_size
    if user_defined_partition_size == "autodetect":
        # Store the time delta between each sequential event
        unique_timestamps['timedelta'] = unique_timestamps['timestamp'] - unique_timestamps['timestamp'].shift()

        # Here we calculate the partition size based on the minimum delta between timestamps in the dataset.
        zero_timedelta = '0 days 00:00:00'
        min_timedelta = unique_timestamps['timedelta'][unique_timestamps['timedelta'] != zero_timedelta].dropna().min()

        # Initialize timeseries partition size. The available options are:
        #   PT1M (minute)
        #   PT1H (hour)
        #   P1D (day)
        #   P7D (7 days)
        timeseries_partition_size = 'PT1M'

        # If the smallest delta between timestamps is at least 60 minutes (3600 seconds), then we'll partition timeseries data into one file for each hour.
        # Note, timedelta.seconds rolls over to 0 when the timedelta reaches 1 day, so we need to check timedelta.days too:
        if (min_timedelta.seconds >= 3600 and min_timedelta.days == 0):
            timeseries_partition_size = 'PT1H'

        # If the smallest delta between timestamps is at least 24 hours, then we'll partition timeseries data into one file for each day.
        elif (0 < min_timedelta.days < 7):
            timeseries_partition_size = 'P1D'

        # If the smallest delta between timestamps is at least 7 days, then we'll partition timeseries data into one file for each week.
        elif (min_timedelta.days >= 7):
            timeseries_partition_size = 'P7D'

###############################
# SAVE OUTPUT DATA
###############################

# Partition the timeseries dataset into separate files for each
# unique timestamp.
output_files = []
amc_str = 'amc'
datetime_format = '%Y-%m-%dT%H:%M:%SZ'

if timestamp_column:
    dataset_type = 'FACT'
    # Initialize a temporary variable to help us know when timestamps
    # map to a new string:
    timestamp_str_old = ''
    # Initialize a dataframe to hold the dataset for this timestamp:
    df_partition = pd.DataFrame()
    for timestamp in unique_timestamps.timestamp:
        # In order to avoid errors like this:
        #   "The timeWindowStart ... does not align with the data set's period"
        # we need to save file names with timestamps that use
        #   00 for seconds in the case of PT1M, PT1H, P1D, and P7D,
        #   00 for minutes and seconds in the case of PT1H, P1D, P7D,
        #   and 00 for hours, minutes, and seconds in the case of P1D, P7D.
        timestamp_str = timestamp.strftime("%Y_%m_%d-%H:%M:00")
        if timeseries_partition_size == 'PT1H' or timeseries_partition_size == 'P1D' or timeseries_partition_size == 'P7D':
            timestamp_str = timestamp.strftime("%Y_%m_%d-%H:00:00")
        if timeseries_partition_size == 'P1D' or timeseries_partition_size == 'P7D':
            timestamp_str = timestamp.strftime("%Y_%m_%d-00:00:00")

        # Since unique_timestamps is sorted, we can iterate thru
        # each timestamp to collect all the events which map to the
        # same timestamp_str, then write them to s3 as a single file
        # when timestamp_str has changed. The following if condition handles
        # this:

        # Write rows to s3 if we're processing a new timestamp
        if timestamp_str_old != timestamp_str:
            # Yes, this timestamp maps to a new timestamp_str.
            # From now on check to see when timestamp_str is different from this one
            if timestamp_str_old == '':
                # ...unless we're just starting out.
                timestamp_str_old = timestamp_str
                # Get all the events that occurred at the first timestamp
                # so that they can be recorded when we read the next timestamp.
                df_partition = df[df[timestamp_column] == timestamp]
                df_partition[timestamp_column] = df_partition[timestamp_column].dt.strftime(datetime_format)
                # Now proceed to the next unique timestamp.
                continue
            # write the old df_partition to s3
            output_file = 's3://' + output_bucket + '/' + amc_str + '/' + dataset_id + '/' + timeseries_partition_size + '/' + filename + '-' + timestamp_str_old + '.gz'
            if len(df_partition) > 0:
                output_files.append(output_file)
                # Earlier, we rounded the timestamp_column to minute (60s) granularity.
                # Now we need to revert it back to full precision in order to avoid data loss.
                df_partition[timestamp_column] = df_partition[timestamp_full_precision].dt.strftime(datetime_format)
                df_partition.drop(timestamp_full_precision, axis=1, inplace=True)
                print(writing + str(len(df_partition)) + rows_to + output_file)
                num_rows += len(df_partition)
                if content_type == json_content_type:
                    wr.s3.to_json(df=df_partition, path=output_file, compression='gzip', lines=True, orient='records')
                elif content_type == csv_content_type:
                    wr.s3.to_csv(df=df_partition, path=output_file, compression='gzip', header=True, index=False)
            # reset df_partition for the new timestamp string
            df_partition = pd.DataFrame()
            timestamp_str_old = timestamp_str
            # Get all the events that occurred at this timestamp
            df_partition = df[df[timestamp_column] == timestamp]
            df_partition[timestamp_column] = df_partition[timestamp_column].dt.strftime(datetime_format)
        else:
            # Append all the events that occurred at this timestamp to df_partition
            df_partition2 = pd.DataFrame()
            df_partition2 = df[df[timestamp_column] == timestamp]
            df_partition2[timestamp_column] = df_partition2[timestamp_column].dt.strftime(datetime_format)
            df_partition = df_partition.append(df_partition2, ignore_index=True)
    # write the last timestamp to s3
    output_file = 's3://' + output_bucket + '/' + amc_str + '/' + dataset_id + '/' + timeseries_partition_size + '/' + filename + '-' + timestamp_str_old + '.gz'
    if len(df_partition) > 0:
        output_files.append(output_file)
        # Earlier, we rounded the timestamp_column to minute (60s) granularity.
        # Now we need to revert it back to full precision in order to avoid data loss.
        df_partition[timestamp_column] = df_partition[timestamp_full_precision].dt.strftime(datetime_format)
        df_partition.drop(timestamp_full_precision, axis=1, inplace=True)
        print(writing + str(len(df_partition)) + rows_to + output_file)
        num_rows += len(df_partition)
        if content_type == json_content_type:
            wr.s3.to_json(df=df_partition, path=output_file, compression='gzip', lines=True, orient='records')
        elif content_type == csv_content_type:
            wr.s3.to_csv(df=df_partition, path=output_file, compression='gzip', header=True, index=False)

    output = {
        'timeseries granularity': timeseries_partition_size,
        'output files': output_files
    }
    print(output)
else:
    dataset_type = 'DIMENSION'
    output_file = 's3://' + output_bucket + '/' + amc_str + '/' + dataset_id + '/dimension/' + filename + '.gz'
    print(writing + str(len(df)) + rows_to + output_file)
    num_rows += len(df)
    if content_type == json_content_type:
        wr.s3.to_json(df=df, path=output_file, compression='gzip', lines=True, orient='records')
    elif content_type == csv_content_type:
        wr.s3.to_csv(df=df, path=output_file, compression='gzip', header=True, index=False)
    output = {
        'output files': output_file
    }
    print(output)

###############################
# SAVE PERFORMANCE METRICS
###############################

if enable_anonymous_data == 'true':
    glue_client = boto3.client('glue')
    lambda_client = boto3.client('lambda')
    response = glue_client.get_job_run(
        JobName=job_name,
        RunId=job_run_id,
        PredecessorsIncluded=True|False
    )
    started_on = response['JobRun']['StartedOn'].replace(tzinfo=None)
    glue_job_duration = (datetime.now() - started_on).total_seconds()
    metrics = {'RequestType': 'Workload', 'Metrics': {'SolutionId': solution_id, 'UUID': uuid, 'numBytes': num_bytes, 'numRows': num_rows, 'datasetType': dataset_type, 'glueJobDuration': glue_job_duration}}
    response = lambda_client.invoke(
        FunctionName=anonymous_data_logger,
        InvocationType='Event',
        Payload=json.dumps(metrics).encode('utf-8')
    )
    print("Performance metrics:")
    print(metrics)
