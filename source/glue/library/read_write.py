# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import re
import sys
from datetime import datetime
import math
import awswrangler as wr
import boto3
import pandas as pd
import numpy as np
import os
import urllib.parse

###############################
# CONSTANTS
###############################

# Resolve sonarqube code smells
WRITING = "Writing "
ROWS_TO = " rows to "
AMC_STR = "amc"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
S3_PREFIX = "s3://"

pandas_options_to_write_json = {
    "compression": "gzip",
    "lines": True,
    "orient": "records",
}

pandas_options_to_write_csv = {
    "compression": "gzip",
    "header": True,
    "index": False,
}

GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES = 500.0 * 1000000


###############################
# HELPER FUNCTIONS
###############################


def write_to_s3(df: pd.DataFrame, filepath: str, file_format: str) -> None:
    if file_format == "JSON":
        wr.s3.to_json(
            df=df,
            path=filepath,
            **pandas_options_to_write_json
        )
    elif file_format == "CSV":
        wr.s3.to_csv(
            df=df,
            path=filepath,
            **pandas_options_to_write_csv
        )


###############################
# MAIN METHODS
###############################


class DataFile:
    # pylint: disable=too-many-instance-attributes
    # All instance attributes are needed.
    def __init__(self, args):
        # required params
        self.job_name = args["JOB_NAME"]
        self.job_run_id = args["JOB_RUN_ID"]
        self.solution_id = args["solution_id"]
        self.uuid = args["uuid"]
        self.enable_anonymous_data = args["enable_anonymous_data"]
        self.anonymous_data_logger = args["anonymous_data_logger"]
        self.source_bucket = args["source_bucket"]
        self.key = args["source_key"]
        self.output_bucket = args["output_bucket"]
        self.pii_fields = list(json.loads(args["pii_fields"]))
        self.deleted_fields = list(json.loads(args["deleted_fields"]))
        self.dataset_id = args["dataset_id"]
        self.amc_instances = list(json.loads(args["amc_instances"]))
        self.user_id = args["user_id"]
        self.file_format = args["file_format"]
        self.update_strategy = args["update_strategy"]

        # other attributes
        self.data = pd.DataFrame()
        self.filename = self.key.split("/")[-1]
        self.num_rows = 0
        self.num_bytes = 0
        self.partition_identifier = ""

        # optional params
        resolve_optional_params = [
            "timestamp_column",
            "country_code"
        ]

        for optional_param in resolve_optional_params:
            setattr(self, optional_param, None)
            if optional_param in args.keys():
                setattr(self, optional_param, args[optional_param])

    def read_bucket(self) -> None:
        s3 = boto3.client("s3")
        response = s3.head_object(Bucket=self.source_bucket, Key=self.key)
        num_bytes = response["ContentLength"]
        print("FILE SIZE: " + str(num_bytes))
        self.num_bytes = num_bytes

    def load_input_data(self) -> None:
        df = self.data
        chunksize = 2000

        # Configure all PII-designated fields to be read as strings
        # This avoids reading phone or zip values as floats and dropping data or requiring additional transformation before normalization
        pii_column_names = {}
        for field in self.pii_fields:
            pii_column_names[field["column_name"]] = str

        if self.file_format == "JSON":
            df_chunks = wr.s3.read_json(
                path=[S3_PREFIX + self.source_bucket + "/" + self.key],
                chunksize=chunksize,
                lines=True,
                dtype=pii_column_names,
            )
        elif self.file_format == "CSV":
            df_chunks = wr.s3.read_csv(
                path=[S3_PREFIX + self.source_bucket + "/" + self.key],
                chunksize=chunksize,
                dtype=pii_column_names,
            )
        else:
            print("Unsupported file format: " + self.file_format)
            sys.exit(1)

        for chunk in df_chunks:
            # Save each chunk
            df = pd.concat([chunk, df])

        print(f"DATAFRAME ROWS: {len(df)}")
        self.data = df

    def remove_deleted_fields(self) -> None:
        # Delete the columns that were indicated by the user to be deleted.
        for column_name in self.deleted_fields:
            self.data.drop(column_name, axis=1, inplace=True)

    def save_performance_metrics(self) -> None:
        glue_client = boto3.client("glue")
        lambda_client = boto3.client("lambda")
        response = glue_client.get_job_run(
            JobName=self.job_name,
            RunId=self.job_run_id,
            PredecessorsIncluded=True | False,
        )
        started_on = response["JobRun"]["StartedOn"].replace(tzinfo=None)
        glue_job_duration = (datetime.now() - started_on).total_seconds()
        metrics = {
            "RequestType": "Workload",
            "Metrics": {
                "SolutionId": self.solution_id,
                "UUID": self.uuid,
                "numBytes": self.num_bytes,
                "numRows": self.num_rows,
                "glueJobDuration": glue_job_duration,
            },
        }
        lambda_client.invoke(
            FunctionName=self.anonymous_data_logger,
            InvocationType="Event",
            Payload=json.dumps(metrics).encode("utf-8"),
        )
        print("Performance metrics:")
        print(metrics)
    
    def _format_output(self, amc_instance_id_user_id):
        country_code = self.country_code
        if not country_code:
            country_code = json.dumps(country_code)
        output = [
            f"{S3_PREFIX}{self.output_bucket}",
            AMC_STR,
            self.dataset_id,
            self.update_strategy,
            self.file_format,
            country_code,
            amc_instance_id_user_id,
            f"{re.split('.gz', self.filename, 0)[0]}-{self.partition_identifier}.gz",
        ]
        return "/".join(output)
    
    def timestamp_transform(self) -> None:
        df = self.data

        try:
            df[self.timestamp_column] = pd.to_datetime(
                df[self.timestamp_column], utc=True
            )
        except ValueError as e:
            print(e)
            print(
                "Failed to parse timeseries in column " + self.timestamp_column
            )
            print("Verify that timeseries is formatted according to ISO 8601.")
            raise e
        except Exception as e:
            print(e)
            print(
                "Failed to parse timeseries in column " + self.timestamp_column
            )
            raise e

        self.data = df

    def upload_dataset(self, df: pd.DataFrame) -> list:
        uploads = []
        for amc_instance in self.amc_instances:
            # We're going to pass these amc_instance to the amc_uploader.py Lambda function
            # amc_instance is concatenated with user_id for Aws secret.
            amc_instance_id_user_id = f"{amc_instance}|{self.user_id}"
            # write the old df_partition to s3
            output_file = self._format_output(amc_instance_id_user_id)
            print(WRITING + str(len(df)) + ROWS_TO + output_file)
            self.num_rows += len(df)
            write_to_s3(
                df=df, filepath=output_file, file_format=self.file_format
            )
            s3key = output_file[output_file.find(self.output_bucket) + (len(self.output_bucket) + 1):]
            s3 = boto3.client("s3")
            s3.put_object_tagging(
                Bucket=self.output_bucket,
                Key=s3key,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'instanceId',
                            'Value': amc_instance
                        },
                    ]
                },
            )
            uploads.append(output_file)

        return uploads

    def estimate_compression_ratio(self) -> float:
        """
        This function estimates gzip compression ratio using some data sampled from raw data.
        """
        df = self.data
        df_sample = df.sample(frac=0.001)
        # Get memory usage of sample data in bytes
        df_size = df_sample.memory_usage(index=True, deep=True).sum()
        tmp_compressed_filename = 'tmp_sample_data.gz'
        # Generate a temporary gzipped file to get the compressed file size
        if self.file_format == "JSON":
            df_sample.to_json(
                tmp_compressed_filename,
                **pandas_options_to_write_json
            )
        elif self.file_format == "CSV":
            df_sample.to_csv(
                tmp_compressed_filename,
                **pandas_options_to_write_csv
            )
        compressed_size = os.path.getsize(tmp_compressed_filename)
        # Delete the temporary gzipped file
        os.remove(tmp_compressed_filename)

        compression_ratio = df_size / compressed_size
        return compression_ratio

    def estimate_number_of_partitions(self):
        if self.num_bytes < GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES:
            print(
                f"Uncompressed file size is smaller than {GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES} bytes, no need to partition file")
            return 1

        # Add 2 more partitions into the calculated partition number to
        # reduce chance of gzipped file size > GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES
        number_of_partition = 2
        try:
            compression_ratio = self.estimate_compression_ratio()
            compressed_file_size = self.num_bytes / compression_ratio
            number_of_partition += math.ceil(compressed_file_size / GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES)
        except Exception as e:
            # If there is an error in calculating partition number, do nothing. The function
            # returns default partition number=number_of_partition
            print(e)
        return number_of_partition

    def convert_timestamp_format(self, df: pd.DataFrame) -> None:
        try:
            # Convert TIMESTAMP and DATE columns to the accepted format.
            df[self.timestamp_column] = df[self.timestamp_column].dt.strftime(DATETIME_FORMAT)
        except Exception as e:
            print(e)
            print(
                f"Failed to convert timeseries in column {self.timestamp_column} to accepted format {DATETIME_FORMAT}"
            )
            raise e

    def save_output(self) -> None:
        df = self.data
        # Partition the dataset into separate files for file size, so that AMC is uploading files < 500MB (compressed)
        output_files = []
        number_of_partitions = self.estimate_number_of_partitions()
        dfs_partition = np.array_split(df, number_of_partitions)

        for i, df_partition in enumerate(dfs_partition):
            self.partition_identifier = str(i)
            print(f"PARTITION FILE {self.partition_identifier}, ROWS: {len(dfs_partition)}")
            if self.timestamp_column:
                self.convert_timestamp_format(df=df_partition)
            uploads = self.upload_dataset(df=df_partition)
            output_files.extend(uploads)

        if not output_files:
            print("No output files to put in manifest")
        else:
            s3 = boto3.client("s3")
            # Each output_file is an s3Key in the following format:
            #   amc/[dataset_id]/[update_strategy]/[country_code]/[instance_id|user_id]/[data_file]-[partition_number].gz
            # The manifest file will have the same S3 key prefix as each output_file
            # except it will not contain the partition number, and it will have suffix .txt instead of .gz.
            # Parse the S3 key prefix for each output_file, so we can construct the S3 key for the manifest file.
            _, dataset_id, update_strategy, file_format, country_code, instance_id_user_id, filename_quoted = output_files[0].replace(f's3://{self.output_bucket}/', '').split('/')
            instance_id, user_id = instance_id_user_id.split("|")
            filename = urllib.parse.unquote_plus(filename_quoted)
            filename_base = filename.rsplit('-', 1)[0].rsplit('.', 1)[0]

            for amc_instance in self.amc_instances:
                # Generate separate manifest files for each user-specified AMC instance
                manifest_file = f"amc/{dataset_id}/{update_strategy}/{file_format}/{country_code}/{amc_instance}|{user_id}/{filename_base}.txt"
                data = "\n".join([line for line in output_files if amc_instance in line])
                # Save the manifest file to the S3 key derived above.
                response = s3.put_object(Bucket=self.output_bucket, Key=manifest_file, Body=data)
                # Check if that operation was successful.
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    print(f"Created manifest file: s3://{self.output_bucket}{manifest_file}\n")
                    # Tag the manifest file to the target AMC instance, as required by AMC.
                    s3.put_object_tagging(
                        Bucket=self.output_bucket,
                        Key=manifest_file,
                        Tagging={
                            'TagSet': [
                                {
                                    'Key': 'instanceId',
                                    'Value': amc_instance
                                },
                            ]
                        },
                    )
                else:
                    print(f"Error creating manifest file: {response}")

        output = {
            "output files": output_files,
        }
        print(output)
