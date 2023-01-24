import phonenumbers

class PhoneNormalizer():
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
            validityCheck = phonenumbers.is_possible_number(parsedNumber)
            if validityCheck:
                self.normalizedPhone = phonenumbers.format_number(
                    parsedNumber, phonenumbers.PhoneNumberFormat.E164
                    ).replace('+', "")
            else:
                self.normalizedPhone = ""
        finally:
            return self