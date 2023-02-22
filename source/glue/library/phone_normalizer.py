import phonenumbers

# phone number cannot start with certain digits for the indicated country
restrictedDigits = {"GB": ["4", "6"]}


def check_if_valid(number: int, country_code: str):
    if country_code in restrictedDigits:
        if str(number)[0] in restrictedDigits[country_code]:
            return False

    return True


class PhoneNormalizer:
    def __init__(self, country_code):
        # library takes 'GB' instead of 'UK' as country_code
        if country_code == "UK":
            self.country_code = "GB"
        else:
            self.country_code = country_code

    def normalize(self, record):
        record = record.replace("+", "")

        try:
            parsed_number = phonenumbers.parse(record, self.country_code)
        except phonenumbers.phonenumberutil.NumberParseException:
            self.normalized_record = ""
        else:
            is_possible = phonenumbers.is_possible_number(parsed_number)
            is_valid = check_if_valid(
                parsed_number.national_number, self.country_code
            )
            if is_possible and is_valid:
                self.normalized_record = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                ).replace("+", "")
            else:
                self.normalized_record = ""
        return self
