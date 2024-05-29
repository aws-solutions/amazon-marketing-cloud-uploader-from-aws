# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# ###############################################################################
# PURPOSE:
#   * Regression test for amc_transformation.
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name amc_transformation/test_amc_transformation.py
###############################################################################

import os
import shutil
from unittest.mock import ANY, patch, Mock, MagicMock
from unittest import TestCase
from pathlib import Path
import pandas as pd
import pytest
from glue.library import read_write as rw
from glue.library import transform
from glue.library.address_normalizer import load_address_map_helper
from moto import mock_aws
import boto3
import sys


###############################
# TEST NORMALIZER UTILS
###############################

def test_load_address_map_helper():
    address_map = load_address_map_helper()
    assert address_map["NumberIndicators"]
    assert address_map["DirectionalWords"]
    assert address_map["DefaultStreetSuffixes"]
    assert address_map["USStreetSuffixes"]
    assert address_map["USSubBuildingDesignator"]
    assert address_map["ITStreetPrefixes"]
    assert address_map["FRStreetDesignator"]
    assert address_map["ESStreetPrefixes"]
    assert address_map["UKOrganizationSuffixes"]
    assert address_map["UKStreetSuffixes"]
    assert address_map["UKSubBuildingDesignator"]


###############################
# TEST NORMALIZATION & HASHING
###############################

def _match_data(test: pd.DataFrame, check: pd.DataFrame, pii_fields: list):
    df_concat = pd.merge(
        test, check, how="inner", on="id", suffixes=["_test", "_check"]
    )

    cols = ["id", "field", "test", "check"]
    lst = []
    for field in pii_fields:
        column_name = field["column_name"]
        for _, row in df_concat.iterrows():
            test_val = row[f"{column_name}_test"]
            check_val = row[f"{column_name}_check"]

            if test_val != check_val:
                lst.append([row["id"], column_name, test_val, check_val])

    invalid = pd.DataFrame(data=lst, columns=cols)
    return invalid


def _return_results(invalid: pd.DataFrame, raw: pd.DataFrame):
    df_concat = pd.merge(
        invalid,
        raw,
        how="left",
        on="id",
    )

    cols = ["id", "field", "raw", "test", "check"]
    lst = []
    for _, row in df_concat.iterrows():
        invalid_field = row.loc["field"]
        # if phone number is invalid based on AMC criteria, we do not count this as a normalization mismatch
        if not (
            invalid_field == "phone"
            and row.loc["check"]
            == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ):
            lst.append(
                [
                    row.loc["id"],
                    invalid_field,
                    row.loc[invalid_field],
                    row.loc["test"],
                    row.loc["check"],
                ]
            )

    results = pd.DataFrame(data=lst, columns=cols)
    return results


class NormalizationTest:
    def __init__(self, country):
        self.country = country.lower()
        self.pii_fields = [
            {"pii_type": "NAME", "column_name": "first_name"},
            {"pii_type": "NAME", "column_name": "last_name"},
            {"pii_type": "EMAIL", "column_name": "email"},
            {"pii_type": "ADDRESS", "column_name": "address"},
            {"pii_type": "PHONE", "column_name": "phone"},
            {"pii_type": "CITY", "column_name": "city"},
            {"pii_type": "ZIP", "column_name": "zip"},
        ]
        if self.country in ("us", "ca", "fr", "it", "in", "es", "de", "ca"):
            self.pii_fields.append(
                {"pii_type": "STATE", "column_name": "state"}
            )

    # Test amc_transformations normalization & hashing
    def _normalization_matching(self):
        country = self.country

        raw = pd.read_json(
            f"unit_test/amc_transformation/sample_data/test_{country}/{country}_raw.json",
            dtype=str,
        )
        check = pd.read_json(
            f"unit_test/amc_transformation/sample_data/test_{country}/{country}_check.json",
            dtype=str,
        )

        normalized = transform.transform_data(
            data=raw.copy(),
            pii_fields=self.pii_fields,
            country_code=country.upper(),
        )
        hashed = transform.hash_data(
            data=normalized, pii_fields=self.pii_fields
        )

        invalid = _match_data(
            test=hashed, check=check, pii_fields=self.pii_fields
        )
        results = _return_results(invalid=invalid, raw=raw.copy())

        self.results = results

    # Export results locally
    def _export_results(self, fp):
        country = self.country
        results = self.results

        if len(results) > 0:
            if not os.path.exists(fp):
                os.mkdir(fp)
            if not os.path.exists(f"{fp}/{country}"):
                os.mkdir(f"{fp}/{country}")
            results.to_csv(f"{fp}/{country}/results.csv")
            results.to_json(
                f"{fp}/{country}/results.json",
                orient="records",
            )

            print(f"Invalid results for {country}:")
            print(results.groupby(["field"])["id"].count())
            print("")

        else:
            print(
                f"Nothing to export for country: {country}. All tests passed!"
            )


