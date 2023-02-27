import re


class CityNormalizer:
    def normalize(self, record):
        self.normalized_record = record.lower()
        self.normalized_record = re.sub(r'[^a-zA-Z0-9]+', "", self.normalized_record)

        return self