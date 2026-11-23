"""Unit tests for StoreRepository."""


def test_get_product_is_not_sql_injectable(repo):
    assert repo.get_product("x' OR '1'='1") is None