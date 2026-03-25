# Algorithms & Complexity

## Big-O Notation

Describes how an algorithm's runtime or space scales with input size `n`.

| Notation | Name | Example |
|----------|------|---------|
| O(1) | Constant | Hash table lookup |
| O(log n) | Logarithmic | Binary search |
| O(n) | Linear | Array scan |
| O(n log n) | Linearithmic | Merge sort, heap sort |
| O(n²) | Quadratic | Bubble sort, nested loops |
| O(2ⁿ) | Exponential | Brute-force subsets |
| O(n!) | Factorial | Permutations |

**Rule of thumb:** anything worse than O(n log n) is rarely acceptable at scale.

---

## Key Data Structures

### Array / Dynamic Array
- O(1) access by index
- O(n) insert/delete at middle
- Cache-friendly (contiguous memory)

### Hash Map / Hash Table
- O(1) average insert, delete, lookup
- O(n) worst case (all keys collide)
- Use for: counting, grouping, deduplication, caching

### Linked List
- O(1) insert/delete at known node
- O(n) access by index
- High memory overhead (pointers)
- Use when: frequent insert/delete at head, implementing queues

### Stack & Queue
| | Stack | Queue |
|--|-------|-------|
| Order | LIFO | FIFO |
| Operations | push, pop, peek | enqueue, dequeue |
| Use cases | undo, call stack, DFS | BFS, task scheduling, rate limiting |

### Binary Tree / BST
- BST: O(log n) search/insert when balanced, O(n) when degenerate
- Self-balancing: AVL, Red-Black Tree → guaranteed O(log n)

### Heap (Priority Queue)
- Min-heap: smallest element always at root
- O(log n) insert and extract-min
- Use for: Dijkstra, scheduling, top-K problems

### Graph
- **Adjacency list**: O(V+E) space, efficient for sparse graphs
- **Adjacency matrix**: O(V²) space, efficient for dense graphs, O(1) edge check

---

## Sorting Algorithms

| Algorithm | Best | Average | Worst | Space | Stable? |
|-----------|------|---------|-------|-------|--------|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |

**In practice:** Use the language's built-in sort (typically Timsort — O(n log n), stable).

---

## Search Algorithms

### Binary Search
- Requires sorted array
- O(log n) time
- Template:
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

### Graph Search
| | BFS | DFS |
|--|-----|-----|
| Data structure | Queue | Stack (or recursion) |
| Finds shortest path? | Yes (unweighted) | No |
| Memory | O(w) width | O(h) height |
| Use cases | Level-order, shortest path | Cycle detection, topological sort, maze |

---

## Fundamental Algorithm Patterns

### Sliding Window
- For subarray/substring problems with a contiguous constraint
- O(n) instead of O(n²) brute force

### Two Pointers
- Sorted array problems, palindrome checks, partition
- O(n) with no extra space

### Divide & Conquer
- Split problem in half recursively, combine results
- Merge sort, binary search, FFT

### Dynamic Programming
- Overlapping subproblems + optimal substructure
- Memoization (top-down) or tabulation (bottom-up)
- Classic problems: Fibonacci, knapsack, LCS, edit distance

### Greedy
- Make locally optimal choice at each step
- Works when greedy choice property holds
- Examples: Dijkstra, Huffman coding, interval scheduling

---

## Complexity at System Scale

| Operation | Approx. time |
|-----------|-------------|
| L1 cache reference | 1 ns |
| L2 cache reference | 4 ns |
| Main memory reference | 100 ns |
| SSD random read | 100 µs |
| HDD seek | 10 ms |
| Network round trip (same DC) | 500 µs |
| Network round trip (cross-region) | 150 ms |

**Architect tip:** These numbers inform where to cache, what to index, and when local computation beats a network call.

---

## Key Architect Takeaways

1. Know your data structures: hash maps and sorted structures (B-trees) power every database index.
2. O(n²) algorithms break at scale — always analyze query patterns against data size.
3. Database query plans are algorithms — EXPLAIN your queries.
4. Latency numbers above inform architecture decisions (cache layers, co-location).
5. Many distributed system problems map to graph algorithms (Paxos → consensus, Raft → leader election).
