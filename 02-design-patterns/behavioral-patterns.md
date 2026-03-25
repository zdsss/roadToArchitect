# Behavioral Patterns

Behavioral patterns are concerned with algorithms and assignment of responsibilities between objects.

---

## 1. Observer

### Intent
Define a one-to-many dependency so that when one object changes state, all dependents are notified and updated automatically.

### When to Use
- Event systems, pub/sub, reactive UIs
- When a change in one object requires changing others and you don't know how many

### Pseudocode
```python
class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
    def subscribe(self, event, fn):
        self._listeners[event].append(fn)
    def publish(self, event, data):
        for fn in self._listeners[event]:
            fn(data)
```

### Real-World Example
- DOM event listeners
- Message brokers (Kafka, RabbitMQ topics)
- React state / Redux

---

## 2. Strategy

### Intent
Define a family of algorithms, encapsulate each one, and make them interchangeable.

### When to Use
- Multiple variants of an algorithm
- Swap algorithms at runtime
- Avoid conditionals that select algorithm variants

### Pseudocode
```python
class Sorter:
    def __init__(self, strategy):
        self.strategy = strategy
    def sort(self, data):
        return self.strategy(data)

sorter = Sorter(strategy=merge_sort)
sorter.sort([3, 1, 2])
```

### Real-World Example
- Payment processors (Stripe, PayPal, Bank Transfer — each a strategy)
- Routing algorithms (shortest path, fewest hops)
- Compression strategies (gzip, brotli, lz4)

---

## 3. Command

### Intent
Encapsulate a request as an object, allowing parameterization, queuing, logging, and undoable operations.

### When to Use
- Undo/redo functionality
- Queue or schedule operations
- Audit logging of actions
- Transactional behavior

### Pseudocode
```python
class Command:
    def execute(self): ...
    def undo(self): ...

class MoveFileCommand(Command):
    def execute(self): os.rename(src, dst)
    def undo(self): os.rename(dst, src)

history = []
cmd = MoveFileCommand(src, dst)
cmd.execute()
history.append(cmd)
# later: history.pop().undo()
```

### Real-World Example
- Database transaction logs
- UI undo stacks (Photoshop, Google Docs)
- Job queues (Celery tasks are commands)

---

## 4. Chain of Responsibility

### Intent
Pass a request along a chain of handlers. Each handler decides to process or pass to the next.

### When to Use
- More than one object may handle a request
- The handler isn't known a priori
- Request should be processed by one of several handlers

### Pseudocode
```python
class Handler:
    def __init__(self, next_handler=None):
        self.next = next_handler
    def handle(self, request):
        if self.can_handle(request):
            return self.process(request)
        elif self.next:
            return self.next.handle(request)
```

### Real-World Example
- HTTP middleware (auth → rate limit → logging → handler)
- Support escalation tiers (L1 → L2 → L3)
- Exception handling chains

---

## 5. Template Method

### Intent
Define the skeleton of an algorithm in a base class, deferring some steps to subclasses.

### When to Use
- Invariant parts of algorithm belong in base class
- Subclasses implement varying parts
- Control subclass extensions (hook methods)

### Pseudocode
```python
class DataProcessor:
    def process(self):   # template method
        data = self.read()
        data = self.transform(data)
        self.write(data)

    def read(self): raise NotImplementedError
    def transform(self, data): return data  # default hook
    def write(self, data): raise NotImplementedError
```

### Real-World Example
- Django class-based views (`get()`, `post()` override `dispatch()`)
- JUnit test lifecycle (`setUp`, `test`, `tearDown`)

---

## 6. State

### Intent
Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.

### When to Use
- Object behavior depends heavily on its state
- Large conditionals based on state throughout the codebase
- Finite state machines

### Pseudocode
```python
class Order:
    def __init__(self):
        self.state = PendingState()
    def confirm(self):
        self.state = self.state.confirm(self)
    def ship(self):
        self.state = self.state.ship(self)
```

### Real-World Example
- Order lifecycle (Pending → Confirmed → Shipped → Delivered)
- TCP connection states (LISTEN → SYN_SENT → ESTABLISHED → CLOSE_WAIT)
- Traffic lights

---

## 7. Iterator

### Intent
Provide a way to sequentially access elements of a collection without exposing its underlying representation.

### Real-World Example
- Database cursors
- Python generators (`yield`)
- Kafka consumer iterating over partitions

---

## Key Architect Takeaways

1. **Observer/Event Bus** decouples producers from consumers — foundational for event-driven architecture.
2. **Strategy** replaces `if/else` ladders — prefer composition over inheritance.
3. **Command** enables undo, queuing, and audit trails — use in CQRS write side.
4. **Chain of Responsibility** is how every middleware framework works under the hood.
5. **State** machines are underused — they make complex lifecycle logic explicit and testable.
