# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import phonenumbers


class PhoneNormalizer:
    def normalize(self, record):
        # Amazon Ads normalization spec requires that phone numbers begin with a country code.
        # Prepend a '+' to the number unless it already begins with '+'
        # because the phonenumbers library requires that leading plus sign
        # in order to correctly parse the country code.
        if record.startswith('+') is False:
            record = "+" + record

        try:
            parsed_number = phonenumbers.parse(record, None)
        except phonenumbers.phonenumberutil.NumberParseException:
            self.normalized_record = ""
        else:
            is_possible = phonenumbers.is_possible_number(parsed_number)
            if is_possible:
                # Amazon Ads spec expects the phone number in E.164 format
                # but without a leading plus sign.
                self.normalized_record = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                ).replace("+", "")
            else:
                self.normalized_record = ""
        return self
