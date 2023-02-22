import re


class DefaultNormalizer:
    def normalize(self, record):
        self.normalized_record = record.lower()

        # convert characters ß, ä, ö, ü, ø, æ
        self.normalized_record = self.normalized_record.replace("ß", "ss")
        self.normalized_record = self.normalized_record.replace("ä", "ae")
        self.normalized_record = self.normalized_record.replace("ö", "oe")
        self.normalized_record = self.normalized_record.replace("ü", "ue")
        self.normalized_record = self.normalized_record.replace("ø", "o")
        self.normalized_record = self.normalized_record.replace("æ", "ae")

        # remove all symbols and whitespace
        self.normalized_record = re.sub(
            r"[^a-z0-9]", "", self.normalized_record
        )

        return self
