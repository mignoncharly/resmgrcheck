"""Last-mile log redaction, including exception text and attacker-chosen URL paths."""
import logging,re

ACCESS=re.compile(r'(?<![A-Za-z0-9_-])rmc_[0-9a-f]{32}_[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])')
PROVIDER=re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}')

class PrivateFormatter(logging.Formatter):
    def format(self,record):
        value=super().format(record)
        return PROVIDER.sub('[REDACTED_PROVIDER_KEY]',ACCESS.sub('[REDACTED_ACCESS_CODE]',value))
