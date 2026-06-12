import re
from dataclasses import dataclass

_TYPE_SAVDO_RE = re.compile(r"Тип:\s*Савдо", re.IGNORECASE)
_TYPE_TOLOV_RE = re.compile(r"Тип:\s*Т[ўу]лов", re.IGNORECASE)
_CLIENT_RE = re.compile(r"Мижоз:\s*(.+)", re.IGNORECASE)
_QUANTITY_RE = re.compile(r"Кол-во:\s*([\d\s.,]+?)\s*м3", re.IGNORECASE)
_CAR_RE = re.compile(r"(?:Машина[а-яёА-ЯЁ]*|Транспорт):\s*(.+)", re.IGNORECASE)
_DATETIME_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}:\d{2})")

# Money fields. The capture class deliberately excludes newlines (only digits, spaces,
# nbsp, dot, comma, minus) so a number never swallows the following line.
_NUM = "([0-9  .,\\-]+)"
_PRICE_RE = re.compile(r"Цена:\s*" + _NUM, re.IGNORECASE)
# `^Сумма` (line start) so it does NOT match "Даставка сумма:" or "Жами сумма:".
_AMOUNT_RE = re.compile(r"^[ \t]*Сумма:\s*" + _NUM, re.IGNORECASE | re.MULTILINE)
_PAID_RE = re.compile(r"Туланди:\s*" + _NUM, re.IGNORECASE)
# Payment ("Тип: Тўлов") — money received from the client.
_RECEIVED_RE = re.compile(r"Пул\s+олинди\s*:\s*" + _NUM, re.IGNORECASE)


@dataclass(frozen=True)
class ParsedSale:
    """A "Тип: Савдо" message — goods sold to a client."""
    product_name: str
    quantity_kub: float
    client_name: str | None
    car_number: str | None
    sale_datetime: str | None
    price: float | None = None
    amount: float | None = None   # "Сумма" — value of goods sold
    paid: float | None = None     # "Туланди" — paid at point of sale (info only)


@dataclass(frozen=True)
class ParsedPayment:
    """A "Тип: Тўлов" message — money received from a client."""
    client_name: str | None
    amount: float            # "Пул олинди" — money received
    sale_datetime: str | None


def _parse_number(raw: str | None) -> float | None:
    """'56 666,67' -> 56666.67, '425 000' -> 425000.0, '-50 000' -> -50000.0."""
    if raw is None:
        return None
    cleaned = raw.strip().replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _search_number(pattern: re.Pattern, text: str) -> float | None:
    match = pattern.search(text)
    return _parse_number(match.group(1)) if match else None


def _client_name(text: str) -> str | None:
    match = _CLIENT_RE.search(text)
    return match.group(1).strip() if match else None


def _sale_datetime(text: str) -> str | None:
    match = _DATETIME_RE.search(text)
    return match.group(1).strip() if match else None


def parse_payment_message(text: str) -> ParsedPayment | None:
    if not _TYPE_TOLOV_RE.search(text):
        return None
    amount = _search_number(_RECEIVED_RE, text)
    if amount is None:
        return None
    return ParsedPayment(
        client_name=_client_name(text),
        amount=amount,
        sale_datetime=_sale_datetime(text),
    )


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

    car_match = _CAR_RE.search(text)
    car_number = car_match.group(1).strip() if car_match else None

    return ParsedSale(
        product_name=product_name,
        quantity_kub=quantity,
        client_name=_client_name(text),
        car_number=car_number,
        sale_datetime=_sale_datetime(text),
        price=_search_number(_PRICE_RE, text),
        amount=_search_number(_AMOUNT_RE, text),
        paid=_search_number(_PAID_RE, text),
    )


def parse_group_message(text: str) -> ParsedSale | ParsedPayment | None:
    """Dispatch a group message to the right parser based on its "Тип" line."""
    payment = parse_payment_message(text)
    if payment is not None:
        return payment
    return parse_sale_message(text)
