import re

def is_valid_email(email):
    try:
        return bool(email and re.match("([\w._-]+@[\w._-]+)", email))
    except Exception:
        return False

class EmailNormalizer():

    def normalize(self, record):
        self.normalizedEmail = record.lower()
        self.normalizedEmail = re.sub("[^\w.@-]+", "", self.normalizedEmail)

        if not is_valid_email(self.normalizedEmail):
            self.normalizedEmail = ""

        return self