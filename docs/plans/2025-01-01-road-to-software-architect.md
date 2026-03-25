# Road to Software Architect — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a comprehensive, well-organized markdown knowledge base covering the skills, concepts, and patterns needed to become a Software Architect.

**Architecture:** A flat-folder markdown structure organized by topic domain (fundamentals, patterns, system design, etc.), with a master README index linking all sections. Each topic file is self-contained with theory, key concepts, examples, and further reading.

**Tech Stack:** Markdown, Git, no build tools required.

---

### Task 1: Project scaffold — README and folder structure

**Files:**
- Create: `README.md`
- Create: `01-fundamentals/README.md`
- Create: `02-design-patterns/README.md`
- Create: `03-system-design/README.md`
- Create: `04-architecture-patterns/README.md`
- Create: `05-data/README.md`
- Create: `06-devops-infrastructure/README.md`
- Create: `07-soft-skills/README.md`
- Create: `08-case-studies/README.md`

**Step 1: Create root README**

```markdown
# Road to Software Architect

A structured knowledge base for engineers growing into Software Architect roles.

## Sections

| # | Topic | Description |
|---|-------|-------------|
| 1 | [Fundamentals](./01-fundamentals/README.md) | CS basics, networking, OS, security |
| 2 | [Design Patterns](./02-design-patterns/README.md) | GoF patterns, anti-patterns |
| 3 | [System Design](./03-system-design/README.md) | Scalability, reliability, distributed systems |
| 4 | [Architecture Patterns](./04-architecture-patterns/README.md) | Microservices, event-driven, layered, hexagonal |
| 5 | [Data](./05-data/README.md) | Databases, caching, messaging |
| 6 | [DevOps & Infrastructure](./06-devops-infrastructure/README.md) | CI/CD, containers, cloud |
| 7 | [Soft Skills](./07-soft-skills/README.md) | Communication, trade-off analysis, leadership |
| 8 | [Case Studies](./08-case-studies/README.md) | Real-world architecture teardowns |
```

**Step 2: Create each section README with a stub**

Each section README follows this template:
```markdown
# [Section Name]

## Topics
- [ ] Topic A
- [ ] Topic B

## Notes
_Work in progress._
```

**Step 3: Initialize git**

```bash
git init
git add .
git commit -m "chore: scaffold project structure"
```

---

### Task 2: Fundamentals section

**Files:**
- Create: `01-fundamentals/networking.md`
- Create: `01-fundamentals/operating-systems.md`
- Create: `01-fundamentals/security-basics.md`
- Create: `01-fundamentals/complexity-and-algorithms.md`
- Modify: `01-fundamentals/README.md`

**Step 1: Write `networking.md`**

Covers: OSI model, TCP/IP, HTTP/HTTPS/HTTP2/HTTP3, DNS, load balancing, CDN, WebSockets.

Structure:
```markdown
# Networking Fundamentals

## OSI Model
...

## TCP vs UDP
...

## HTTP/HTTPS
...

## DNS
...

## Key Architect Considerations
...
```

**Step 2: Write `operating-systems.md`**

Covers: processes vs threads, concurrency, memory management, I/O models (blocking, non-blocking, async), file systems.

**Step 3: Write `security-basics.md`**

Covers: AuthN vs AuthZ, OAuth2/OIDC, JWT, TLS, OWASP top 10, secrets management.

**Step 4: Write `complexity-and-algorithms.md`**

Covers: Big-O, common data structures and when to use them, trade-offs relevant to system design.

**Step 5: Update section README checklist, commit**

```bash
git add 01-fundamentals/
git commit -m "docs: add fundamentals section"
```

---

### Task 3: Design Patterns section

**Files:**
- Create: `02-design-patterns/creational.md`
- Create: `02-design-patterns/structural.md`
- Create: `02-design-patterns/behavioral.md`
- Create: `02-design-patterns/anti-patterns.md`
- Modify: `02-design-patterns/README.md`

**Step 1: Write `creational.md`**

Covers: Singleton, Factory, Abstract Factory, Builder, Prototype — with use cases and code sketches.

**Step 2: Write `structural.md`**

Covers: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy.

**Step 3: Write `behavioral.md`**

Covers: Chain of Responsibility, Command, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor.

**Step 4: Write `anti-patterns.md`**

Covers: God Object, Spaghetti Code, Shotgun Surgery, Golden Hammer, Premature Optimization, etc.

**Step 5: Commit**

```bash
git add 02-design-patterns/
git commit -m "docs: add design patterns section"
```

---

### Task 4: System Design section

**Files:**
- Create: `03-system-design/scalability.md`
- Create: `03-system-design/reliability-and-availability.md`
- Create: `03-system-design/distributed-systems.md`
- Create: `03-system-design/api-design.md`
- Create: `03-system-design/interview-framework.md`
- Modify: `03-system-design/README.md`

**Step 1: Write `scalability.md`**

Covers: horizontal vs vertical scaling, stateless vs stateful, sharding, partitioning, read replicas, caching layers.

**Step 2: Write `reliability-and-availability.md`**

Covers: SLA/SLO/SLI, fault tolerance, circuit breakers, bulkheads, retries with backoff, chaos engineering.