def test_amc_transformations(countries=None):
    countries = countries or [
        "us",
        "gb",
        "jp",
        "in",
        "it",
        "es",
        "ca",
        "de",
        "fr",
    ]
    test_results_filepath = "unit_test/amc_transformation/test_results"

    if os.path.exists(test_results_filepath):
        shutil.rmtree(test_results_filepath)

    for item in countries:
        test = NormalizationTest(country=item)
        test._normalization_matching()
        test._export_results(fp=test_results_filepath)

        assert len(test.results) == 0, item


"""
Unit tests for the check_params function.

These tests validate the behavior of check_params() under different 
parameter conditions: valid params, missing required params, invalid 
param values. Each test case covers a different code path within 
check_params().
"""

# Example parameters for testing
# REQUIRED_PARAMS = ['file_format', 'amc_instances']
# OPTIONAL_PARAMS = ['dataset_id', 'country_code', 'timestamp_column']
# RESOLVED_OPTIONS = {
#     'file_format': 'CSV',
#     'amc_instances': 'amc_instance_1,amc_instance_2',
#     'dataset_id': '1234',
#     'country_code': 'US',
#     'timestamp_column': 'timestamp'
# }

# Mock data for testing
mock_params = {
    "JOB_NAME": "mock_job",
    "solution_id": "mock_solution_id",
    "uuid": "mock_uuid",
    "enable_anonymous_data": "true",
    "anonymous_data_logger": "mock_logger",
    "source_bucket": "mock_source_bucket",
    "source_key": "mock_source_key",
    "output_bucket": "mock_output_bucket",
    "pii_fields": "mock_pii_fields",
    "deleted_fields": "mock_deleted_fields",
    "dataset_id": " mock_dataset_id ",
    "user_id": "mock_user_id",
    "file_format": "CSV",
    "amc_instances": "mock_amc_instance",
    "update_strategy": "mock_update_strategy",
    "timestamp_column": " mock_timestamp ",
    "country_code": "US"
}

mock_fail_params = {
    "JOB_NAME": "mock_job",
    "solution_id": "mock_solution_id",
    "uuid": "mock_uuid",
    "enable_anonymous_data": "true",
    "anonymous_data_logger": "mock_logger",
    "source_bucket": "mock_source_bucket",
    "source_key": "mock_source_key",
    "output_bucket": "mock_output_bucket",
    "pii_fields": "mock_pii_fields",
    "deleted_fields": "mock_deleted_fields",
    "dataset_id": " mock_dataset_id ",
    "user_id": "mock_user_id",
    "file_format": "ABC",
    "amc_instances": [],
    "update_strategy": "mock_update_strategy",
    "timestamp_column": " mock_timestamp ",
    "country_code": "XY"
}

