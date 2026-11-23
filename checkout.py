"""Checkout coordinator."""
import logging

from models import OrderResult, to_money
from repository import OutOfStockError

logger = logging.getLogger(__name__)


def mask_token(token):
    """Show only the last 4 characters of a payment token in logs."""
    return '****' + token[-4:] if len(token) > 4 else '****'


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        if not request_id:
            raise ValueError('request_id is required so a retried checkout cannot charge twice')
        if not payment_token:
            raise ValueError('payment_token is required')

        existing = self.repository.find_order_by_request(request_id)
        if existing is not None:
            order_id, _user, amount, status = existing
            return OrderResult(order_id, status, to_money(amount))

        if not cart.lines:
            return OrderResult(None, 'empty', to_money(0))

        amount = cart.total()

        try:
            order_id = self.repository.reserve_order(cart.user_id, amount, request_id, cart.lines)
        except OutOfStockError:
            return OrderResult(None, 'out_of_stock', amount)

        logger.info('Charging %s to token %s', amount, mask_token(payment_token))
        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response.get('approved') else 'declined'
        except Exception:
            logger.exception('Payment gateway error for order %s', order_id)
            status = 'payment_error'

        if status == 'paid':
            self.repository.mark_paid(order_id)
            cart.clear()
            cart.save()
        else:
            self.repository.fail_order(order_id, status)

        return OrderResult(order_id, status, amount)