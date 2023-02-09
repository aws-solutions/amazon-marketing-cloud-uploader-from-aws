import re


def is_valid_email_address(email):
    try:
        wrd_str = r"\w"
        re_str = f"([{wrd_str}._-]+@[{wrd_str}._-]+)"
        return bool(email and re.match(re_str, email))
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
