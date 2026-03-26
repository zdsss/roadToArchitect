"""
ShopFlow — 商品存储模块（Sprint 1）

学习目标：
- 理解为什么用 dict 而不是 list 存储商品（O(1) vs O(n) 查找）
- 掌握 JSON 文件的读写持久化
- 为每个方法写复杂度注释
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "products.json")


@dataclass
class Product:
    id: int
    name: str
    price: float
    stock: int


class ProductStore:
    """
    基于 dict 的商品存储

    数据结构选择：dict（HashMap）
    理由：按 ID 查询是最频繁的操作，dict 提供 O(1) 的查找复杂度。
    如果用 list，按 ID 查找需要 O(n) 遍历。

    TODO: 在每个方法上方添加时间复杂度注释
    """

    def __init__(self, data_file: str = DATA_FILE):
        self._data_file = data_file
        # 关键数据结构选择：用 dict，key 是 product_id
        # 这使得 get_by_id 是 O(1) 而不是 O(n)
        self._store: dict[int, Product] = {}
        self._next_id: int = 1
        self._load()

    # TODO: 添加时间复杂度注释
    def add(self, name: str, price: float, stock: int) -> Product:
        """
        添加新商品

        Time Complexity: TODO — 请分析并填写
        Space Complexity: TODO — 请分析并填写
        """
        product = Product(id=self._next_id, name=name, price=price, stock=stock)
        self._store[self._next_id] = product
        self._next_id += 1
        self._save()
        return product

    # TODO: 添加时间复杂度注释
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        按 ID 查询商品

        Time Complexity: TODO — 请分析并填写（提示：dict 的特性是什么？）
        Space Complexity: TODO
        """
        return self._store.get(product_id)

    # TODO: 添加时间复杂度注释
    def list_all(self) -> list[Product]:
        """
        获取所有商品

        Time Complexity: TODO
        Space Complexity: TODO
        """
        return list(self._store.values())

    # TODO: 添加时间复杂度注释
    def update(self, product_id: int, **kwargs) -> Optional[Product]:
        """
        更新商品字段

        Time Complexity: TODO
        Space Complexity: TODO

        注意：这是幂等操作——用相同参数调用多次，结果相同
        """
        product = self._store.get(product_id)
        if product is None:
            return None

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        self._save()
        return product

    # TODO: 添加时间复杂度注释
    def delete(self, product_id: int) -> bool:
        """
        删除商品

        Time Complexity: TODO
        Space Complexity: TODO
        """
        if product_id not in self._store:
            return False
        del self._store[product_id]
        self._save()
        return True

    # TODO: 添加时间复杂度注释，并在注释里解释为什么 O(n) 在这里是可接受的
    def search_by_name(self, name: str) -> list[Product]:
        """
        按名称搜索商品（大小写不敏感）

        Time Complexity: TODO — 提示：必须检查每个商品名称
        Space Complexity: TODO

        思考题：如果商品数量达到百万级，这个 O(n) 搜索会成为瓶颈吗？
        应该如何优化？（答案：建立名称索引，或使用 Elasticsearch）
        """
        name_lower = name.lower()
        return [p for p in self._store.values() if name_lower in p.name.lower()]

    def _load(self):
        """从 JSON 文件加载数据"""
        os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
        if not os.path.exists(self._data_file):
            return

        with open(self._data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._store = {
                item["id"]: Product(**item) for item in data.get("products", [])
            }
            self._next_id = data.get("next_id", 1)

    def _save(self):
        """持久化数据到 JSON 文件"""
        os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
        with open(self._data_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "products": [asdict(p) for p in self._store.values()],
                    "next_id": self._next_id,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
