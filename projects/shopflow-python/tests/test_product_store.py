"""
Sprint 1 单元测试

运行：pytest tests/ -v

学习目标：
- 理解测试驱动开发的好处
- 验证每个操作的复杂度行为
"""

import pytest
import time
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

    def test_get_is_constant_time(self, tmp_path, monkeypatch):
        """
        验证 get_by_id 的 O(1) 特性：
        无论 dict 中有 10 个还是 10,000 个商品，查询耗时应接近常数。

        设计说明：
        - 用 monkeypatch 禁用 _save()，避免 10,000 次 JSON 写入造成 O(n²) I/O 干扰
        - 对比小集合（10）和大集合（10,000）的查询耗时
        - 若是 O(n) 算法，大集合应慢约 1,000 倍；O(1) 应接近相同
        """
        data_file = str(tmp_path / "products.json")
        store = ProductStore(data_file=data_file)

        # 禁用磁盘写入，只测内存操作的复杂度
        monkeypatch.setattr(store, "_save", lambda: None)

        # 构造小集合（10个），测量查询耗时
        for i in range(10):
            store.add(f"Product-{i}", float(i), i)
        last_id_small = store._next_id - 1

        rounds = 10_000
        start = time.perf_counter()
        for _ in range(rounds):
            store.get_by_id(last_id_small)
        time_small = (time.perf_counter() - start) / rounds

        # 扩大到 10,000 个，测量查询耗时
        for i in range(9990):
            store.add(f"Extra-{i}", 1.0, 1)
        last_id_large = store._next_id - 1

        start = time.perf_counter()
        for _ in range(rounds):
            store.get_by_id(last_id_large)
        time_large = (time.perf_counter() - start) / rounds

        # O(1) 断言：大集合的查询时间不超过小集合的 20 倍
        # （若是 O(n)，大集合应慢约 1,000 倍）
        ratio = time_large / time_small if time_small > 0 else 1.0
        assert ratio < 20, (
            f"get_by_id 不符合 O(1) 预期：大集合耗时是小集合的 {ratio:.1f} 倍\n"
            f"  小集合(n=10)   : {time_small*1e6:.3f} μs/次\n"
            f"  大集合(n=10000): {time_large*1e6:.3f} μs/次"
        )


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
