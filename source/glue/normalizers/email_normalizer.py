import re


def isValidEmailAddress(email):
    try:
        return bool(email and re.match(r"([\w._-]+@[\w._-]+)", email))
    except Exception:
        return False


def normalizeEmail(email):
    if email:
        return re.sub(r"[^\w.@-]+", "", email.lower())
    return None


class EmailNormalizer:
    def __init__(self, email):
        self.email = email

    def normalize(self):
        email = normalizeEmail(self.email)
        if isValidEmailAddress(email):
            return email
        return ""
