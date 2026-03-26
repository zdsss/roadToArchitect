"""
Sprint 1 单元测试

运行：pytest tests/ -v

学习目标：
- 理解测试驱动开发的好处
- 验证每个操作的复杂度行为
"""

import pytest
import tempfile
import os
from shop.product_store import ProductStore, Product


@pytest.fixture
def store(tmp_path):
    """使用临时文件的 ProductStore，每个测试隔离"""
    data_file = str(tmp_path / "products.json")
    return ProductStore(data_file=data_file)


class TestProductStoreAdd:
    def test_add_returns_product_with_id(self, store):
        product = store.add(name="Widget", price=9.99, stock=100)
        assert product.id == 1
        assert product.name == "Widget"
        assert product.price == 9.99
        assert product.stock == 100

    def test_add_increments_id(self, store):
        p1 = store.add(name="Widget", price=9.99, stock=10)
        p2 = store.add(name="Gadget", price=19.99, stock=20)
        assert p1.id == 1
        assert p2.id == 2


class TestProductStoreGetById:
    def test_get_existing_product(self, store):
        added = store.add(name="Widget", price=9.99, stock=100)
        found = store.get_by_id(added.id)
        assert found is not None
        assert found.id == added.id
        assert found.name == "Widget"

    def test_get_nonexistent_returns_none(self, store):
        result = store.get_by_id(999)
        assert result is None

    # TODO: 添加一个测试，验证查找 O(1) 的行为
    # 提示：可以添加 1000 个商品，然后验证查询最后一个商品的时间接近常数


class TestProductStoreList:
    def test_list_empty(self, store):
        assert store.list_all() == []

    def test_list_all_products(self, store):
        store.add("Widget", 9.99, 10)
        store.add("Gadget", 19.99, 20)
        products = store.list_all()
        assert len(products) == 2


class TestProductStoreUpdate:
    def test_update_price(self, store):
        product = store.add("Widget", 9.99, 100)
        updated = store.update(product.id, price=12.99)
        assert updated.price == 12.99
        assert updated.name == "Widget"  # 未修改的字段不变

    def test_update_nonexistent_returns_none(self, store):
        result = store.update(999, price=12.99)
        assert result is None

    def test_update_is_idempotent(self, store):
        """幂等性：用相同参数调用多次，结果相同"""
        product = store.add("Widget", 9.99, 100)
        result1 = store.update(product.id, price=12.99)
        result2 = store.update(product.id, price=12.99)
        assert result1.price == result2.price == 12.99


class TestProductStoreDelete:
    def test_delete_existing(self, store):
        product = store.add("Widget", 9.99, 100)
        assert store.delete(product.id) is True
        assert store.get_by_id(product.id) is None

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete(999) is False


class TestProductStoreSearch:
    def test_search_finds_matching(self, store):
        store.add("Wireless Widget", 9.99, 10)
        store.add("Wired Gadget", 19.99, 20)
        results = store.search_by_name("widget")
        assert len(results) == 1
        assert results[0].name == "Wireless Widget"

    def test_search_case_insensitive(self, store):
        store.add("Widget", 9.99, 10)
        results = store.search_by_name("WIDGET")
        assert len(results) == 1

    def test_search_no_results(self, store):
        store.add("Widget", 9.99, 10)
        results = store.search_by_name("nonexistent")
        assert results == []


class TestProductStorePersistence:
    def test_data_persists_across_instances(self, tmp_path):
        """验证数据在重启后依然存在"""
        data_file = str(tmp_path / "products.json")

        # 第一个实例添加商品
        store1 = ProductStore(data_file=data_file)
        store1.add("Widget", 9.99, 100)

        # 第二个实例（模拟重启）能读到数据
        store2 = ProductStore(data_file=data_file)
        products = store2.list_all()
        assert len(products) == 1
        assert products[0].name == "Widget"
