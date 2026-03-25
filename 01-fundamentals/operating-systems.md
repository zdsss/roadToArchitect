# Operating Systems Fundamentals

Core OS concepts every architect must understand — they underpin performance, concurrency, and infrastructure decisions.

---

## Processes vs Threads

| | Process | Thread |
|--|---------|--------|
| Memory | Own address space | Shared memory within process |
| Creation cost | High (fork) | Low |
| Communication | IPC (pipes, sockets, shared mem) | Shared variables (need sync) |
| Isolation | Strong — crash doesn't affect others | Weak — one thread can crash process |
| Use case | Microservices, isolation-critical tasks | Concurrent work within one service |

### Context Switching
The OS scheduler saves a process/thread's state (registers, PC, stack pointer) and loads another's. Cost:
- **Process switch**: ~1–10 μs (flush TLB, reload page tables)
- **Thread switch**: ~0.1–1 μs (same address space)

**Architect implication**: Thousands of threads = high context-switch overhead. Use async I/O + event loops (Node.js, asyncio) or worker pools.

---

## Concurrency Primitives

### Mutex (Mutual Exclusion Lock)
Only one thread holds it at a time. Others block.
```
lock(mutex)
  // critical section
unlock(mutex)
```

### Semaphore
Counts available resources. `wait()` decrements, `signal()` increments.
- Binary semaphore ≈ mutex
- Counting semaphore controls access to N resources (e.g., DB connection pool)

### Deadlock Conditions (all 4 must hold)
1. **Mutual exclusion** — resource held by only one thread
2. **Hold and wait** — thread holds resource while waiting for another
3. **No preemption** — resources can't be forcibly taken
4. **Circular wait** — T1 waits for T2, T2 waits for T1

**Prevention**: Lock ordering, timeouts, lock-free structures.

### Race Condition
Outcome depends on thread scheduling order. Fix with proper synchronization.

---

## Memory Management

### Virtual Memory
- Each process sees its own address space (illusion)
- OS maps virtual → physical via **page table**
- **Page fault**: accessed page not in RAM → OS loads from disk (swap)

### Memory Layout (typical process)
```
┌─────────────┐  high address
│   Stack     │  grows down — local vars, function frames
├─────────────┤
│     ↓       │
│    (gap)    │
│     ↑       │
├─────────────┤
│   Heap      │  grows up — dynamic allocation (malloc/new)
├─────────────┤
│   BSS       │  uninitialized globals
├─────────────┤
│   Data      │  initialized globals
├─────────────┤
│   Text      │  program code (read-only)
└─────────────┘  low address
```

### Common Memory Issues
| Issue | Description | Example |
|-------|-------------|----------|
| Memory leak | Allocated memory never freed | Forgotten `free()` / unclosed connections |
| Buffer overflow | Writing past allocated boundary | C string operations |
| Dangling pointer | Pointer to freed memory | Use-after-free |
| Stack overflow | Stack grows into forbidden region | Deep recursion |

---

## I/O Models

### Blocking I/O
Thread blocks until I/O completes. Simple but wastes CPU waiting.

### Non-Blocking I/O
I/O call returns immediately with EAGAIN if not ready. App polls.

### I/O Multiplexing (select/poll/epoll)
- One thread monitors many file descriptors
- `select`: O(n) scan, limited FDs
- `epoll` (Linux): O(1) event notification, scales to millions
- Foundation of Node.js, Nginx, Redis event loops

### Async I/O (AIO)
Kernel notifies app via callback/signal when I/O completes. True async.

### Architect Decision
```
CPU-bound work    → Multiple processes/threads (use all cores)
I/O-bound work    → Async/event-driven (Node.js, asyncio, Netty)
Mixed             → Thread pool + async I/O (Golang goroutines, Java virtual threads)
```

---

## File Systems

### Key Concepts
- **Inode**: metadata about a file (size, permissions, timestamps, pointers to data blocks). Not the filename.
- **Hard link**: another directory entry pointing to same inode
- **Soft link (symlink)**: file whose content is a path to another file

### File Descriptors
Integers the OS uses to track open files/sockets. Default limits (ulimit) cause "too many open files" errors at scale — always configure limits in production.

---

## Signals & Process Management

| Signal | Default action | Common use |
|--------|---------------|------------|
| SIGTERM | Terminate | Graceful shutdown (Docker stop) |
| SIGKILL | Kill (uncatchable) | Force kill (Docker kill) |
| SIGINT | Terminate | Ctrl+C |
| SIGHUP | Terminate | Reload config (Nginx) |
| SIGCHLD | Ignore | Parent notified of child exit |

**Always handle SIGTERM** for graceful shutdown — drain connections, flush buffers, deregister from service discovery.

---

## Key Architect Takeaways

1. Understand threads vs processes to choose the right concurrency model for each service.
2. Deadlocks happen in distributed systems too — design with timeouts and circuit breakers.
3. Virtual memory and swap affect latency — avoid swap in production databases.
4. `epoll`-based event loops handle C10K+ connections with a single thread.
5. File descriptor limits are a common production footgun — set them correctly.
