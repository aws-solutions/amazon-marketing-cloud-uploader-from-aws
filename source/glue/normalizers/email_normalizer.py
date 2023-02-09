import re


def is_valid_email_address(email):
    try:
        return bool(email and re.match(r"([\w._-]+@[\w._-]+)", email))
    except Exception:
        return False


def normalize_email(email):
    if email:
        return re.sub(r"[^\w.@-]+", "", email.lower())
    return None


class EmailNormalizer:
    def __init__(self, email):
        self.email = email

    def normalize(self):
        email = normalize_email(self.email)
        if is_valid_email_address(email):
            return email
        return ""
