import base64
import json
import sys
from datetime import datetime

import awswrangler as wr
import boto3
import pandas as pd
import re

###############################
# CONSTANTS
###############################

# Resolve sonarqube code smells
WRITING = "Writing "
ROWS_TO = " rows to "
JSON_CONTENT_TYPE = "application/json"
CSV_CONTENT_TYPE = "text/csv"
GZIP_CONTENT_TYPE = "application/x-gzip"
AMC_STR = "amc"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

###############################
# HELPER FUNCTIONS
###############################


def write_to_s3(df: pd.DataFrame, filepath: str, content_type: str) -> None:
    if content_type == JSON_CONTENT_TYPE:
        wr.s3.to_json(
            df=df,
            path=filepath,
            compression="gzip",
            lines=True,
            orient="records",
        )
    elif content_type == CSV_CONTENT_TYPE:
        wr.s3.to_csv(
            df=df,
            path=filepath,
            compression="gzip",
            header=True,
            index=False,
        )


def encode_endpoint(text: str) -> str:
    destination_endpoint_encoded = base64.b64encode(
        text.encode("ascii")
    ).decode("ascii")

    return destination_endpoint_encoded


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
        self.country_code = args["country_code"]
        self.destination_endpoints = list(
            json.loads(args["destination_endpoints"])
        )

        # other attributes
        self.data = pd.DataFrame()
        self.filename = self.key.split("/")[-1]
        self.num_rows = 0
        self.dataset_type = ""

    def read_bucket(self) -> None:
        s3 = boto3.client("s3")
        response = s3.head_object(Bucket=self.source_bucket, Key=self.key)
        content_type = response["ContentType"]
        print("CONTENT TYPE: " + content_type)
        num_bytes = response["ContentLength"]
        print("FILE SIZE: " + str(num_bytes))

        self.content_type = content_type
        self.num_bytes = num_bytes

    def load_input_data(self) -> None:
        df = self.data
        chunksize = 2000

        # Configure all PII-designated fields to be read as strings
        # This avoids reading phone or zip values as floats and dropping data or requiring additional transformation before normalization
        pii_column_names = {}
        for field in self.pii_fields:
            pii_column_names[field["column_name"]] = str

        content_type = self.content_type

        # if a gzip, determine whether it is a zipped json or csv
        if self.content_type == GZIP_CONTENT_TYPE:
            # regex file name to see if json.gz
            if re.search("\.json\.gz$", self.key):
                content_type = JSON_CONTENT_TYPE

            # regex file name to see if csv.gz
            elif re.search("\.csv\.gz$", self.key):
                content_type = CSV_CONTENT_TYPE

        if content_type == JSON_CONTENT_TYPE:
            df_chunks = wr.s3.read_json(
                path=["s3://" + self.source_bucket + "/" + self.key],
                chunksize=chunksize,
                lines=True,
                dtype=pii_column_names,
            )
        elif content_type == CSV_CONTENT_TYPE:
            df_chunks = wr.s3.read_csv(
                path=["s3://" + self.source_bucket + "/" + self.key],
                chunksize=chunksize,
                dtype=pii_column_names,
            )
        else:
            print("Unsupported content type: " + self.content_type)
            sys.exit(1)

        for chunk in df_chunks:
            # Save each chunk
            df = pd.concat([chunk, df])

        self.data = df

    def remove_deleted_fields(self) -> None:
        df = self.data
        # Delete the columns that were indicated by the user to be deleted.
        for column_name in self.deleted_fields:
            df.drop(column_name, axis=1, inplace=True)

        self.data = df

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
                "datasetType": self.dataset_type,
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


