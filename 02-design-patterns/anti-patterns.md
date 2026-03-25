# Anti-Patterns

Anti-patterns are common responses to recurring problems that are ineffective and counterproductive. Recognizing them is as important as knowing the good patterns.

---

## 1. God Object / God Class

### What it is
A single class that knows too much or does too much — it holds most of the application's data and logic.

### Why it happens
- Organic growth: "just add it here"
- No clear domain boundaries
- Fear of creating new files/classes

### Why it's harmful
- Impossible to test in isolation
- Merge conflicts on every feature
- Violates Single Responsibility Principle

### How to fix
- Identify distinct responsibilities and extract them into separate classes
- Apply Domain-Driven Design — find your bounded contexts
- Decompose by feature, not by layer

---

## 2. Spaghetti Code

### What it is
Code with tangled control flow — deeply nested conditionals, goto-like jumps, no clear structure.

### Why it happens
- Patches on patches without refactoring
- No design upfront
- Deadline pressure

### Why it's harmful
- Impossible to reason about
- Every change risks breaking something unrelated

### How to fix
- Extract methods/functions to flatten nesting
- Replace conditionals with polymorphism or strategy pattern
- Introduce clear layers (controller → service → repository)

---

## 3. Golden Hammer

### What it is
Applying a familiar technology or pattern to every problem regardless of fit. "If all you have is a hammer, everything looks like a nail."

### Examples
- Using a relational DB for everything (even graph data)
- Microservices for a 2-person startup
- Kafka for a feature that needs a simple job queue

### How to fix
- Evaluate tools against requirements, not familiarity
- Build a tech radar — know what's in your toolbox and when each applies

---

## 4. Premature Optimization

### What it is
Optimizing code before you know where the bottleneck is.

> "Premature optimization is the root of all evil." — Knuth

### Why it's harmful
- Wastes time on non-bottlenecks
- Makes code harder to read and maintain
- Optimizes the wrong thing

### How to fix
1. Make it work
2. Make it correct
3. Profile to find the actual bottleneck
4. Make it fast (only the bottleneck)

---

## 5. Magic Numbers / Magic Strings

### What it is
Unexplained literals embedded in code.

```python
# Bad
if status == 3:
    ...
time.sleep(86400)

# Good
APPROVED_STATUS = 3
ONE_DAY_SECONDS = 86400
```

### How to fix
- Named constants or enums
- Configuration files for environment-specific values

---

## 6. Copy-Paste Programming

### What it is
Duplicating code instead of abstracting it.

### Why it's harmful
- Bug fixes must be applied in N places
- Divergence over time — copies drift apart
- Violates DRY (Don't Repeat Yourself)

### How to fix
- Extract shared logic into a function/class
- But: don't abstract prematurely — wait until you have 3+ copies (Rule of Three)

---

## 7. Lava Flow (Dead Code)

### What it is
Code that nobody understands anymore but everyone is afraid to delete. Like cooled lava — hard and in the way.

### Why it happens
- Original author left
- No tests to verify deletion is safe
- "It might be needed someday"

### How to fix
- Delete it — that's what version control is for
- Write tests first to document current behavior, then remove dead code

---

## 8. Big Ball of Mud

### What it is
A system with no discernible architecture — everything depends on everything.

### Why it happens
- No architectural vision
- Accumulated technical debt
- Constant firefighting

### How to fix
- Identify seams and introduce boundaries incrementally
- Strangler Fig pattern: build new architecture alongside old, migrate piece by piece

---

## 9. Anemic Domain Model

### What it is
Domain objects (entities) that are just data bags with no behavior — all logic lives in service classes.

```python
# Anemic
class Order:
    status: str
    items: list

class OrderService:
    def confirm(self, order): order.status = "confirmed"
    def calculate_total(self, order): ...

# Rich domain model
class Order:
    def confirm(self): self.status = "confirmed"
    def total(self): return sum(i.price for i in self.items)
```

### Why it's harmful
- Business logic scattered across services
- Domain model doesn't reflect the real domain
- Hard to enforce invariants

### How to fix
- Move behavior into domain objects
- Apply DDD tactical patterns (entities, value objects, aggregates)

---

## Key Architect Takeaways

1. Anti-patterns are symptoms of missing design — address root causes, not symptoms.
2. God Objects and Big Ball of Mud are the most common in legacy systems — use Strangler Fig to escape.
3. Golden Hammer is an architect-level risk — always match tool to problem.
4. Profile before optimizing — intuition about bottlenecks is usually wrong.
5. Anemic domain models are fine for simple CRUD; for complex domains, invest in rich models.
