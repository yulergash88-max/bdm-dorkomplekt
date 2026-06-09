import re


def normalize_phone(phone: str) -> str:
    """Returns the last 9 digits — country-code/leading-zero agnostic match key."""
    return re.sub(r"\D", "", phone)[-9:]
