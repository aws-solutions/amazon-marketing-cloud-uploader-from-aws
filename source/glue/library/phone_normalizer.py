# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import phonenumbers


class PhoneNormalizer:
    def __init__(self, country_code):
        # library takes 'GB' instead of 'UK' as country_code
        if country_code == "UK":
            self.country_code = "GB"
        else:
            self.country_code = country_code

    def normalize(self, record):
        record = record.replace("+", "")

        try:
            parsed_number = phonenumbers.parse(record, self.country_code)
        except phonenumbers.phonenumberutil.NumberParseException:
            self.normalized_record = ""
        else:
            is_possible = phonenumbers.is_possible_number(parsed_number)
            if is_possible:
                self.normalized_record = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                ).replace("+", "")
            else:
                self.normalized_record = ""
        return self
