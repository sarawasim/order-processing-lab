"""Models for the intentionally imperfect order-management application."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')


def to_money(value) -> Decimal:
    """Round a number to cents as a Decimal."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Product:
    sku: str
    name: str
    price: float
    stock: int


@dataclass
class CartLine:
    sku: str
    name: str
    unit_price: float
    quantity: int


@dataclass
class OrderResult:
    order_id: int | None
    status: str
    total: float
