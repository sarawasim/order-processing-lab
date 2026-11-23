"""Shared fixtures: a fresh temporary database for every test."""
import pytest

from cart import ShoppingCart
from repository import StoreRepository
from setup_db import initialize


@pytest.fixture
def repo(tmp_path):
    db = tmp_path / 'test.db'
    initialize(str(db))
    return StoreRepository(str(db))


@pytest.fixture
def cart(repo):
    return ShoppingCart('student', repo)