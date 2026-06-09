"""Shared date-range report helpers used by both buyer and supplier handlers."""

from datetime import datetime

DATE_FORMAT = "%d.%m.%Y"
DATE_HINT = "кун.ой.йил форматида, масалан: 01.06.2026"


def parse_date(text: str) -> str | None:
    """Parses DD.MM.YYYY → ISO date string YYYY-MM-DD. Returns None on failure."""
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).strftime("%Y-%m-%d")
    except ValueError:
        return None


def fmt(iso: str) -> str:
    """Converts ISO date YYYY-MM-DD → DD.MM.YYYY for display."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime(DATE_FORMAT)
    except ValueError:
        return iso
