import re

class ZipNormalizer():
    def __init__(self, countryCode):
        # CA ZIP, A1A1A1
        if countryCode == "CA":
            self.normalizeRegex = r'[^0-9A-Za-z]'
            self.zipLength = 6
            self.regex = re.compile(r'^([A-Za-z][0-9]){3}')
        # UK Zip, A11AA A111AA AA11AA AA111AA A1A1AA AA1A1AA
        elif countryCode == "UK":
            self.normalizeRegex = r'[^0-9A-Za-z]'
            self.zipLength = 7
            self.regex = re.compile(r'^(([A-Za-z]{1,2}[0-9]{2,3})|([A-Za-z]{1,2}[0-9][A-Za-z][0-9]))[A-Za-z]{2}')
        # IN ZIP, 6 digits
        elif countryCode == "IN":
            self.normalizeRegex = r'[^0-9]'
            self.zipLength = 6
            self.regex = re.compile(r'[0-9]{6}')
        # JP ZIP, 7 digits
        elif countryCode == "JP":
            self.normalizeRegex = r'[^0-9]'
            self.zipLength = 7
            self.regex = re.compile(r'[0-9]{7}')
        # ZIP, 5 digits
        else:
            self.normalizeRegex = r'[^0-9]'
            self.zipLength = 7
            self.regex = re.compile(r'[0-9]{7}')
    
    def normalize(self, record):
        self.normalizedZip = re.sub(self.normalizeRegex, '', record)

        if len(self.normalizedZip) > self.zipLength:
            self.normalizedZip = self.normalizedZip[:self.zipLength]
        
        if not re.match(self.regex, self.normalizedZip):
            self.normalizedZip = ""

        return self