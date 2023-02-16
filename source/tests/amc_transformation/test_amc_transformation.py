# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import pytest


@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["AMC_ENDPOINT_URL"] = "AmcEndpointUrl"
    os.environ["AMC_API_ROLE_ARN"] = "AmcApiRoleArn"
    os.environ["botoConfig"] = '{"region_name": "us-east-1"}'

def test_load_address_map_helper():
    from glue.normalizers.address_normalizer import load_address_map_helper

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
import shutil

import pandas as pd

from glue.normalizers import transform


def _match_data(test: pd.DataFrame, check: pd.DataFrame, pii_fields: list):
    df_concat = pd.merge(
        test, 
        check, 
        how = 'inner', 
        on = 'id', 
        suffixes = ["_test", "_check"]
        )

    cols=['id', 'field', 'test', 'check']
    lst = []
    for field in pii_fields:
        column_name = field['column_name']
        for index, row in df_concat.iterrows():
            test_val = row[f'{column_name}_test']
            check_val = row[f'{column_name}_check']

            if test_val != check_val:
                lst.append([row['id'], column_name, test_val, check_val])
                
    invalid = pd.DataFrame(data=lst, columns=cols)
    return invalid

def _return_results(invalid: pd.DataFrame, raw: pd.DataFrame):
    df_concat = pd.merge(
        invalid,
        raw,
        how = 'left',
        on = 'id',
    )

    cols=['id', 'field', 'raw', 'test', 'check']
    lst = []
    for index, row in df_concat.iterrows():
        invalid_field = (row.loc['field'])
        lst.append(
            [row.loc['id'], 
            invalid_field,
            row.loc[invalid_field],
            row.loc['test'], 
            row.loc['check']]
            )

    results = pd.DataFrame(data=lst, columns=cols)
    return results

class AMCTransformationTest:
    def __init__(self, country):
        self.country = country.lower()
        self.pii_fields = [
            {
                'pii_type': 'NAME',
                'column_name': 'first_name'
            },
            {
                'pii_type': 'NAME',
                'column_name': 'last_name'
            },
            {
                'pii_type': 'EMAIL',
                'column_name': 'email'
            },
            {
                'pii_type': 'ADDRESS',
                'column_name': 'address'
            },
            {
                'pii_type': 'PHONE',
                'column_name': 'phone'
            },
            {
                'pii_type': 'CITY',
                'column_name': 'city'
            },
            {
                'pii_type': 'ZIP',
                'column_name': 'zip'
            }
        ]
        if self.country == "us":
            self.pii_fields.append({'pii_type': 'STATE', 'column_name': 'state'})

    # Test amc_transformations normalization & hashing
    def _normalization_matching(self):
        country = self.country

        raw = pd.read_json(f'tests/amc_transformation/sample_data/test_{country}/{country}_raw.json')
        check = pd.read_json(f'tests/amc_transformation/sample_data/test_{country}/{country}_check.json')

        normalized = transform.transform_data(df=raw.copy(), pii_fields=self.pii_fields, country_code=country.upper())
        hashed = transform.hash_data(df=normalized, pii_fields=self.pii_fields)

        invalid = _match_data(test=hashed, check=check, pii_fields=self.pii_fields)
        results = _return_results(invalid=invalid, raw=raw.copy())

        self.results = results

    # Export results locally
    def _export_results(self):
        country = self.country
        results = self.results

        if len(results) > 0:
            if not os.path.exists('tests/amc_transformation/test_results'):
                os.mkdir('tests/amc_transformation/test_results')
            if not os.path.exists(f'tests/amc_transformation/test_results/{country}'):
                os.mkdir(f'tests/amc_transformation/test_results/{country}')
            results.to_csv(f'tests/amc_transformation/test_results/{country}/results.csv')
            results.to_json(f'tests/amc_transformation/test_results/{country}/results.json', orient='records')
            
            print(f'Invalid results for {country}:')
            print(results.groupby(['field'])['id'].count())
            print('')

        else:
            print(f'Nothing to export for country: {country}. All tests passed!')

    # Delete previously exported results
    def _clean_test_artifacts(self):
        if os.path.exists('tests/amc_transformation/test_results'):
            shutil.rmtree('tests/amc_transformation/test_results')

def test_amc_transformations(countries=["us", "uk"]):
    for item in countries:
        test = AMCTransformationTest(country=item)
        test._normalization_matching()

        assert len(test.results) < 10, item
