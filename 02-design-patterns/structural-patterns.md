# Structural Patterns

Structural patterns deal with how classes and objects are composed to form larger structures.

---

## 1. Adapter

### Intent
Convert an interface of a class into another interface clients expect. Lets incompatible interfaces work together.

### When to Use
- Integrating legacy code or third-party libraries with incompatible interfaces
- You want to use an existing class but its interface doesn't match what you need

### Structure
```
Client → Target (interface) ← Adapter → Adaptee
```

### Pseudocode
```python
class LegacyPrinter:
    def print_old_way(self, text): ...

class PrinterAdapter:
    def __init__(self, legacy):
        self.legacy = legacy
    def print(self, text):  # new interface
        self.legacy.print_old_way(text)
```

### Real-World Example
- ORMs adapting DB drivers (psycopg2 → SQLAlchemy)
- Payment gateway adapters (Stripe/PayPal behind one interface)

---

## 2. Decorator

### Intent
Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing.

### When to Use
- Add behavior to individual objects without affecting others
- Behavior can be added and removed at runtime
- Extending via subclassing would lead to an explosion of classes

### Structure
```
Component (interface)
├── ConcreteComponent
└── Decorator (wraps Component)
    ├── LoggingDecorator
    ├── CachingDecorator
    └── AuthDecorator
```

### Pseudocode
```python
class DataService:
    def fetch(self, id): return db.get(id)

class CachingDecorator:
    def __init__(self, service):
        self.service = service
        self.cache = {}
    def fetch(self, id):
        if id not in self.cache:
            self.cache[id] = self.service.fetch(id)
        return self.cache[id]
```

### Real-World Example
- HTTP middleware stacks (auth → logging → rate-limit → handler)
- Python `@functools.lru_cache`, `@property`

---

## 3. Facade

### Intent
Provide a simplified interface to a complex subsystem.

### When to Use
- Simplify a complex library or set of APIs
- Layer your subsystems — higher layers use facades of lower layers
- Reduce dependencies on complex subsystem internals

### Structure
```
Client → Facade → SubsystemA
                → SubsystemB
                → SubsystemC
```

### Pseudocode
```python
class OrderFacade:
    def place_order(self, cart, user):
        inventory.check(cart)
        payment.charge(user, cart.total)
        shipping.schedule(user.address)
        notification.send(user, "Order confirmed")
```

### Real-World Example
- API Gateway hiding microservice complexity
- SDK wrapping complex REST APIs

---

## 4. Proxy

### Intent
Provide a surrogate or placeholder for another object to control access to it.

### Types
| Type | Purpose |
|------|---------|
| Virtual Proxy | Lazy initialization — delay expensive object creation |
| Protection Proxy | Access control |
| Remote Proxy | Local representative of remote object (RPC stub) |
| Caching Proxy | Cache results of expensive operations |

### Pseudocode
```python
class ImageProxy:
    def __init__(self, path):
        self.path = path
        self._image = None
    def display(self):
        if not self._image:
            self._image = RealImage(self.path)  # load only when needed
        self._image.display()
```

### Real-World Example
- Service mesh sidecar proxies (Envoy, Linkerd)
- ORM lazy-loading relationships
- API Gateway as reverse proxy

---

## 5. Composite

### Intent
Compose objects into tree structures to represent part-whole hierarchies. Let clients treat individual objects and compositions uniformly.

### When to Use
- Tree structures: file system, UI component trees, org charts
- You want clients to ignore the difference between leaf and composite

### Pseudocode
```python
class Component:
    def render(self): ...

class Leaf(Component):
    def render(self): print(self.text)

class Container(Component):
    def __init__(self):
        self.children = []
    def add(self, c): self.children.append(c)
    def render(self):
        for c in self.children: c.render()
```

### Real-World Example
- React component tree
- HTML DOM
- File system (files and directories)

---

## 6. Bridge

### Intent
Decouple an abstraction from its implementation so both can vary independently.

### When to Use
- Avoid permanent binding between abstraction and implementation
- Both abstraction and implementation should be extensible via subclassing

### Pseudocode
```python
class Notification:
    def __init__(self, sender):  # sender is the "bridge"
        self.sender = sender
    def send(self, msg): self.sender.deliver(msg)

class EmailSender:
    def deliver(self, msg): ...

class SMSSender:
    def deliver(self, msg): ...
```

### Real-World Example
- Notification system supporting multiple channels
- Database drivers (abstraction: ORM, implementation: specific DB)

---

## Key Architect Takeaways

1. **Adapter** when you can't change existing code but need interop.
2. **Decorator** for composable middleware pipelines — HTTP, logging, auth.
3. **Facade** at service boundaries — hide complexity behind clean APIs.
4. **Proxy** for cross-cutting concerns: caching, auth, circuit breaking.
5. **Composite** whenever you model tree structures in your domain.