class FactDataset(DataFile):
    def __init__(self, args):
        super().__init__(args)

        self.timestamp_column = args["timestamp_column"]
        self.timeseries_partition_size = args["period"]
        self.timestamp_str_old = ""
        self.dataset_type = "FACT"

    def _format_output(self, destination_endpoint_encoded):
        return (
            "s3://"
            + self.output_bucket
            + "/"
            + AMC_STR
            + "/"
            + self.dataset_id
            + "/"
            + self.timeseries_partition_size
            + "/"
            + destination_endpoint_encoded
            + "/"
            + re.split('.gz', self.filename, 0)[0]
            + "-"
            + self.timestamp_str_old
            + ".gz"
        )

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

    def time_series_partitioning(self) -> tuple:
        df = self.data
        # AMC supports "Units of upload" of PT1M (minute-by-minute) granularity or longer
        # so we round timestamps to the nearest minute, below.
        # But before we write that data to AMC, we will want to restore the timestamp to full precision.
        # So we record that full precision here so that it can be restored later.
        df["timestamp_full_precision"] = df[self.timestamp_column]
        df[self.timestamp_column] = df[self.timestamp_column].dt.round("Min")

        # Prepare to calculate time deltas by sorting on the timeseries column
        self.unique_timestamps = pd.DataFrame(
            df[self.timestamp_column].unique()
        )
        self.unique_timestamps = self.unique_timestamps.rename(
            columns={0: "timestamp"}
        )
        self.unique_timestamps = self.unique_timestamps.sort_values(
            by="timestamp"
        )

        if self.timeseries_partition_size == "autodetect":
            # Store the time delta between each sequential event
            self.unique_timestamps["timedelta"] = (
                self.unique_timestamps["timestamp"]
                - self.unique_timestamps["timestamp"].shift()
            )

            # Here we calculate the partition size based on the minimum delta between timestamps in the dataset.
            zero_timedelta = "0 days 00:00:00"
            min_timedelta = (
                self.unique_timestamps["timedelta"][
                    self.unique_timestamps["timedelta"] != zero_timedelta
                ]
                .dropna()
                .min()
            )

            # Initialize timeseries partition size. The available options are:
            #   PT1M (minute)
            #   PT1H (hour)
            #   P1D (day)
            #   P7D (7 days)
            self.timeseries_partition_size = "PT1M"

            # If the smallest delta between timestamps is at least 60 minutes (3600 seconds), then we'll partition timeseries data into one file for each hour.
            # Note, timedelta.seconds rolls over to 0 when the timedelta reaches 1 day, so we need to check timedelta.days too:
            if min_timedelta.seconds >= 3600 and min_timedelta.days == 0:
                self.timeseries_partition_size = "PT1H"

            # If the smallest delta between timestamps is at least 24 hours, then we'll partition timeseries data into one file for each day.
            elif 0 < min_timedelta.days < 7:
                self.timeseries_partition_size = "P1D"

            # If the smallest delta between timestamps is at least 7 days, then we'll partition timeseries data into one file for each week.
            elif min_timedelta.days >= 7:
                self.timeseries_partition_size = "P7D"

        self.data = df

    def upload_dataset(self, df: pd.DataFrame) -> list:
        uploads = []
        for destination_endpoint in self.destination_endpoints:
            # The destination endpoints are URLs.
            # We're going to pass these endpoints to the amc_uploader.py Lambda function
            # via the S3 key. But we can't put forward slashes, like "https://" in the S3
            # key. So, we encode the endpoint here and use that in the s3key.
            # The amc_uploader.py can use base64 decode to get the original endpoint URL.
            destination_endpoint_encoded = encode_endpoint(
                destination_endpoint
            )
            # write the old df_partition to s3
            output_file = self._format_output(destination_endpoint_encoded)
            print(WRITING + str(len(df)) + ROWS_TO + output_file)
            self.num_rows += len(df)
            write_to_s3(
                df=df, filepath=output_file, content_type=self.content_type
            )
            uploads.append(output_file)

        return uploads

    def save_fact_output(self) -> None:
        df = self.data

        # Partition the timeseries dataset into separate files for each
        # unique timestamp.
        output_files = []

        # Initialize a dataframe to hold the dataset for this timestamp:
        df_partition = pd.DataFrame()
        for timestamp in self.unique_timestamps.timestamp:
            # In order to avoid errors like this:
            #   "The timeWindowStart ... does not align with the data set's period"
            # we need to save file names with timestamps that use
            #   00 for seconds in the case of PT1M, PT1H, P1D, and P7D,
            #   00 for minutes and seconds in the case of PT1H, P1D, P7D,
            #   and 00 for hours, minutes, and seconds in the case of P1D, P7D.
            timestamp_str = timestamp.strftime("%Y_%m_%d-%H:%M:00")
            if self.timeseries_partition_size in ("PT1H", "P1D", "P7D"):
                timestamp_str = timestamp.strftime("%Y_%m_%d-%H:00:00")
            if self.timeseries_partition_size in ("P1D", "P7D"):
                timestamp_str = timestamp.strftime("%Y_%m_%d-00:00:00")

            # Since unique_timestamps is sorted, we can iterate thru
            # each timestamp to collect all the events which map to the
            # same timestamp_str, then write them to s3 as a single file
            # when timestamp_str has changed. The following if condition handles
            # this:

            # Write rows to s3 if we're processing a new timestamp
            if self.timestamp_str_old != timestamp_str:
                # Yes, this timestamp maps to a new timestamp_str.
                # From now on check to see when timestamp_str is different from this one
                if self.timestamp_str_old == "":
                    # ...unless we're just starting out.
                    self.timestamp_str_old = timestamp_str
                    # Get all the events that occurred at the first timestamp
                    # so that they can be recorded when we read the next timestamp.
                    df_partition = df[df[self.timestamp_column] == timestamp]
                    df_partition[self.timestamp_column] = df_partition[
                        self.timestamp_column
                    ].dt.strftime(DATETIME_FORMAT)
                    # Now proceed to the next unique timestamp.
                    continue

                if len(df_partition) > 0:
                    # Earlier, we rounded the timestamp_column to minute (60s) granularity.
                    # Now we need to revert it back to full precision in order to avoid data loss.
                    df_partition[self.timestamp_column] = df_partition[
                        "timestamp_full_precision"
                    ].dt.strftime(DATETIME_FORMAT)
                    df_partition.drop(
                        "timestamp_full_precision", axis=1, inplace=True
                    )
                    uploads = self.upload_dataset(df=df_partition)
                    output_files.extend(uploads)
                # reset df_partition for the new timestamp string
                self.timestamp_str_old = timestamp_str
                # Get all the events that occurred at this timestamp
                df_partition = df[df[self.timestamp_column] == timestamp]
                df_partition[self.timestamp_column] = df_partition[
                    self.timestamp_column
                ].dt.strftime(DATETIME_FORMAT)

            else:
                # Append all the events that occurred at this timestamp to df_partition
                df_partition2 = df[df[self.timestamp_column] == timestamp]
                df_partition2[self.timestamp_column] = df_partition2[
                    self.timestamp_column
                ].dt.strftime(DATETIME_FORMAT)
                df_partition = df_partition.append(
                    df_partition2, ignore_index=True
                )

        # write the last timestamp to s3
        if len(df_partition) > 0:
            # Earlier, we rounded the timestamp_column to minute (60s) granularity.
            # Now we need to revert it back to full precision in order to avoid data loss.
            df_partition[self.timestamp_column] = df_partition[
                "timestamp_full_precision"
            ].dt.strftime(DATETIME_FORMAT)
            df_partition.drop("timestamp_full_precision", axis=1, inplace=True)
            uploads = self.upload_dataset(df=df_partition)
            output_files.extend(uploads)

        output = {
            "timeseries granularity": self.timeseries_partition_size,
            "output files": output_files,
        }
        print(output)


class DimensionDataset(DataFile):
    def __init__(self, args):
        super().__init__(args)

        self.dataset_type = "DIMENSION"

    def save_dimension_output(self):
        df = self.data
        for destination_endpoint in self.destination_endpoints:
            # The destination endpoints are URLs.
            # We're going to pass these endpoints to the amc_uploader.py Lambda function
            # via the S3 key. But we can't put forward slashes, like "https://" in the S3
            # key. So, we encode the endpoint here and use that in the s3key.
            # The amc_uploader.py can use base64 decode to get the original endpoint URL.
            destination_endpoint_encoded = encode_endpoint(
                destination_endpoint
            )
            output_file = (
                "s3://"
                + self.output_bucket
                + "/"
                + AMC_STR
                + "/"
                + self.dataset_id
                + "/dimension/"
                + destination_endpoint_encoded
                + "/"
                + self.filename
                + ".gz"
            )
        print(WRITING + str(len(df)) + ROWS_TO + output_file)
        self.num_rows += len(df)
        write_to_s3(
            df=df, filepath=output_file, content_type=self.content_type
        )

        output = {"output files": output_file}
        print(output)
