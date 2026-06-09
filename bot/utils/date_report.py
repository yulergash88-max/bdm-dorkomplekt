"""Shared date-range report helpers used by both buyer and supplier handlers."""

from datetime import date, datetime, timedelta

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


def preset_to_range(preset: str) -> tuple[str, str] | None:
    """Returns (date_from_iso, date_to_iso) for a preset button label, or None."""
    from bot.keyboards.input_keyboards import DATE_LAST_MONTH, DATE_THIS_MONTH, DATE_TODAY, DATE_YESTERDAY
    today = date.today()
    if preset == DATE_TODAY:
        iso = today.isoformat()
        return iso, iso
    if preset == DATE_YESTERDAY:
        iso = (today - timedelta(days=1)).isoformat()
        return iso, iso
    if preset == DATE_THIS_MONTH:
        return today.replace(day=1).isoformat(), today.isoformat()
    if preset == DATE_LAST_MONTH:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev.isoformat(), last_prev.isoformat()
    return None