class TestCheckParams(TestCase):
    def setUp(self):
        # Create a mock for the awsglue.utils module
        self.mock_awsglue_utils = MagicMock()
        # Mock GlueArgumentError and getResolvedOptions specifically
        self.mock_awsglue_utils.GlueArgumentError = Exception  # Use Exception for simplicity
        self.mock_awsglue_utils.getResolvedOptions.side_effect = lambda argv, params: {key: mock_params[key] for key in params}
        self.side_effect_fail = lambda argv, params: {key: mock_fail_params[key] for key in params}
        # Create a mock for
        # Patch sys.modules to include the mocked awsglue.utils
        self.patcher = patch.dict('sys.modules', {
            'awsglue.utils': self.mock_awsglue_utils,
            'awsglue': MagicMock()  # Mock the entire awsglue if necessary
        })
        self.patcher.start()

    def tearDown(self):
        # Stop the patcher to clean up the sys.modules
        self.patcher.stop()

    @patch("library.read_write.DataFile")
    @patch("library.transform.hash_data")
    @patch("library.transform.transform_data")
    @patch("sys.exit")
    def test_success_path(
        self, mock_exit, mock_transform_data, mock_hash_data, mock_data_file
    ):
        # Mock the DataFile methods
        mock_data_file_instance = MagicMock()
        mock_data_file.return_value = mock_data_file_instance

        # Set return values for mock methods
        mock_transform_data.return_value = "transformed_data"
        mock_hash_data.return_value = "hashed_data"
        mock_data_file_instance.data = "mock_data"

        # Mock sys.argv for getResolvedOptions to parse
        sys.argv = ["script_name.py"]

        # Import the module under test
        import glue.amc_transformations

        # Assertions to check correct behavior
        self.mock_awsglue_utils.getResolvedOptions.assert_called()

    @patch("library.read_write.DataFile")
    @patch("library.transform.hash_data")
    @patch("library.transform.transform_data")
    @patch("sys.exit")
    def test_exception_paths(
        self, mock_exit, mock_transform_data, mock_hash_data, mock_data_file
    ):
        mock_exit.side_effect = RuntimeError("Exit called")

        # Mock the DataFile methods
        mock_data_file_instance = MagicMock()
        mock_data_file.return_value = mock_data_file_instance

        # Set return values for mock methods
        mock_transform_data.return_value = "transformed_data"
        mock_hash_data.return_value = "hashed_data"
        mock_data_file_instance.data = "mock_data"

        # Mock sys.argv for getResolvedOptions to parse
        sys.argv = ["script_name.py"]

        # Import the module under test
        import glue.amc_transformations

        # negative test for GlueArgumentError
        self.mock_awsglue_utils.getResolvedOptions.side_effect = self.mock_awsglue_utils.GlueArgumentError

        # test first sys.exit call
        with self.assertRaises(RuntimeError):
            glue.amc_transformations.check_params(mock_params, {})

        # test bad country code
        self.mock_awsglue_utils.getResolvedOptions.side_effect = self.side_effect_fail
        with self.assertRaises(RuntimeError):
            glue.amc_transformations.check_params(mock_params, {})

        # test bad file format
        mock_exit.side_effect = [Mock(), RuntimeError("Exit called")]
        with self.assertRaises(RuntimeError):
            glue.amc_transformations.check_params(mock_params, {})

        # test bad amc instances
        mock_exit.side_effect = [Mock(), Mock(), RuntimeError("Exit called")]
        with self.assertRaises(RuntimeError):
            glue.amc_transformations.check_params(mock_params, {})


###############################
# TEST READING & WRITING
###############################

test_args = {
    "source_bucket": "test",
    "output_bucket": "test",
    "source_key": "test",
    "pii_fields": '[{"column_name":"address","pii_type":"ADDRESS"},{"column_name":"phone","pii_type":"PHONE"},{"column_name":"city","pii_type":"CITY"}]',
    "deleted_fields": '["address"]',
    "dataset_id": "test",
    "period": "P1D",
    "timestamp_column": "timestamp",
    "country_code": "US",
    "file_format": "JSON",
    "JOB_NAME": "test",
    "JOB_RUN_ID": "test",
    "solution_id": "test",
    "uuid": "test",
    "enable_anonymous_data": "true",
    "anonymous_data_logger": "test",
    "amc_instances": '["amc12345678"]',
    "user_id": "us-east-1_Z85CJEZK1",
    "update_strategy": "ADDITIVE"
}


