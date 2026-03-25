# Creational Patterns

Creational patterns deal with object creation mechanisms, aiming to create objects in a manner suitable to the situation. They abstract the instantiation process, making a system independent of how its objects are created, composed, and represented.

---

## 1. Singleton

### Intent
Ensure a class has only one instance and provide a global point of access to it.

### When to Use
- Exactly one object is needed to coordinate actions across the system (e.g., a configuration manager, logger, or thread pool)
- Shared resource access must be controlled (database connection, file system)
- You want to avoid repeatedly creating expensive objects

### Structure
```
Singleton
├── -instance: Singleton  (static, private)
├── -Singleton()           (private constructor)
└── +getInstance(): Singleton  (static, public)
```

### Pseudocode
```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.config = {}

# Usage
a = Singleton()
b = Singleton()
assert a is b  # True — same instance
```

### Real-World Use Case
- **Application Logger**: A single logger instance routes all log messages to the same output stream/file, preventing duplicate logs or conflicting file handles.
- **Database Connection Pool**: One pool object manages all connections to avoid exhausting DB connections.

### Caveats
- Makes unit testing difficult (global state)
- Can be a disguised global variable — use sparingly
- In multi-threaded environments, getInstance() must be synchronized

---

## 2. Factory Method

### Intent
Define an interface for creating an object, but let subclasses decide which class to instantiate. Factory Method lets a class defer instantiation to subclasses.

### When to Use
- A class cannot anticipate the type of objects it needs to create
- Subclasses should control what gets created
- You want to encapsulate object creation logic and hide concrete types from clients

### Structure
```
Creator (abstract)
├── +factoryMethod(): Product   (abstract)
└── +operation()               (uses factoryMethod)

ConcreteCreator extends Creator
└── +factoryMethod(): ConcreteProduct

Product (interface)
ConcreteProduct implements Product
```

### Pseudocode
```python
class Notification:  # Product interface
    def send(self, message): pass

class EmailNotification(Notification):
    def send(self, message):
        print(f"Email: {message}")

class SMSNotification(Notification):
    def send(self, message):
        print(f"SMS: {message}")

class NotificationFactory:  # Creator
    def create_notification(self, channel) -> Notification:
        if channel == "email":
            return EmailNotification()
        elif channel == "sms":
            return SMSNotification()
        raise ValueError(f"Unknown channel: {channel}")

# Usage
factory = NotificationFactory()
notif = factory.create_notification("email")
notif.send("Hello!")  # Email: Hello!
```

### Real-World Use Case
- **UI Framework Buttons**: A cross-platform UI library uses a factory method so Windows creates `WindowsButton` and macOS creates `MacButton`, while the client code calls `createButton()` without knowing the concrete type.
- **Payment Processors**: An e-commerce system creates `StripePayment`, `PayPalPayment`, or `CryptoPayment` objects depending on user selection.

---

## 3. Abstract Factory

### Intent
Provide an interface for creating **families** of related or dependent objects without specifying their concrete classes.

### When to Use
- A system must be independent of how its products are created
- You need to ensure that a family of products works together (UI theme, OS-specific widgets)
- You want to enforce constraints across product families

### Structure
```
AbstractFactory (interface)
├── +createProductA(): AbstractProductA
└── +createProductB(): AbstractProductB

ConcreteFactory1 implements AbstractFactory
ConcreteFactory2 implements AbstractFactory

AbstractProductA / AbstractProductB (interfaces)
ConcreteProductA1, ConcreteProductA2 (implementations)
ConcreteProductB1, ConcreteProductB2 (implementations)
```

### Pseudocode
```python
class GUIFactory:  # Abstract Factory
    def create_button(self): pass
    def create_checkbox(self): pass

class WindowsFactory(GUIFactory):
    def create_button(self):
        return WindowsButton()
    def create_checkbox(self):
        return WindowsCheckbox()

class MacFactory(GUIFactory):
    def create_button(self):
        return MacButton()
    def create_checkbox(self):
        return MacCheckbox()

def build_ui(factory: GUIFactory):
    button = factory.create_button()
    checkbox = factory.create_checkbox()
    button.render()
    checkbox.render()

# Usage
os_type = detect_os()
factory = WindowsFactory() if os_type == "windows" else MacFactory()
build_ui(factory)
```

### Real-World Use Case
- **Cross-platform UI toolkits**: Qt, wxWidgets, or JavaFX produce native-looking components per OS via abstract factories.
- **Cloud provider SDKs**: An abstract factory produces `S3Bucket`/`AzureBlob`/`GCSBucket` depending on the configured cloud, keeping application code provider-agnostic.

