"""SQLite persistence. Contains deliberate reliability/security problems."""
import sqlite3
from contextlib import closing, contextmanager

from models import Product, to_money

class OutOfStockError(Exception):
    """Raised when there isn't enough stock to reserve an order."""


class StoreRepository:
    def __init__(self, db_path='shop.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    @contextmanager
    def _transaction(self):
        with closing(self.connect()) as conn:
            with conn:
                yield conn

    def get_product(self, sku):
        with self._transaction() as conn:
            row = conn.execute(
                'SELECT sku, name, price, stock FROM products WHERE sku = ?', (sku,)
            ).fetchone()
        if row is None:
            return None
        sku, name, price, stock = row
        return Product(sku, name, to_money(price), stock)

    def get_saved_cart(self, user_id):
        with self._transaction() as conn:
            return conn.execute(
                'SELECT sku, quantity FROM saved_cart WHERE user_id = ?', (user_id,)
            ).fetchall()

    def save_cart(self, user_id, lines):
        with self._transaction() as conn:
            conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
            conn.executemany(
                'INSERT INTO saved_cart (user_id, sku, quantity) VALUES (?, ?, ?)',
                [(user_id, line.sku, line.quantity) for line in lines],
            )

    def find_order_by_request(self, request_id):
        with self._transaction() as conn:
            return conn.execute(
                'SELECT id, user_id, amount, status FROM orders WHERE request_id = ?',
                (request_id,),
            ).fetchone()

    def reserve_order(self, user_id, amount, request_id, lines):
        with self._transaction() as conn:
            for line in lines:
                cur = conn.execute(
                    'UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?',
                    (line.quantity, line.sku, line.quantity),
                )
                if cur.rowcount != 1:
                    raise OutOfStockError(line.sku)  # rolls back earlier lines too
            cur = conn.execute(
                'INSERT INTO orders (user_id, amount, status, request_id) VALUES (?, ?, ?, ?)',
                (user_id, float(amount), 'pending', request_id),
            )
            order_id = cur.lastrowid
            conn.executemany(
                'INSERT INTO order_lines (order_id, sku, quantity) VALUES (?, ?, ?)',
                [(order_id, line.sku, line.quantity) for line in lines],
            )
            return order_id

    def mark_paid(self, order_id):
        with self._transaction() as conn:
            conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))

    def fail_order(self, order_id, status):
        with self._transaction() as conn:
            rows = conn.execute(
                'SELECT sku, quantity FROM order_lines WHERE order_id = ?', (order_id,)
            ).fetchall()
            for sku, quantity in rows:
                conn.execute('UPDATE products SET stock = stock + ? WHERE sku = ?', (quantity, sku))
            conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))

    def list_orders(self, user_id):
        with self._transaction() as conn:
            return conn.execute(
                'SELECT id, user_id, amount, status FROM orders WHERE user_id = ? ORDER BY id DESC',
                (user_id,),
            ).fetchall()
