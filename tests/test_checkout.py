"""Unit tests for CheckoutService using the supplied FakePaymentGateway."""
from decimal import Decimal
from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway


class ExplodingGateway:
    """Simulates the gateway timing out / crashing."""
    def charge(self, amount, payment_token):
        raise TimeoutError('gateway unreachable')


def stock(repo, sku):
    return repo.get_product(sku).stock


def test_empty_cart_does_not_charge(repo, cart):
    gateway = FakePaymentGateway()
    result = CheckoutService(repo, gateway).checkout(cart, 'tok_test_1234', 'req-1')
    assert result.status == 'empty'
    assert gateway.calls == []


def test_successful_checkout_charges_discounted_total_and_takes_stock(repo, cart):
    cart.add_item('MOU-01', 2)
    cart.apply_discount('WELCOME10')
    gateway = FakePaymentGateway()
    result = CheckoutService(repo, gateway).checkout(cart, 'tok_test_1234', 'req-1')
    assert result.status == 'paid'
    assert gateway.calls == [(Decimal('53.91'), 'tok_test_1234')]
    assert stock(repo, 'MOU-01') == 18
    assert cart.lines == [] and cart.discount_code is None


def test_declined_payment_restores_stock_and_keeps_cart(repo, cart):
    cart.add_item('MOU-01', 2)
    result = CheckoutService(repo, FakePaymentGateway(should_approve=False)).checkout(
        cart, 'tok_test_1234', 'req-1')
    assert result.status == 'declined'
    assert stock(repo, 'MOU-01') == 20
    assert len(cart.lines) == 1


def test_gateway_exception_is_handled_and_stock_restored(repo, cart):
    cart.add_item('USB-01', 3)
    result = CheckoutService(repo, ExplodingGateway()).checkout(cart, 'tok_test_1234', 'req-1')
    assert result.status == 'payment_error'
    assert stock(repo, 'USB-01') == 50
    assert len(cart.lines) == 1


def test_repeated_request_id_charges_only_once(repo, cart):
    gateway = FakePaymentGateway()
    service = CheckoutService(repo, gateway)
    cart.add_item('USB-01', 1)
    first = service.checkout(cart, 'tok_test_1234', 'req-dup')
    retry_cart = ShoppingCart('student', repo)
    retry_cart.add_item('USB-01', 1)
    second = service.checkout(retry_cart, 'tok_test_1234', 'req-dup')
    assert second.order_id == first.order_id
    assert len(gateway.calls) == 1
    assert stock(repo, 'USB-01') == 49