### Factory Method vs. Abstract Factory

| | Factory Method | Abstract Factory |
|---|---|---|
| Scope | Single product | Family of products |
| Mechanism | Inheritance (subclass overrides) | Composition (factory object injected) |
| Use when | One varying product type | Multiple related product types |

---

## 4. Builder

### Intent
Separate the construction of a complex object from its representation, allowing the same construction process to create different representations.

### When to Use
- An object requires many optional parameters (avoid telescoping constructors)
- Construction involves multiple steps that must occur in a specific order
- You want to produce different representations of the same product (e.g., XML vs. JSON report)

### Structure
```
Director
└── +construct(builder: Builder)

Builder (interface)
├── +buildPartA()
├── +buildPartB()
└── +getResult(): Product

ConcreteBuilder implements Builder
Product
```

### Pseudocode
```python
class QueryBuilder:
    def __init__(self):
        self._table = ""
        self._conditions = []
        self._columns = ["*"]
        self._limit = None

    def from_table(self, table):
        self._table = table
        return self  # fluent interface

    def select(self, *columns):
        self._columns = list(columns)
        return self

    def where(self, condition):
        self._conditions.append(condition)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def build(self):
        cols = ", ".join(self._columns)
        sql = f"SELECT {cols} FROM {self._table}"
        if self._conditions:
            sql += " WHERE " + " AND ".join(self._conditions)
        if self._limit:
            sql += f" LIMIT {self._limit}"
        return sql

# Usage
query = (
    QueryBuilder()
    .from_table("users")
    .select("id", "name", "email")
    .where("active = 1")
    .where("age > 18")
    .limit(100)
    .build()
)
# SELECT id, name, email FROM users WHERE active = 1 AND age > 18 LIMIT 100
```

### Real-World Use Case
- **HTTP Request Builders**: Libraries like Python's `requests` or Java's `HttpClient.newBuilder()` use builder to construct requests with optional headers, timeouts, body, etc.
- **Document Generators**: Building PDF, HTML, or Markdown reports from the same data by swapping the concrete builder.
- **Test Data Factories**: Creating complex domain objects in tests without dozens of constructor arguments.

---

## 5. Prototype

### Intent
Specify the kinds of objects to create using a prototypical instance, and create new objects by **copying** (cloning) this prototype.

### When to Use
- Object creation is expensive (complex initialization, DB lookups) and a copy is cheaper
- You need copies of objects with slight variations at runtime
- Classes to instantiate are specified at runtime (e.g., dynamic plugin loading)
- You want to avoid a class hierarchy of factories

### Structure
```
Prototype (interface)
└── +clone(): Prototype

ConcretePrototype implements Prototype
└── +clone(): Prototype  (returns copy of self)

Client
└── uses prototype.clone() instead of new ConcretePrototype()
```

### Pseudocode
```python
import copy

class DocumentTemplate:
    def __init__(self, title, sections, styles):
        self.title = title
        self.sections = sections   # list — mutable
        self.styles = styles       # dict — mutable

    def clone(self):
        # Deep copy ensures nested objects are independent
        return copy.deepcopy(self)

# Create a prototype
base_report = DocumentTemplate(
    title="Monthly Report",
    sections=["Summary", "Details", "Appendix"],
    styles={"font": "Arial", "size": 12}
)

# Clone and customize — base_report is untouched
march_report = base_report.clone()
march_report.title = "March 2026 Report"
march_report.sections.append("Q1 Forecast")
```

### Shallow vs. Deep Copy

| | Shallow Copy | Deep Copy |
|---|---|---|
| Primitives | Copied by value | Copied by value |
| Nested objects | Shared reference | New independent copy |
| Use when | No nested mutable state | Nested mutable objects present |

### Real-World Use Case
- **Game Enemies**: A game spawns dozens of enemy instances by cloning a pre-configured prototype rather than re-loading assets and running initialization logic.
- **Configuration Templates**: A deployment system maintains baseline server configs as prototypes; each environment clones and overrides only differing values.
- **Cell division metaphor**: Biological inspiration — a template splits to produce configured offspring.

---

## Summary Table

| Pattern | Problem Solved | Key Mechanism |
|---|---|---|
| Singleton | One instance only | Private constructor + static accessor |
| Factory Method | Decouple creation from use (one type) | Subclass overrides creation method |
| Abstract Factory | Families of related objects | Factory object injected/swapped |
| Builder | Complex multi-step construction | Step-by-step builder with fluent API |
| Prototype | Cheap copies with variation | Clone existing instance |
