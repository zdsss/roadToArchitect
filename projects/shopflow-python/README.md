# ShopFlow Python — Sprint 1：命令行商品管理

## 目标

实现一个可在终端运行的商品管理工具，数据存储在 JSON 文件中。

完成本 Sprint 后，你将能够：
- 用 Big-O 分析自己的代码
- 解释为什么用 `dict` 而不是 `list` 存储商品
- 用 O(1) 时间复杂度完成商品搜索

---

## 待实现功能

```
python -m shop.cli add --name "Widget" --price 9.99 --stock 100
python -m shop.cli get --id 1
python -m shop.cli list
python -m shop.cli update --id 1 --price 12.99
python -m shop.cli delete --id 1
python -m shop.cli search --name "Widget"
```

---

## 复杂度分析要求

在 `product_store.py` 的每个方法上方，用注释写明时间复杂度，格式：

```python
def get_by_id(self, product_id: int):
    # Time Complexity: O(1) — dict 按 key 查找是常数时间
    # Space Complexity: O(1) — 不分配额外空间
    return self._store.get(product_id)
```

---

## 文件结构

```
projects/shopflow-python/
├── shop/
│   ├── __init__.py
│   ├── cli.py              # 命令行入口（待实现）
│   └── product_store.py    # 商品存储（待实现）
├── tests/
│   └── test_product_store.py  # 单元测试（待实现）
├── data/
│   └── .gitkeep           # JSON数据文件存放在这里（不提交）
├── README.md
└── requirements.txt
```

---

## 验收标准

- [ ] `add` 命令：添加商品，自动分配 ID，持久化到 JSON
- [ ] `get` 命令：按 ID 查询，O(1) 时间复杂度（用 dict）
- [ ] `list` 命令：列出所有商品
- [ ] `update` 命令：更新商品字段（幂等操作）
- [ ] `delete` 命令：删除商品
- [ ] `search` 命令：按名称搜索（O(n)，在注释里标明为什么这里 O(n) 是可接受的）
- [ ] 所有操作的复杂度都有注释说明
- [ ] pytest 单元测试覆盖所有方法

---

## 技术选型

- 存储：Python `dict` in memory + JSON 文件持久化
- CLI：`argparse` 或 `click`（推荐 `click`，更直观）
- 测试：`pytest`

---

## 学习资源

对应知识库：`01-fundamentals/algorithms-complexity.md`

重点阅读：
1. Big-O 分析方法
2. 常见数据结构的操作复杂度（特别是 dict vs list）
3. 什么时候 O(n) 是可接受的

---

## ADR 要求

完成 Sprint 1 后，在 `docs/decisions/` 目录创建：

**ADR-001-storage-data-structure.md**
> 记录：为什么用 dict 而不是 list 存储商品？
> 格式参考：`docs/decisions/ADR-template.md`

---

## Git 提交规范

本 Sprint 建议的提交序列：

```
feat: add product store with dict-based storage
feat: implement CLI commands for product CRUD
test: add unit tests for product store
docs: add complexity analysis comments
docs: create ADR-001 for data structure choice
```
