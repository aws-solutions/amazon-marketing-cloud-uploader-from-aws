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
from unittest.mock import ANY, patch
from moto import mock_s3
import boto3

import pandas as pd
import pytest
from glue.library import read_write as rw
from glue.library import transform
from glue.library.address_normalizer import load_address_map_helper

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
    "period": "autodetect",
    "timestamp_column": "timestamp",
    "country_code": "US",
    "file_format": "JSON",
    "JOB_NAME": "test",
    "JOB_RUN_ID": "test",
    "solution_id": "test",
    "uuid": "test",
    "enable_anonymous_data": "true",
    "anonymous_data_logger": "test",
    "destination_endpoints": '["https://sample_endpoint.execute-api.us-east-1.amazonaws.com/prod"]',
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
    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[["test", "test"]], columns=["address", "city"]
    )

    test_file.remove_deleted_fields()
    assert "address" not in test_file.data


@patch("awswrangler.s3.read_csv")
def test_load_input_data(mock_read_csv):
    test_file = rw.FactDataset(test_args)
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
    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[["2020-04-01T20:50:00Z"]], columns=["timestamp"], dtype=str
    )

    test_file.timestamp_transform()
    assert pd.api.types.is_datetime64_any_dtype(test_file.data["timestamp"])

    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(data=[["invalid"]], columns=["timestamp"])

    with pytest.raises(ValueError):
        test_file.timestamp_transform()


def test_time_series_partitioning():
    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[
            pd.to_datetime(["2020-04-01T20:00:00Z"]),
            pd.to_datetime(["2020-04-01T20:01:00Z"]),
        ],
        columns=["timestamp"],
    )

    test_file.time_series_partitioning()
    assert test_file.timeseries_partition_size == "PT1M"

    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[
            pd.to_datetime(["2020-04-05T20:00:00Z"]),
            pd.to_datetime(["2020-04-05T21:00:00Z"]),
        ],
        columns=["timestamp"],
    )

    test_file.time_series_partitioning()
    assert test_file.timeseries_partition_size == "PT1H"

    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[
            pd.to_datetime(["2020-04-02T20:00:00Z"]),
            pd.to_datetime(["2020-04-03T20:00:00Z"]),
        ],
        columns=["timestamp"],
    )

    test_file.time_series_partitioning()
    assert test_file.timeseries_partition_size == "P1D"

    test_file = rw.FactDataset(test_args)
    test_file.data = pd.DataFrame(
        data=[
            pd.to_datetime(["2020-04-7T20:00:00Z"]),
            pd.to_datetime(["2020-04-14T20:00:00Z"]),
        ],
        columns=["timestamp"],
    )

    test_file.time_series_partitioning()
    assert test_file.timeseries_partition_size == "P7D"


@patch("glue.library.read_write.write_to_s3")
def test_save_dimension_output(mock_write_to_s3):
    test_file = rw.DimensionDataset(test_args)
    test_file.data = "test"
    test_file.file_format = "test"

    df = "test"
    filepath = (
        "s3://"
        + "test"
        + "/"
        + "amc"
        + "/"
        + "test"
        + "/US/dimension/"
        + "sample_endpoint.execute-api.us-east-1.amazonaws.com"
        + "/"
        + "test"
        + ".gz"
    )
    test_file.save_dimension_output()
    mock_write_to_s3.assert_called_once_with(
        df=df, filepath=filepath, file_format=test_file.file_format
    )


@patch("glue.library.read_write.write_to_s3")
def test_save_fact_output(mock_write_to_s3):
    test_file = rw.FactDataset(test_args)
    test_file.file_format = "test"
    test_file.timeseries_partition_size = "P1D"
    test_file.destination_endpoints = [
        "http://sample_endpoint1.execute-api.us-east-1.amazonaws.com/prod",
        "http://sample_endpoint2.execute-api.us-east-1.amazonaws.com/prod",
    ]

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
            "filepath": "s3://test/amc/test/US/P1D/sample_endpoint1.execute-api.us-east-1.amazonaws.com/test-2020_04_12-00:00:00.gz",
            "file_format": "test",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/US/P1D/sample_endpoint2.execute-api.us-east-1.amazonaws.com/test-2020_04_12-00:00:00.gz",
            "file_format": "test",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/US/P1D/sample_endpoint1.execute-api.us-east-1.amazonaws.com/test-2020_04_11-00:00:00.gz",
            "file_format": "test",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/US/P1D/sample_endpoint2.execute-api.us-east-1.amazonaws.com/test-2020_04_11-00:00:00.gz",
            "content_type": "test",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/US/P1D/sample_endpoint1.execute-api.us-east-1.amazonaws.com/test-2020_04_10-00:00:00.gz",
            "file_format": "test",
        },
        {
            "df": ANY,
            "filepath": "s3://test/amc/test/US/P1D/invalid_sample_endpoint2.execute-api.us-east-1.amazonaws.com/test-2020_04_10-00:00:00.gz",
            "file_format": "test",
        },
    ]

    test_file.save_fact_output()

    assert mock_write_to_s3.call_count == 6

    check = expected_arguments[0]
    mock_write_to_s3.assert_any_call(**check)
    check = expected_arguments[1]
    mock_write_to_s3.assert_any_call(**check)
    check = expected_arguments[2]
    mock_write_to_s3.assert_any_call(**check)
