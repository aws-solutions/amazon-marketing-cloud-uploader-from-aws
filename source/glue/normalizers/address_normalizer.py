# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
###############################################################################
#
# PURPOSE:
#   Normalize addresses according to the normalization standard used by Amazon
#   Ads for privacy enhanced identity resolution and data collaboration.
#
# USAGE:
#   1. Import AddressNormalizer
#   2. Instantiate AddressNormalizer with a country code, like this:
#      addressNormalizer = AddressNormalizer('FR')
#   3. Normalize text, like this:
#      addressNormalizer.normalize(text).normalized_address
#
# REFERENCE:
#   https://github.com/amzn/amazon-ads-advertiser-audience-normalization-sdk-py
#
###############################################################################
import hashlib
import json
import os
import re
import tempfile
from re import finditer
from zipfile import ZipFile


def load_address_map_helper():
    try:
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        with open(
            os.path.join(__location__, "address_map_helper.json"),
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except Exception:
        # Glue job put files in zip
        with ZipFile("normalizers.zip", "r") as zipFile:
            with tempfile.TemporaryDirectory() as tempdir:
                zipFile.extractall(path=tempdir)
                print(os.listdir(tempdir))
                with open(
                    os.path.join(
                        f"{tempdir}/normalizers/address_map_helper.json"
                    ),
                    "r",
                    encoding="utf-8",
                ) as file:
                    return json.load(file)


address_map = load_address_map_helper()

NumberIndicators = address_map["NumberIndicators"]

DirectionalWords = address_map["DirectionalWords"]

DefaultStreetSuffixes = address_map["DefaultStreetSuffixes"]

USStreetSuffixes = address_map["USStreetSuffixes"]

USSubBuildingDesignator = address_map["USSubBuildingDesignator"]

ITStreetPrefixes = address_map["ITStreetPrefixes"]

FRStreetDesignator = address_map["FRStreetDesignator"]

ESStreetPrefixes = address_map["ESStreetPrefixes"]

UKOrganizationSuffixes = address_map["UKOrganizationSuffixes"]

UKStreetSuffixes = address_map["UKStreetSuffixes"]
UKSubBuildingDesignator = address_map["UKSubBuildingDesignator"]

DASH_STRING = "-"

POUND_REGEX = "([A-Z]*)#([0-9A-Z-/]*)"
POUND_STRING = "#"

DELIMITER_PATTERN_MAP = {
    "COMMA": "(\\s?,\\s?)+",
    "CO": "\\bC/O\\b",
    "EXCLAMATION_MARK": "!",
    "OPEN_BRACKET": "[\\[\\{\\(]",
    "CLOSE_BRACKET": "[\\]\\}\\)]",
    "SPACE": "\\s+",
}


class Delimiter:
    def __init__(self, text="", start=0, del_type=None) -> None:
        self.text = text
        self.start = start
        self.end = start + len(text)
        self.del_type = del_type

    def parse(self, text, start=None):
        if start is None:
            start = 0
        delimiters = []
        a = list(DELIMITER_PATTERN_MAP.keys())
        for i in range(0, len(a)):
            delimiter_type = a[i]
            new_found_delimiters = self.find_delimiters(
                text, start, delimiters, delimiter_type
            )
            delimiters.extend(new_found_delimiters)
            delimiters.sort(key=lambda x: x.start, reverse=False)
        return delimiters

    def find_delimiters(self, text, start, delimiters, del_type):
        result = []
        text_start = start
        delimiters_1 = delimiters

        for i in range(0, len(delimiters_1)):
            cur_delimiter = delimiters_1[i]
            text_end = cur_delimiter.start
            if text_end == text_start:
                text_start = cur_delimiter.end
                continue
            search_string = text[text_start - start : text_end - start]
            regexp = re.compile(DELIMITER_PATTERN_MAP[del_type], re.IGNORECASE)
            match_result = 0
            for match_result in finditer(regexp, search_string):
                delimiter = Delimiter(
                    match_result.group(),
                    text_start + match_result.span()[0],
                    del_type,
                )
                result.append(delimiter)
            text_start = cur_delimiter.end

        if text_start < start + len(text):
            search_string = text[text_start - start :]
            regexp = re.compile(DELIMITER_PATTERN_MAP[del_type], re.IGNORECASE)
            match_result = 0
            for match_result in finditer(regexp, search_string):
                index = match_result.span()[0]
                delimiter_string = match_result.group()
                delimiter = Delimiter(
                    delimiter_string, text_start + index, del_type
                )
                result.append(delimiter)
        return result


class NormalizedAddress:
    def __init__(self, full_address):
        self.address_tokens = []
        self.full_address = full_address

    def generate_tokens(self):
        delimiters = Delimiter().parse(text=self.full_address)
        tokens = []
        start = 0
        address = self.full_address
        text_start = start

        delimiters_1 = delimiters

        for i in range(0, len(delimiters_1)):
            delimiter = delimiters_1[i]
            text_end = delimiter.start
            if text_end != text_start:
                address_token = address[text_start - start : text_end - start]
                tokens.append(address_token)
            text_start = delimiter.end
        if text_start < start + len(address):
            address_token = address[text_start - start :]
            tokens.append(address_token)

        self.address_token = tokens

    def update_address_tokens(self, index, **kwargs):
        rest = []

        for _, value in kwargs.items():
            rest.append(value)

        self.address_tokens.pop(index)
        for i in range(0, len(rest)):
            self.address_tokens.insert(index + i, rest[i])


class Dash:
    def apply(self, normalized_address):
        for i in range(0, len(normalized_address.address_tokens)):
            word = normalized_address.address_tokens[i]
            index = word.rfind(DASH_STRING)
            if index > 0 and index < len(word) - 1:
                first_part = word[0:index]
                second_part = word[index + 1 :]
                if not second_part.isnumeric() and first_part.isnumeric():
                    normalized_address.update_address_tokens(
                        i, 1, first_part=first_part, second_part=second_part
                    )


class Pound:
    def apply(self, normalized_address):
        for i in range(0, len(normalized_address.address_tokens)):
            word = normalized_address.address_tokens[i]
            regexp = re.compile(POUND_REGEX)
            match_result = 0
            for match_result in finditer(regexp, word):
                first_part = match_result.group(1)
                second_part = match_result.group(2)

                if first_part == "" and second_part == "":
                    continue

                if first_part == "":
                    normalized_address.update_address_tokens(
                        i,
                        1,
                        pound_string=POUND_STRING,
                        second_part=second_part,
                    )
                    i += 1
                elif second_part == "":
                    normalized_address.update_address_tokens(
                        i, 1, first_part=first_part, pound_string=POUND_STRING
                    )
                    i += 1
                else:
                    normalized_address.update_address_tokens(
                        i,
                        1,
                        first_part=first_part,
                        pound_string=POUND_STRING,
                        second_part=second_part,
                    )
                    i += 2


pre_proccess_rules = [Dash(), Pound()]


class AddressNormalizer:
    def __init__(self, country_code):
        self.street_word_maps = []
        self.street_word_maps.extend(NumberIndicators)
        self.street_word_maps.extend(DirectionalWords)
        self.normalized_address = None
        self.sha256normalized_address = None

        if country_code == "US":
            self.street_word_maps.extend(USStreetSuffixes)
            self.street_word_maps.extend(USSubBuildingDesignator)

        elif country_code == "CA":
            self.street_word_maps.extend(DefaultStreetSuffixes)

        elif country_code == "UK":
            self.street_word_maps.extend(UKOrganizationSuffixes)
            self.street_word_maps.extend(UKStreetSuffixes)
            self.street_word_maps.extend(UKSubBuildingDesignator)

        elif country_code == "FR":
            self.street_word_maps.extend(FRStreetDesignator)
            self.street_word_maps.extend(DefaultStreetSuffixes)

        elif country_code == "DE":
            self.street_word_maps.extend(DefaultStreetSuffixes)

        elif country_code == "ES":
            self.street_word_maps.extend(DefaultStreetSuffixes)
            self.street_word_maps.extend(ESStreetPrefixes)

        elif country_code == "IT":
            self.street_word_maps.extend(DefaultStreetSuffixes)
            self.street_word_maps.extend(ITStreetPrefixes)

        elif country_code == "JP":
            self.street_word_maps.extend(DefaultStreetSuffixes)

        elif country_code == "IN":
            self.street_word_maps.extend(DefaultStreetSuffixes)

        else:
            raise ValueError("The country code provided is not yet supported")

        self.pre_proccess_rules = pre_proccess_rules

    def normalize(self, record):
        record = record.strip().upper()

        normalized_address = NormalizedAddress(record)
        normalized_address.generate_tokens()

        a = self.pre_proccess_rules
        for i in range(0, len(a)):
            rule = a[i]
            rule.apply(normalized_address)

        for i in range(0, len(normalized_address.address_tokens)):
            word = normalized_address.address_tokens[i]
            for j in range(0, len(self.street_word_maps)):
                if word in self.street_word_maps[j]:
                    normalized_address.update_address_tokens(
                        i, 1, first_part=self.street_word_maps[j].get(word)
                    )

        self.normalized_address = "".join(
            normalized_address.address_tokens
        ).lower()
        self.sha256normalized_address = hashlib.sha256(
            self.normalized_address.encode()
        ).hexdigest()
        return self