**Step 3: Write `distributed-systems.md`**

Covers: CAP theorem, PACELC, eventual consistency, consensus (Raft/Paxos overview), distributed transactions (2PC, Saga).

**Step 4: Write `api-design.md`**

Covers: REST best practices, GraphQL trade-offs, gRPC, versioning strategies, API gateway pattern.

**Step 5: Write `interview-framework.md`**

Covers: step-by-step system design interview approach (clarify requirements → estimate scale → define API → high-level design → deep dive → bottlenecks).

**Step 6: Commit**

```bash
git add 03-system-design/
git commit -m "docs: add system design section"
```

---

### Task 5: Architecture Patterns section

**Files:**
- Create: `04-architecture-patterns/layered.md`
- Create: `04-architecture-patterns/hexagonal.md`
- Create: `04-architecture-patterns/microservices.md`
- Create: `04-architecture-patterns/event-driven.md`
- Create: `04-architecture-patterns/serverless.md`
- Create: `04-architecture-patterns/comparison.md`
- Modify: `04-architecture-patterns/README.md`

**Step 1: Write each pattern file**

Each file covers: definition, diagram description, pros/cons, when to use, real-world examples.

**Step 2: Write `comparison.md`**

A decision matrix: which pattern fits which problem.

**Step 3: Commit**

```bash
git add 04-architecture-patterns/
git commit -m "docs: add architecture patterns section"
```

---

### Task 6: Data section

**Files:**
- Create: `05-data/sql-vs-nosql.md`
- Create: `05-data/caching.md`
- Create: `05-data/messaging.md`
- Create: `05-data/data-modeling.md`
- Modify: `05-data/README.md`

**Step 1: Write `sql-vs-nosql.md`**

Covers: relational DBs, document, key-value, column-family, graph DBs — with trade-offs and use cases.

**Step 2: Write `caching.md`**

Covers: cache-aside, read-through, write-through, write-behind, eviction policies, Redis vs Memcached.

**Step 3: Write `messaging.md`**

Covers: message queues vs event streaming, Kafka vs RabbitMQ vs SQS, at-least-once vs exactly-once delivery.

**Step 4: Write `data-modeling.md`**

Covers: normalization, denormalization, CQRS, event sourcing.

**Step 5: Commit**

```bash
git add 05-data/
git commit -m "docs: add data section"
```

---

### Task 7: DevOps & Infrastructure section

**Files:**
- Create: `06-devops-infrastructure/ci-cd.md`
- Create: `06-devops-infrastructure/containers-and-orchestration.md`
- Create: `06-devops-infrastructure/cloud-fundamentals.md`
- Create: `06-devops-infrastructure/observability.md`
- Modify: `06-devops-infrastructure/README.md`

**Step 1: Write each file**

- `ci-cd.md`: pipelines, trunk-based dev, feature flags, blue/green, canary deployments
- `containers-and-orchestration.md`: Docker, Kubernetes core concepts (pod, service, ingress, HPA)
- `cloud-fundamentals.md`: IaaS/PaaS/SaaS, managed services mindset, cost optimization
- `observability.md`: metrics, logs, traces (the three pillars), alerting, SRE practices

**Step 2: Commit**

```bash
git add 06-devops-infrastructure/
git commit -m "docs: add devops and infrastructure section"
```

---

### Task 8: Soft Skills section

**Files:**
- Create: `07-soft-skills/trade-off-analysis.md`
- Create: `07-soft-skills/architecture-decision-records.md`
- Create: `07-soft-skills/communication.md`
- Create: `07-soft-skills/tech-radar.md`
- Modify: `07-soft-skills/README.md`

**Step 1: Write each file**

- `trade-off-analysis.md`: framework for evaluating build vs buy, consistency vs availability, etc.
- `architecture-decision-records.md`: ADR template and examples
- `communication.md`: presenting to stakeholders, writing RFCs, running design reviews
- `tech-radar.md`: how to evaluate and adopt/retire technologies

**Step 2: Commit**

```bash
git add 07-soft-skills/
git commit -m "docs: add soft skills section"
```

---

### Task 9: Case Studies section

**Files:**
- Create: `08-case-studies/url-shortener.md`
- Create: `08-case-studies/twitter-feed.md`
- Create: `08-case-studies/ride-sharing.md`
- Create: `08-case-studies/video-streaming.md`
- Modify: `08-case-studies/README.md`

**Step 1: Write each case study**

Each file follows: requirements → scale estimation → API design → high-level design → component deep dive → trade-offs → summary.

**Step 2: Commit**

```bash
git add 08-case-studies/
git commit -m "docs: add case studies section"
```

---

### Task 10: Final polish

**Files:**
- Modify: `README.md` — add progress badges, reading order recommendation, how to contribute
- Create: `.gitignore` — `*.DS_Store`, `Thumbs.db`

**Step 1: Update root README with reading order**

Recommended path: Fundamentals → Design Patterns → System Design → Architecture Patterns → Data → DevOps → Soft Skills → Case Studies

**Step 2: Final commit**

```bash
git add .
git commit -m "docs: finalize root README and add gitignore"
```
