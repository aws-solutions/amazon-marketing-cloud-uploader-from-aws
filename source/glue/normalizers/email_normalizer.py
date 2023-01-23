import re


def isValidEmailAddress(email):
    try:
        return bool(email and re.match("([\w._-]+@[\w._-]+)", email))
    except Exception:
        return False

class EmailNormalizer():
    def __init__(self, email):
        self.email = email

    def normalize(self):
        if isValidEmailAddress(self.email):
            return self.email
        return ""