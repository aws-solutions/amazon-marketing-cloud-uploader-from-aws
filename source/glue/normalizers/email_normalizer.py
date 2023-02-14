import re

def is_valid_email(email):
    try:
        wrd_str = r"\w"
        re_str = f"([{wrd_str}._-]+@[{wrd_str}._-]+)"
        return bool(email and re.match(re_str, email))
    except Exception:
        return False

class EmailNormalizer():

    def normalize(self, record):
        self.normalized_email = record.lower()
        self.normalized_email = re.sub("[^\w.@-]+", "", self.normalized_email)

        if not is_valid_email(self.normalized_email):
            self.normalized_email = ""

        return self
