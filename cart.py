"""Business logic. Several design and correctness issues are intentional."""
from decimal import Decimal

from models import CartLine, to_money

class CartError(ValueError):
    """Raised when a cart operation is invalid (bad quantity, unknown SKU, no stock)."""


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise CartError(f'Quantity must be a positive whole number, got {quantity!r}')

PERCENT_DISCOUNTS = {'WELCOME10': Decimal('0.90'), 'STUDENT20': Decimal('0.80')}
FIXED_DISCOUNTS = {'SAVE15': Decimal('15.00')}
NO_EFFECT_CODES = {'FREESHIP'}
VALID_CODES = set(PERCENT_DISCOUNTS) | set(FIXED_DISCOUNTS) | NO_EFFECT_CODES


class ShoppingCart:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.repository = repository
        self.lines = []
        self.discount_code = None

    def _find(self, sku):
        return next((line for line in self.lines if line.sku == sku), None)

    def add_item(self, sku, quantity):
        _validate_quantity(quantity)
        product = self.repository.get_product(sku)
        if product is None:
            raise CartError(f'Unknown product {sku!r}')
        existing = self._find(sku)
        already_in_cart = existing.quantity if existing else 0
        if already_in_cart + quantity > product.stock:
            raise CartError(f'Only {product.stock} of {sku} in stock')
        if existing:
            existing.quantity += quantity
        else:
            self.lines.append(CartLine(sku, product.name, product.price, quantity))
        return True

    def remove_item(self, sku, quantity=None):
        if quantity is not None:
            _validate_quantity(quantity)
        line = self._find(sku)
        if line is None:
            raise CartError(f'{sku!r} is not in the cart')
        if quantity is None or quantity >= line.quantity:
            self.lines.remove(line)
        else:
            line.quantity -= quantity
        return True

    def subtotal(self) -> Decimal:
        return to_money(sum((line.unit_price * line.quantity for line in self.lines), Decimal('0')))

    def discount_amount(self) -> Decimal:
        subtotal = self.subtotal()
        code = self.discount_code
        if code in PERCENT_DISCOUNTS:
            return subtotal - to_money(subtotal * PERCENT_DISCOUNTS[code])
        if code in FIXED_DISCOUNTS:
            return min(FIXED_DISCOUNTS[code], subtotal)
        return Decimal('0.00')

    def total(self) -> Decimal:
        return to_money(self.subtotal() - self.discount_amount())

    def apply_discount(self, code):
        normalized = (code or '').strip().upper()
        if normalized not in VALID_CODES:
            raise CartError(f'Invalid coupon {code!r}')
        self.discount_code = normalized
        return True

    def clear(self):
        self.lines.clear()
        self.discount_code = None

    def load(self):
        self.lines = []
        for sku, quantity in self.repository.get_saved_cart(self.user_id):
            try:
                self.add_item(sku, quantity)
            except CartError:
                continue

    def save(self):
        self.repository.save_cart(self.user_id, self.lines)
