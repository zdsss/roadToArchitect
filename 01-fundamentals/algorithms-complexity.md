# 算法与复杂度（Algorithms & Complexity）

## 大 O 表示法（Big-O Notation）

描述算法的运行时间或空间占用随输入规模 `n` 增长的变化趋势。

| 表示法 | 名称 | 示例 |
|----------|------|---------|
| O(1) | 常数（Constant） | Hash table 查找 |
| O(log n) | 对数（Logarithmic） | 二分查找 |
| O(n) | 线性（Linear） | 数组遍历 |
| O(n log n) | 线性对数（Linearithmic） | Merge sort、Heap sort |
| O(n²) | 平方（Quadratic） | Bubble sort、嵌套循环 |
| O(2ⁿ) | 指数（Exponential） | 暴力枚举子集 |
| O(n!) | 阶乘（Factorial） | 全排列 |

**经验法则：** 在大规模场景下，复杂度超过 O(n log n) 的算法通常是不可接受的。

---

## 核心数据结构

### Array / Dynamic Array（数组 / 动态数组）
- 按索引访问：O(1)
- 在中间插入/删除：O(n)
- 缓存友好（内存连续）

### Hash Map / Hash Table（哈希表）
- 平均插入、删除、查找：O(1)
- 最坏情况（所有键冲突）：O(n)
- 适用场景：计数、分组、去重、缓存

### Linked List（链表）
- 在已知节点处插入/删除：O(1)
- 按索引访问：O(n)
- 内存开销较大（需存储指针）
- 适用场景：频繁在头部插入/删除、实现队列

### Stack & Queue（栈与队列）
| | Stack（栈） | Queue（队列） |
|--|-------|-------|
| 顺序 | LIFO（后进先出） | FIFO（先进先出） |
| 操作 | push、pop、peek | enqueue、dequeue |
| 使用场景 | 撤销操作、调用栈、DFS | BFS、任务调度、限流 |

### Binary Tree / BST（二叉树 / 二叉搜索树）
- BST：平衡时搜索/插入为 O(log n)，退化时为 O(n)
- 自平衡变体：AVL、Red-Black Tree → 保证 O(log n)

### Heap（堆）/ Priority Queue（优先队列）
- Min-heap（最小堆）：根节点始终为最小元素
- 插入与取最小值：O(log n)
- 适用场景：Dijkstra 算法、任务调度、Top-K 问题

### Graph（图）
- **邻接表（Adjacency list）**：O(V+E) 空间，稀疏图效率高
- **邻接矩阵（Adjacency matrix）**：O(V²) 空间，稠密图效率高，边的查询为 O(1)

---

## 排序算法（Sorting Algorithms）

| 算法 | 最优 | 平均 | 最差 | 空间 | 稳定？ |
|-----------|------|---------|-------|-------|--------|
| Bubble Sort（冒泡排序） | O(n) | O(n²) | O(n²) | O(1) | 是 |
| Insertion Sort（插入排序） | O(n) | O(n²) | O(n²) | O(1) | 是 |
| Merge Sort（归并排序） | O(n log n) | O(n log n) | O(n log n) | O(n) | 是 |
| Quick Sort（快速排序） | O(n log n) | O(n log n) | O(n²) | O(log n) | 否 |
| Heap Sort（堆排序） | O(n log n) | O(n log n) | O(n log n) | O(1) | 否 |

**实践建议：** 优先使用语言内置排序（通常为 Timsort —— O(n log n)，稳定）。

---

## 搜索算法（Search Algorithms）

### Binary Search（二分查找）
- 要求数组已排序
- 时间复杂度：O(log n)
- 模板代码：
```python
lo, hi = 0, len(arr) - 1
while lo <= hi:
    mid = (lo + hi) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        lo = mid + 1
    else:
        hi = mid - 1
return -1
```

### 图搜索（Graph Search）
| | BFS（广度优先搜索） | DFS（深度优先搜索） |
|--|-----|-----|
| 数据结构 | 队列（Queue） | 栈（Stack）或递归 |
| 能否找最短路径？ | 可以（无权图） | 不可以 |
| 内存占用 | O(w)，w 为图的宽度 | O(h)，h 为图的深度 |
| 使用场景 | 层序遍历、最短路径 | 环检测、拓扑排序、迷宫求解 |

---

## 基础算法范式（Fundamental Algorithm Patterns）

### Sliding Window（滑动窗口）
- 用于具有连续约束的子数组/子字符串问题
- 将暴力 O(n²) 优化为 O(n)

### Two Pointers（双指针）
- 适用于有序数组问题、回文检测、分区操作
- O(n) 时间，无额外空间开销

### Divide & Conquer（分治法）
- 将问题递归地拆分为两半，再合并结果
- 典型应用：Merge sort、Binary search、FFT

### Dynamic Programming（动态规划）
- 适用于具有重叠子问题（Overlapping subproblems）和最优子结构（Optimal substructure）的问题
- 实现方式：记忆化（Memoization，自顶向下）或制表法（Tabulation，自底向上）
- 经典问题：Fibonacci、背包问题（Knapsack）、最长公共子序列（LCS）、编辑距离（Edit distance）

### Greedy（贪心算法）
- 每一步都做出局部最优选择
- 当贪心选择性质（Greedy choice property）成立时有效
- 典型应用：Dijkstra 算法、Huffman 编码、区间调度

---

## 系统规模下的复杂度参考（Complexity at System Scale）

| 操作 | 大约耗时 |
|-----------|-------------|
| L1 缓存读取 | 1 ns |
| L2 缓存读取 | 4 ns |
| 主内存读取 | 100 ns |
| SSD 随机读取 | 100 µs |
| HDD 寻道 | 10 ms |
| 网络往返（同数据中心） | 500 µs |
| 网络往返（跨地区） | 150 ms |

**架构师提示：** 上述延迟数字有助于判断在哪里引入缓存、哪些数据需要建索引，以及何时本地计算优于网络调用。

---

## 架构师核心要点（Key Architect Takeaways）

1. 熟悉数据结构：HashMap 和有序结构（B-tree）是每一种数据库索引的基石。
2. O(n²) 算法在大规模场景下会崩溃——务必结合数据量分析查询模式。
3. 数据库查询计划本质上也是算法——养成用 EXPLAIN 分析查询的习惯。
4. 上述延迟数字直接影响架构决策（缓存层的设计、服务的物理位置）。
5. 许多分布式系统问题都可以映射为图算法（Paxos → 共识，Raft → 领导者选举）。
