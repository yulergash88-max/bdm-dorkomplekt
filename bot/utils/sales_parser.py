import re
from dataclasses import dataclass

_TYPE_SAVDO_RE = re.compile(r"Тип:\s*Савдо", re.IGNORECASE)
_CLIENT_RE = re.compile(r"Мижоз:\s*(.+)", re.IGNORECASE)
_QUANTITY_RE = re.compile(r"Кол-во:\s*([\d\s.,]+?)\s*м3", re.IGNORECASE)
_CAR_RE = re.compile(r"(?:Машина[а-яёА-ЯЁ]*|Транспорт):\s*(.+)", re.IGNORECASE)
_DATETIME_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})")


@dataclass(frozen=True)
class ParsedSale:
    product_name: str
    quantity_kub: float
    client_name: str | None
    car_number: str | None
    sale_datetime: str | None


def parse_sale_message(text: str) -> ParsedSale | None:
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

    car_match = _CAR_RE.search(text)
    car_number = car_match.group(1).strip() if car_match else None

    dt_match = _DATETIME_RE.search(text)
    sale_datetime = dt_match.group(1).strip() if dt_match else None

    return ParsedSale(product_name=product_name, quantity_kub=quantity, client_name=client_name, car_number=car_number, sale_datetime=sale_datetime)