@patch("awswrangler.s3.to_json")
def test_write_to_s3_json(mock_to_json):
    rw.write_to_s3(df="test", filepath="test", file_format="JSON")
    mock_to_json.assert_called()


@patch("awswrangler.s3.to_csv")
def test_write_to_s3_csv(mock_to_csv):
    rw.write_to_s3(df="test", filepath="test", file_format="CSV")
    mock_to_csv.assert_called()


def test_remove_deleted_fields():
    test_file = rw.DataFile(test_args)
    test_file.data = pd.DataFrame(
        data=[["test", "test"]], columns=["address", "city"]
    )

    test_file.remove_deleted_fields()
    assert "address" not in test_file.data


@patch("awswrangler.s3.read_csv")
def test_load_input_data(mock_read_csv):
    test_file = rw.DataFile(test_args)
    test_file.data = pd.DataFrame(data=[[1234]], columns=["phone"])
    test_file.source_bucket = "bucket"
    test_file.key = "key"
    test_file.file_format = "CSV"
    test_file.pii_fields = [{"column_name": "phone", "pii_type": "PHONE"}]

    test_file.load_input_data()
    mock_read_csv.assert_called_once_with(
        path=["s3://" + "bucket" + "/" + "key"],
        chunksize=2000,
        dtype={"phone": str},
    )


def test_timestamp_transform():
    test_file = rw.DataFile(test_args)
    test_file.data = pd.DataFrame(
        data=[["2020-04-01T20:50:00Z"]], columns=["timestamp"], dtype=str
    )

    test_file.timestamp_transform()
    assert pd.api.types.is_datetime64_any_dtype(test_file.data["timestamp"])

    test_file = rw.DataFile(test_args)
    test_file.data = pd.DataFrame(data=[["invalid"]], columns=["timestamp"])

    with pytest.raises(ValueError):
        test_file.timestamp_transform()


@patch("glue.library.read_write.write_to_s3")
def test_save_output(mock_write_to_s3):
    test_file = rw.DataFile(test_args)
    test_file.data = "test"
    test_file.file_format = "JSON"

    df = "test"
    filepath = (
        "s3://"
        + "test"
        + "/"
        + "amc"
        + "/"
        + "test"
        + "/"
        + "ADDITIVE"
        + "/US/dimension/"
        + "amc12345678|us-east-1_Z85CJEZK1"
        + "/"
        + "test"
        + ".gz"
    )
    test_file.save_output()
    mock_write_to_s3.assert_called_once_with(
        df=df, filepath=filepath, file_format=test_file.file_format
    )

def test_estimate_number_of_partitions():
    test_file = rw.DataFile(test_args)
    test_file.num_bytes = rw.GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES * 2
    test_file.estimate_compression_ratio = Mock(return_value=2)
    actual_number_of_partition = test_file.estimate_number_of_partitions()
    expected_number_of_partition = 3
    assert actual_number_of_partition == expected_number_of_partition


def test_estimate_number_of_partitions_with_error():
    test_file = rw.DataFile(test_args)
    test_file.num_bytes = rw.GZIPPED_OUTPUT_FILE_SIZE_IN_BYTES * 2
    test_file.estimate_compression_ratio = Mock(return_value=0)
    actual_number_of_partition = test_file.estimate_number_of_partitions()
    expected_number_of_partition = 2
    assert actual_number_of_partition == expected_number_of_partition


@patch("os.path.getsize")
@patch("pandas.Series.sum")
def test_estimate_compression_ratio(mock_memory_usage_sum, mock_getsize):
    df = pd.DataFrame({'A': range(10), 'B': range(10, 20)})
    test_file = rw.DataFile(test_args)
    test_file.data = df
    test_file.file_format = "JSON"
    mock_memory_usage_sum.return_value = 2000.0
    mock_getsize.return_value = 10
    assert test_file.estimate_compression_ratio() == 200
    assert not Path('tmp_sample_data.gz').exists()


