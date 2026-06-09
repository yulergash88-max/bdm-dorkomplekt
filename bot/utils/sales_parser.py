import re
from dataclasses import dataclass

# Matches notifications like:
#   Тип: Савдо
#   Мижоз: Dorkomplektsnab Plus Mchj
#   ...
#   Sheben 20-40мм
#   Кол-во: 15 м3
_TYPE_SAVDO_RE = re.compile(r"Тип:\s*Савдо", re.IGNORECASE)
_CLIENT_RE = re.compile(r"Мижоз:\s*(.+)", re.IGNORECASE)
_QUANTITY_RE = re.compile(r"Кол-во:\s*([\d\s.,]+?)\s*м3", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedSale:
    product_name: str
    quantity_kub: float
    client_name: str | None


def parse_sale_message(text: str) -> ParsedSale | None:
    """Extracts product, quantity and client name from a "Савдо" sales-feed notification.

    Returns None if the text isn't a recognizable sale notification — the product name
    is taken from the plain-text line directly above the "Кол-во: ... м3" line, since
    that's the only line in the message without a "Label: value" shape.
    """
    if not _TYPE_SAVDO_RE.search(text):
        return None

    quantity_match = _QUANTITY_RE.search(text)
    if quantity_match is None:
        return None

    try:
        quantity = float(quantity_match.group(1).replace(" ", "").replace(",", "."))
    except ValueError:
        return None

    lines = [line.strip() for line in text.splitlines()]
    quantity_line_index = next(
        (i for i, line in enumerate(lines) if _QUANTITY_RE.search(line)), None
    )
    if quantity_line_index is None:
        return None

    product_name = next(
        (line for line in reversed(lines[:quantity_line_index]) if line and ":" not in line),
        None,
    )
    if not product_name:
        return None

    client_match = _CLIENT_RE.search(text)
    client_name = client_match.group(1).strip() if client_match else None

    return ParsedSale(product_name=product_name, quantity_kub=quantity, client_name=client_name)
