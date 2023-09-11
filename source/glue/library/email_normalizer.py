# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import re


def is_valid_email(email):
    try:
        wrd_str = r"\w"
        re_str = f"([{wrd_str}._-]+@[{wrd_str}._-]+)"
        return bool(email and re.match(re_str, email))
    except Exception:
        return False


class EmailNormalizer:
    def normalize(self, record):
        self.normalized_record = record.lower()
        self.normalized_record = re.sub(
            r"[^\w.@-]+", "", self.normalized_record
        )

        if not is_valid_email(self.normalized_record):
            self.normalized_record = ""

        return self