def test_convert_timestamp_format():
    df = pd.DataFrame({'timestamp': range(10), 'B': range(10, 20)})
    test_file = rw.DataFile(test_args)
    test_file.data = df
    test_file.file_format = "JSON"
    with pytest.raises(AttributeError) as error:
        test_file.convert_timestamp_format(df)
    assert str(error.value) == "Can only use .dt accessor with datetimelike values"

@mock_aws
@patch("glue.library.read_write.write_to_s3")
def test_save_output(mock_write_to_s3):

    test_file = rw.DataFile(test_args)
    test_file.file_format = "JSON"
    test_file.timeseries_partition_size = "P1D"
    test_file.amc_instances = [
        "amc12345678",
        "amc12345679",
    ]
    test_file.user_id = "us-east-1_Z85CJEZK1"

    timestamp_1 = "2020-04-10T20:00:00Z"
    timestamp_2 = "2020-04-11T20:00:00Z"
    timestamp_3 = "2020-04-12T20:00:00Z"

    unique_timestamps = pd.DataFrame(
        data=[
            pd.to_datetime([timestamp_1]),
            pd.to_datetime([timestamp_2]),
            pd.to_datetime([timestamp_3]),
        ],
        columns=["timestamp"],
    )
    unique_timestamps = unique_timestamps.sort_values(by="timestamp")
    test_file.unique_timestamps = unique_timestamps

    test_file.data = pd.DataFrame(
        data=[
            [
                pd.to_datetime(timestamp_1),
                "test1",
                pd.to_datetime(timestamp_1),
            ],
            [
                pd.to_datetime(timestamp_1),
                "test2",
                pd.to_datetime(timestamp_1),
            ],
            [
                pd.to_datetime(timestamp_2),
                "test3",
                pd.to_datetime(timestamp_2),
            ],
            [
                pd.to_datetime(timestamp_3),
                "test3",
                pd.to_datetime(timestamp_3),
            ],
            [
                pd.to_datetime(timestamp_3),
                "test3",
                pd.to_datetime(timestamp_3),
            ],
        ],
        columns=["timestamp", "address", "timestamp_full_precision"],
    )

    expected_arguments = [
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/ADDITIVE/JSON/US/amc12345679|us-east-1_Z85CJEZK1/test-2020_04_12-00:00:00.gz",
            "file_format": "JSON",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/ADDITIVE/JSON/US/amc12345679|us-east-1_Z85CJEZK1/test-2020_04_11-00:00:00.gz",
            "file_format": "JSON",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/ADDITIVE/JSON/US/amc12345679|us-east-1_Z85CJEZK1/test-2020_04_10-00:00:00.gz",
            "file_format": "JSON",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/ADDITIVE/JSON/US/INVALID_amc12345679|us-east-1_Z85CJEZK1/test-2020_04_10-00:00:00.gz",
            "file_format": "JSON",
        },
    ]

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=test_args["output_bucket"])
        s3 = boto3.resource("s3", region_name="us-east-1")
        s3_object = s3.Object(
            test_args["output_bucket"],
            'amc/test/ADDITIVE/JSON/US/amc12345678|us-east-1_Z85CJEZK1/test-0.gz'
        )
        s3_object.put(Body="{}", ContentType="application/json")
        s3_object = s3.Object(
            test_args["output_bucket"],
            'amc/test/ADDITIVE/JSON/US/amc12345679|us-east-1_Z85CJEZK1/test-0.gz'
        )
        s3_object.put(Body="{}", ContentType="application/json")
        test_file.save_output()

    assert mock_write_to_s3.call_count == 2

    try:
        check = expected_arguments[0]
        mock_write_to_s3.assert_any_call(**check)
        check = expected_arguments[1]
        mock_write_to_s3.assert_any_call(**check)
        check = expected_arguments[2]
        mock_write_to_s3.assert_any_call(**check)
    except ValueError as e:
        print(e)
