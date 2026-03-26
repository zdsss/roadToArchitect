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

    def add(self, name: str, price: float, stock: int) -> Product:
        """
        添加新商品

        Time Complexity: O(1) 均摊
            - dict 赋值：O(1) 均摊（偶发 rehash 为 O(n)，但均摊到每次操作仍是 O(1)）
            - _save() 写 JSON：O(n)，n 为商品总数（必须序列化全部数据）
            - 瓶颈在 I/O，而非数据结构本身
        Space Complexity: O(1) — 只新增一个 Product 对象
        """
        product = Product(id=self._next_id, name=name, price=price, stock=stock)
        self._store[self._next_id] = product
        self._next_id += 1
        self._save()
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        按 ID 查询商品

        Time Complexity: O(1)
            - Python dict 底层是哈希表，按 key 查找不需要遍历，直接计算哈希定位桶
            - 对比 list：list 按值查找需要 O(n) 遍历；按索引访问虽然是 O(1)，
              但 product_id 与 list 索引不一定连续对应
        Space Complexity: O(1) — 不分配额外空间，只返回已有对象的引用
        """
        return self._store.get(product_id)

    def list_all(self) -> list[Product]:
        """
        获取所有商品

        Time Complexity: O(n) — n 为商品总数
            - dict.values() 是 O(1)（返回视图，不复制）
            - list() 转换需要迭代全部 n 个元素，无法避免
        Space Complexity: O(n) — 新建了一个包含所有商品引用的 list
        """
        return list(self._store.values())

    def update(self, product_id: int, **kwargs) -> Optional[Product]:
        """
        更新商品字段

        Time Complexity: O(k)，k 为传入的字段数（通常极小，视为 O(1)）
            - dict.get()：O(1)
            - setattr 循环：O(k)，k ≤ 4（Product 只有 4 个字段）
            - _save()：O(n)，同 add()，瓶颈在 I/O
        Space Complexity: O(1) — 原地修改，不分配新对象

        注意：这是幂等操作——用相同参数调用多次，结果相同
            幂等性对 HTTP PUT 语义很重要：客户端可以安全重试
        """
        product = self._store.get(product_id)
        if product is None:
            return None

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        self._save()
        return product

    def delete(self, product_id: int) -> bool:
        """
        删除商品

        Time Complexity: O(1) 均摊
            - `in` 操作符对 dict：O(1)
            - `del dict[key]`：O(1) 均摊
            - _save()：O(n)，同 add()
        Space Complexity: O(1) — 释放一个对象，不分配新空间
        """
        if product_id not in self._store:
            return False
        del self._store[product_id]
        self._save()
        return True

    def search_by_name(self, name: str) -> list[Product]:
        """
        按名称搜索商品（大小写不敏感）

        Time Complexity: O(n) — n 为商品总数
            - 必须检查每一个商品的名称，无法跳过
            - 没有名称索引，所以无法做到比 O(n) 更快

        为什么这里 O(n) 是可接受的：
            - 当前场景：商品数量 < 10,000，O(n) 耗时 < 1ms，用户感知不到
            - 搜索是低频操作（相比按 ID 查询），性能不是瓶颈
            - 过早优化（引入 Elasticsearch）会带来运维成本，不值得

        迁移信号：当商品数量超过 100 万，且搜索成为性能瓶颈时 → 引入倒排索引（Elasticsearch）

        Space Complexity: O(k) — k 为匹配结果数，最坏 O(n)
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
