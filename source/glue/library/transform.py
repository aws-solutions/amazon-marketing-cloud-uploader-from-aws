import hashlib

import pandas as pd
import regex as re
from library.normalizers.address_normalizer import AddressNormalizer
from library.normalizers.default_normalizer import DefaultNormalizer
from library.normalizers.email_normalizer import EmailNormalizer
from library.normalizers.phone_normalizer import PhoneNormalizer
from library.normalizers.state_normalizer import StateNormalizer
from library.normalizers.zip_normalizer import ZipNormalizer

###############################
# HELPER FUNCTIONS
###############################


# Use this function to flag records that are null or already hashed
# These records will skip normalization/hashing
def skip_record_flag(text):
    # This regex expression matches a sha256 hash value.
    # Sha256 hash codes are 64 consecutive hexadecimal digits, a-f and 0-9.
    sha256_pattern = "^[a-f0-9]{64}$"
    if pd.isnull(text) or re.match(sha256_pattern, text):
        return True


class NormalizationPatterns:
    def __init__(self, field, country_code):
        field_map = {
            "ADDRESS": AddressNormalizer(country_code),
            "STATE": StateNormalizer(country_code),
            "ZIP": ZipNormalizer(country_code),
            "PHONE": PhoneNormalizer(country_code),
            "EMAIL": EmailNormalizer(),
        }
        self.normalizer = field_map.get(field, DefaultNormalizer())

    def text_transformations(self, text):
        text = self.normalizer.normalize(text).normalized_record
        return text


###############################
# DATA NORMALIZATION
###############################


def transform_data(data: pd.DataFrame, pii_fields: dict, country_code: str) -> pd.DataFrame:
    for field in pii_fields:
        column_name = field["column_name"]
        pii_type = field["pii_type"]
        field_normalizer = NormalizationPatterns(
            field=pii_type, country_code=country_code
        )
        data[column_name] = (
            data[column_name]
            .copy()
            .apply(
                lambda x, field_normalizer=field_normalizer: x
                if skip_record_flag(x)
                else field_normalizer.text_transformations(text=x)
            )
        )
    return data


###############################
# PII HASHING
###############################


def hash_data(data: pd.DataFrame, pii_fields: dict) -> pd.DataFrame:
    for field in pii_fields:
        column_name = field["column_name"]
        data[column_name] = (
            data[column_name]
            .copy()
            .apply(
                lambda x: x
                if skip_record_flag(x)
                else hashlib.sha256(x.encode()).hexdigest()
            )
        )
    return data
