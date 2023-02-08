import phonenumbers

# phone number cannot start with certain digits for the indicated country
restrictedDigits = {"GB": ["4", "6"]}


def check_if_valid(number: int, countryCode: str):
    if countryCode in restrictedDigits:
        if str(number)[0] in restrictedDigits[countryCode]:
            return False

    return True


class PhoneNormalizer:
    def __init__(self, countryCode):
        # library takes 'GB' instead of 'UK' as countryCode
        if countryCode == "UK":
            self.countryCode = "GB"
        else:
            self.countryCode = countryCode

    def normalize(self, record):
        record = record.replace("+", "")

        try:
            parsedNumber = phonenumbers.parse(record, self.countryCode)
        except phonenumbers.phonenumberutil.NumberParseException:
            self.normalizedPhone = ""
        else:
            isPossible = phonenumbers.is_possible_number(parsedNumber)
            isValid = check_if_valid(
                parsedNumber.national_number, self.countryCode
            )
            if isPossible and isValid:
                self.normalizedPhone = phonenumbers.format_number(
                    parsedNumber, phonenumbers.PhoneNumberFormat.E164
                ).replace("+", "")
            else:
                self.normalizedPhone = ""
        return self
