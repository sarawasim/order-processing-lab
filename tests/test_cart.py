"""Unit tests for ShoppingCart."""
from decimal import Decimal
import pytest
from cart import CartError, ShoppingCart


def test_adding_same_product_twice_merges_into_one_line(cart):
    cart.add_item('USB-01', 2)
    cart.add_item('USB-01', 3)
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 5


def test_combined_quantity_cannot_exceed_stock(cart):
    cart.add_item('LAP-01', 5)
    with pytest.raises(CartError):
        cart.add_item('LAP-01', 1)
    assert cart.lines[0].quantity == 5

def test_subtotal_is_exact_to_the_cent(cart):
    cart.add_item('USB-01', 3)
    cart.add_item('MOU-01', 1)
    assert cart.subtotal() == Decimal('59.92')
    assert isinstance(cart.total(), Decimal)

@pytest.mark.parametrize('code, expected', [
    ('WELCOME10', Decimal('53.91')),
    ('STUDENT20', Decimal('47.92')),
    ('SAVE15', Decimal('44.90')),
    ('FREESHIP', Decimal('59.90')),
    ('  welcome10 ', Decimal('53.91')),
])
def test_discount_codes(cart, code, expected):
    cart.add_item('MOU-01', 2)
    cart.apply_discount(code)
    assert cart.total() == expected



def test_fixed_discount_never_goes_negative(cart):
    cart.add_item('USB-01', 1)  # 9.99 < 15
    cart.apply_discount('SAVE15')
    assert cart.total() == Decimal('0.00')


def test_total_updates_when_cart_changes_after_discount(cart):
    cart.add_item('MOU-01', 2)
    cart.apply_discount('WELCOME10')
    cart.add_item('MOU-01', 1)
    assert cart.total() == Decimal('80.87')


def test_save_and_load_round_trip(cart, repo):
    cart.add_item('USB-01', 2)
    cart.add_item('MOU-01', 1)
    cart.save()
    restored = ShoppingCart('student', repo)
    restored.load()
    assert {(l.sku, l.quantity) for l in restored.lines} == {('USB-01', 2), ('MOU-01', 1)}


def test_loading_twice_does_not_double_quantities(cart, repo):
    cart.add_item('USB-01', 2)
    cart.save()
    restored = ShoppingCart('student', repo)
    restored.load()
    restored.load()
    assert restored.lines[0].quantity == 2