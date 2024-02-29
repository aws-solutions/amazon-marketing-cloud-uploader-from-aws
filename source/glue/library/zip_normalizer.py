# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import re


class ZipNormalizer:
    def __init__(self, country_code):
        # CA ZIP, A1A1A1
        if country_code == "CA":
            self.normalize_regex = r"[^0-9A-Za-z]"
            self.zip_length = 6
            self.regex = re.compile(r"^([A-Za-z]\d){3}$")
        # UK Zip, A11AA A111AA AA11AA AA111AA | A1A1AA AA1A1AA
        elif country_code == "GB":
            self.normalize_regex = r"[^0-9A-Za-z]"
            self.zip_length = 7
            self.regex = re.compile(
                r"^(([A-Za-z]{1,2}\d{2,3})|([A-Za-z]{1,2}\d[A-Za-z]\d))[A-Za-z]{2}$"
            )
        # IN ZIP, 6 digits
        elif country_code == "IN":
            self.normalize_regex = r"[^\d]"
            self.zip_length = 6
            self.regex = re.compile(r"\d{6}")
        # JP ZIP, 7 digits
        elif country_code == "JP":
            self.normalize_regex = r"[^0-9]"
            self.zip_length = 7
            self.regex = re.compile(r"\d{7}")
        # ZIP, 5 digits
        else:
            self.normalize_regex = r"[^0-9]"
            self.zip_length = 5
            self.regex = re.compile(r"\d{5}")

    def normalize(self, record):
        self.normalized_record = re.sub(self.normalize_regex, "", record)

        if len(self.normalized_record) > self.zip_length:
            self.normalized_record = self.normalized_record[: self.zip_length]

        if not re.match(self.regex, self.normalized_record):
            self.normalized_record = ""

        return self
