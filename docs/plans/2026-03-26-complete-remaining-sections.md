# Complete Remaining Sections — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write all remaining topic files for sections 03–08 and apply final polish to complete the Road to Software Architect knowledge base.

**Architecture:** Each topic file is a self-contained markdown document following the established style: theory → tables/comparisons → code/pseudocode → real-world examples → "Key Architect Takeaways". No build tools. Pure markdown.

**Tech Stack:** Markdown, Git.

**Status at plan creation:**
- ✅ Task 1: Scaffold (done)
- ✅ Task 2: Fundamentals — 4 files, ~6,000 lines (done)
- ✅ Task 3: Design Patterns — 4 files, ~943 lines (done)
- ⬜ Tasks 4–10: Sections 03–08 + polish (this plan)

---

## Content Style Reference

Before writing, read one existing file to calibrate style:
- Deep fundamentals style (1,400–1,530 lines): `01-fundamentals/networking.md`
- Summary/patterns style (200–330 lines): `02-design-patterns/creational-patterns.md`

**Rules to follow for every file:**
1. Use tables for comparisons and decision matrices — never bullet-point what a table can express.
2. Use Python pseudocode blocks for any algorithm, flow, or data structure example.
3. End every H2 section or major topic group with a "Key Architect Takeaways" block (3–5 bullet points).
4. Write from the architect's perspective: trade-offs, when to use, what breaks at scale.
5. Fundamentals-style depth (aim ≥800 lines per file) for sections 03–06; shorter (300–500 lines) for 07 and 08 case study intros.
6. Case studies (section 08) follow a fixed structure: Requirements → Scale Estimation → API Design → High-Level Design → Component Deep Dive → Trade-offs → Summary.

---

## Task 4: Section 03 — System Design

**Files:**
- Create: `03-system-design/scalability.md`
- Create: `03-system-design/reliability-and-availability.md`
- Create: `03-system-design/distributed-systems.md`
- Create: `03-system-design/api-design.md`
- Create: `03-system-design/interview-framework.md`
- Modify: `03-system-design/README.md`

---

### Task 4a: Write `03-system-design/scalability.md`

**Section headings to include (in order):**

```markdown
# Scalability

## What is Scalability?
- Definition, scalability vs performance
- Vertical scaling (scale up): limits, cost curve, SPOF risk
- Horizontal scaling (scale out): stateless requirement, coordination overhead

## Stateless vs Stateful Services
- Why stateless services scale trivially
- Where state must live (DB, cache, external session store)
- Table: stateless vs stateful trade-offs

## Load Balancing
- L4 vs L7 load balancers (reference networking.md, expand on algorithms)
- Algorithms: Round Robin, Least Connections, IP Hash, Consistent Hashing
- Health checks, connection draining
- Table: algorithm trade-offs

## Database Scaling
- Read replicas: eventual consistency lag, read-your-own-writes problem
- Sharding (horizontal partitioning): by range, hash, directory
- Shard key choice pitfalls: hotspots, cross-shard joins, rebalancing
- Vertical partitioning (splitting columns across tables)
- Table: sharding strategies comparison

## Caching Layers
(Brief introduction — full detail in 05-data/caching.md)
- Where caches live: client, CDN, reverse proxy, application, DB query cache
- What to cache: expensive queries, session tokens, static assets
- What NOT to cache: highly dynamic or security-sensitive data

## Auto-Scaling
- Reactive vs predictive scaling
- Scale-in safety: connection draining, in-flight request completion
- Metrics to trigger on: CPU, RPS, queue depth, custom business metrics

## Capacity Planning
- Back-of-envelope estimation approach
- Traffic pattern analysis (peak-to-average ratio)
- Reference latency numbers table (from algorithms-complexity.md)

## Key Architect Takeaways
```

**Step 1: Write the file** — Follow section headings above. Use tables for comparisons. Target ≥800 lines.

**Step 2: Commit**

```bash
git add 03-system-design/scalability.md
git commit -m "docs: add scalability topic"
```

---

### Task 4b: Write `03-system-design/reliability-and-availability.md`

**Section headings to include (in order):**

```markdown
# Reliability & Availability

## Definitions and Metrics
- Reliability vs availability vs durability (distinct concepts)
- SLA, SLO, SLI — definitions and the hierarchy
- Table: SLO → downtime per year (99%, 99.9%, 99.99%, 99.999%)
- Error budget: what it is, how teams use it

## Failure Modes
- Hardware failure, software bugs, dependency failures, human error, cascading failures
- SPOF identification: where is the single point of failure?
- Mean Time To Failure (MTTF), Mean Time To Repair (MTTR), Mean Time Between Failures (MTBF)

## Redundancy Strategies
- Active-active vs active-passive
- Geographic redundancy: multi-region, multi-AZ
- Data replication: synchronous vs asynchronous trade-offs

## Fault Tolerance Patterns
- Circuit Breaker: closed → open → half-open state machine, pseudocode
- Bulkhead: isolate failure domains (thread pool isolation, service mesh)
- Timeout: why every external call must have one; cascading failure without it
- Retry with Exponential Backoff + Jitter: pseudocode, avoiding thundering herd
- Fallback: degraded mode, static response, cached stale data
- Table: pattern, problem it solves, trade-off

## Graceful Degradation
- Non-essential features fail silently (feature flags)
- Example: product page loads without personalization recommendations

## Chaos Engineering
- Principle: inject failure intentionally to find weaknesses
- GameDay exercises, Chaos Monkey origin
- What to test: node failures, network partitions, latency injection, dependency blackholing

## Disaster Recovery
- RTO (Recovery Time Objective) vs RPO (Recovery Point Objective)
- Backup strategies: full, incremental, snapshot
- DR strategies: Pilot Light, Warm Standby, Hot Standby, Multi-Site Active-Active
- Table: DR strategy → RTO → RPO → cost

## Key Architect Takeaways
```

**Step 1: Write the file** — Follow section headings above. Include pseudocode for circuit breaker and retry patterns. Target ≥800 lines.

**Step 2: Commit**

```bash
git add 03-system-design/reliability-and-availability.md
git commit -m "docs: add reliability and availability topic"
```

---

### Task 4c: Write `03-system-design/distributed-systems.md`

**Section headings to include (in order):**

```markdown
# Distributed Systems

## Why Distributed Systems Are Hard
- Fallacies of distributed computing (Deutsch's 8 fallacies)
- Partial failures — neither up nor down
- No shared clock: clock skew, logical clocks vs wall clocks

## CAP Theorem
- Consistency, Availability, Partition Tolerance — only 2 of 3
- Why P is not optional in real networks
- CP systems (HBase, ZooKeeper, etcd) vs AP systems (Cassandra, DynamoDB, CouchDB)
- Table: system → CAP classification → use case
- PACELC extension: latency vs consistency tradeoff during normal operation

## Consistency Models
- Strong consistency (linearizability): what it guarantees, cost
- Eventual consistency: what "eventually" means, convergence
- Causal consistency, read-your-own-writes, monotonic reads
- Table: model → guarantee → example system

## Data Replication
- Leader-based replication: single-leader, multi-leader, leaderless
- Replication lag and the read-replica consistency problem
- Quorum reads/writes: N replicas, W writes, R reads, R+W > N

## Consensus Algorithms
- Why consensus is needed: leader election, distributed locks, atomic commit
- Raft overview: leader election, log replication, safety properties (no detailed math)
- Paxos (brief): why it exists, why Raft is preferred for understandability
- etcd and ZooKeeper as consensus-as-a-service

## Distributed Transactions
- The problem: atomic writes across multiple services/databases
- Two-Phase Commit (2PC): coordinator, prepare, commit, blocking failure mode
- Saga Pattern: choreography vs orchestration, compensating transactions, pseudocode
- Table: 2PC vs Saga → guarantees → failure modes → use cases

## Clocks and Ordering
- Lamport timestamps: logical clock, happens-before relation
- Vector clocks: detect concurrent events, conflict resolution
- When to use each

## Distributed Coordination Primitives
- Distributed lock: use case, lease-based approach, dangers of holding locks across failures
- Leader election: use ZooKeeper / etcd, avoid rolling your own
- Service discovery: client-side vs server-side, health registration

## Key Architect Takeaways
```

**Step 1: Write the file** — Include pseudocode for Saga orchestrator and quorum calculation. Target ≥900 lines.

**Step 2: Commit**

```bash
git add 03-system-design/distributed-systems.md
git commit -m "docs: add distributed systems topic"
```

---

### Task 4d: Write `03-system-design/api-design.md`

**Section headings to include (in order):**

```markdown
# API Design

## REST Principles
- Resource-oriented design: URLs as nouns, verbs as HTTP methods
- Idempotency: GET, PUT, DELETE are idempotent; POST is not
- Statelessness: no server-side session, auth token in every request
- Table: HTTP methods → semantics → idempotent → safe

## REST Best Practices
- URL naming conventions: plural nouns, no verbs, hierarchical resources
- HTTP status code usage: 2xx, 3xx, 4xx, 5xx — common codes and when to use
- Pagination: offset/limit vs cursor-based; why cursor is better at scale
- Filtering, sorting, field selection (sparse fieldsets)
- HATEOAS: what it is, when it matters, when to skip it
- Versioning: URL path (/v1/), header, query param — trade-offs table

## Error Response Design
- Consistent error envelope: code, message, details, requestId
- Example error response JSON
- Error code strategy: machine-readable codes vs HTTP status only

## GraphQL
- What it is: schema, query, mutation, subscription
- When to use: flexible frontends, multiple clients with different data needs
- Trade-offs: N+1 problem, DataLoader pattern, schema complexity, caching difficulty
- Table: REST vs GraphQL → use case fit

## gRPC
- Protocol Buffers: schema-first, binary serialization, code generation
- Streaming: unary, server-streaming, client-streaming, bidirectional
- When to use: internal microservice communication, high-throughput, polyglot environments
- Table: REST vs GraphQL vs gRPC → protocol → strengths → weaknesses

## API Gateway Pattern
- Responsibilities: routing, auth, rate limiting, SSL termination, request/response transformation
- API Gateway vs Service Mesh (different layers)
- BFF (Backend for Frontend) pattern: why one API gateway doesn't fit all clients

## Rate Limiting
- Algorithms: Fixed Window, Sliding Window Log, Sliding Window Counter, Token Bucket, Leaky Bucket
- Where to enforce: API gateway, application layer, per-user vs per-IP vs per-endpoint
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After

## API Security
- Authentication: API keys, OAuth2 Bearer, mTLS
- Authorization: scopes, RBAC at the API layer
- Input validation, schema enforcement
- CORS: what it is, how to configure correctly

## Key Architect Takeaways
```

**Step 1: Write the file** — Include example JSON for REST responses and error envelopes. Target ≥800 lines.

**Step 2: Commit**

```bash
git add 03-system-design/api-design.md
git commit -m "docs: add API design topic"
```

---

### Task 4e: Write `03-system-design/interview-framework.md`

**Section headings to include (in order):**

```markdown
# System Design Interview Framework

## Overview
- Purpose: structured approach to open-ended design questions
- Interviewers evaluate: requirements clarification, estimation, trade-off reasoning, depth
- Common mistakes: jumping to solutions, ignoring scale, under-communicating

## Step 1 — Clarify Requirements (5 min)
- Functional requirements: what the system must do (core user flows)
- Non-functional requirements: scale, latency, availability, consistency, cost
- Out of scope: explicitly name what you are NOT designing
- Questions checklist: users? traffic? read/write ratio? geo distribution? data size? SLA?

## Step 2 — Estimate Scale (3–5 min)
- Back-of-envelope: QPS, storage, bandwidth, cache memory
- Example: Twitter Feed estimation walkthrough (users, tweets/day, storage/tweet, total storage/year)
- Reference numbers table (from algorithms-complexity.md): latency, throughput, storage units

## Step 3 — Define API (5 min)
- Write 3–5 key API endpoints
- Focus on the most important flows only
- Decide on protocol (REST/gRPC) and explain why

## Step 4 — High-Level Design (10 min)
- Draw the major components: client, API gateway/load balancer, services, databases, cache, message queue
- Data flow for the primary use case
- Identify the core data model (key entities, relationships)

## Step 5 — Deep Dive (15–20 min)
- Pick 2–3 most interesting/hardest components and go deep
- Ask interviewer which area they want to explore
- Typical deep dives: database sharding, caching strategy, feed generation, search, consistency model

## Step 6 — Identify Bottlenecks and Trade-offs (5 min)
- What are the scaling limits of your design?
- What would you do differently for 10x traffic?
- Consistency vs availability trade-off in your design
- What monitoring/alerting would you set up?

## Common System Design Topics Table
| System | Key Challenges | Key Patterns |
|--------|---------------|--------------|
| URL Shortener | unique ID generation, redirect at scale | Base62 encoding, consistent hashing |
| Social Feed | fan-out on write vs read, hot celebrities | Hybrid push/pull, cache pre-warming |
| Ride Sharing | real-time location, geospatial queries | WebSockets, geohashing, matching service |
| Video Streaming | storage, encoding, global delivery | CDN, adaptive bitrate, chunked upload |
| Search Engine | indexing, ranking, low latency | Inverted index, TF-IDF, distributed search |
| Rate Limiter | distributed counter, accuracy | Token bucket, Redis atomic increment |
| Notification System | fan-out, delivery guarantees | Message queue, push vs pull, dedupe |

## Communication Tips
- Think out loud: narrate your reasoning
- Acknowledge trade-offs explicitly: "This approach has the advantage of X but costs Y"
- Quantify: use numbers, not just "it's faster"
- Drive the interview: propose the next area to explore

## Key Architect Takeaways
```

**Step 1: Write the file** — Include worked estimation example for Twitter feed. Target ~500 lines.

**Step 2: Update `03-system-design/README.md`** — Mark all topics as complete `[x]`.

**Step 3: Commit**

```bash
git add 03-system-design/
git commit -m "docs: add system design section"
```

---

## Task 5: Section 04 — Architecture Patterns

**Files:**
- Create: `04-architecture-patterns/layered.md`
- Create: `04-architecture-patterns/hexagonal.md`
- Create: `04-architecture-patterns/microservices.md`
- Create: `04-architecture-patterns/event-driven.md`
- Create: `04-architecture-patterns/serverless.md`
- Create: `04-architecture-patterns/comparison.md`
- Modify: `04-architecture-patterns/README.md`

---

### Task 5a: Write `04-architecture-patterns/layered.md`

**Section headings to include:**

```markdown
# Layered Architecture

## Intent
## The Classic N-Tier Model
- Presentation → Business Logic → Data Access → Database
- Layer responsibilities and rules (layers only call down, never up)
- Table: layer → responsibility → example technology

## Separation of Concerns
- Why layers exist: isolation of change, testability, replaceability
- Layer coupling vs cohesion

## Variations
- 3-tier vs 4-tier vs N-tier
- Strict vs relaxed layering

## Pros and Cons
- Table: advantage → explanation | disadvantage → explanation

## When to Use / When to Avoid
## Real-World Examples
## Key Architect Takeaways
```

**Target:** ~300 lines.

---

### Task 5b: Write `04-architecture-patterns/hexagonal.md`

**Section headings to include:**

```markdown
# Hexagonal Architecture (Ports & Adapters)

## Intent
## The Core Idea
- Domain at the center, infrastructure at the edges
- Ports: interfaces defined by the domain
- Adapters: implementations that plug into ports
- Primary (driving) vs Secondary (driven) ports

## Diagram Description
- ASCII or text description of the hexagon with domain core, primary ports (REST, CLI), secondary ports (DB, messaging, email)

## Implementation Example
- Python pseudocode: Port interface, Adapter implementation, Domain using only the port

## Dependency Inversion
- How hexagonal enforces DIP: domain defines the interface, infrastructure implements it
- Inversion of Control container role

## Pros and Cons Table
## When to Use / When to Avoid
## Real-World Examples
## Key Architect Takeaways
```

**Target:** ~350 lines.

---

### Task 5c: Write `04-architecture-patterns/microservices.md`

**Section headings to include:**

```markdown
# Microservices Architecture

## What Are Microservices?
- Definition: bounded by business capability, independently deployable, owned by one team
- Contrasted with monolith and SOA
- Conway's Law: architecture mirrors communication structure

## Decomposition Strategies
- By business capability
- By subdomain (Domain-Driven Design: bounded contexts, aggregates)
- Strangler Fig pattern: migrating from monolith incrementally

## Service Communication
- Synchronous: REST, gRPC — when to use, coupling risk
- Asynchronous: message queues/event bus — decoupling, eventual consistency
- Service discovery: client-side vs server-side

## Data Management
- Database-per-service rule: why shared databases break autonomy
- Distributed transactions problem → Saga pattern
- Data consistency trade-offs: eventual vs strong

## Cross-Cutting Concerns
- API Gateway: single entry point, auth, rate limiting, routing
- Service Mesh (Istio/Linkerd): mTLS, observability, traffic management — sidecar proxy model
- Centralized logging and tracing: correlating across services (trace ID)

## Organizational Considerations
- Team autonomy and ownership
- On-call responsibilities: you build it, you run it
- Independent deployment pipeline per service

## Common Pitfalls
- Distributed monolith: tightly coupled services that must deploy together
- Too fine-grained: network calls where function calls were fine
- Shared libraries as hidden coupling

## Pros and Cons Table
## When to Use / When to Avoid (includes: monolith-first recommendation)
## Key Architect Takeaways
```

**Target:** ~500 lines.

---

### Task 5d: Write `04-architecture-patterns/event-driven.md`

**Section headings to include:**

```markdown
# Event-Driven Architecture

## Core Concepts
- Event: immutable record of something that happened
- Event Producer → Event Broker → Event Consumer
- Decoupling: producers don't know consumers exist

## Event Types
- Domain Events: business facts (OrderPlaced, PaymentProcessed)
- Integration Events: cross-service notifications
- Commands vs Events distinction: command = intent, event = fact

## Patterns
- Event Notification: fire-and-forget, consumer fetches details
- Event-Carried State Transfer: event contains full payload, consumer is self-sufficient
- Event Sourcing: system state = replay of all events (see 05-data/data-modeling.md)
- CQRS (Command Query Responsibility Segregation) — often paired with EDA

## Message Brokers
- Kafka: durable log, replay, high throughput, consumer groups
- RabbitMQ: flexible routing, push model, lower throughput
- AWS SQS/SNS: managed, fan-out
- Table: broker → durability → ordering → use case

## Delivery Guarantees
- At-most-once, at-least-once, exactly-once — what each means in practice
- Idempotency: handling duplicate events safely
- Deduplication key strategy

## Ordering Guarantees
- Total ordering vs partition-level ordering (Kafka)
- When ordering matters (payment events) vs when it doesn't (metrics)

## Pros and Cons Table
## When to Use / When to Avoid
## Key Architect Takeaways
```

**Target:** ~400 lines.

---

### Task 5e: Write `04-architecture-patterns/serverless.md`

**Section headings to include:**

```markdown
# Serverless Architecture

## What is Serverless?
- Functions as a Service (FaaS): AWS Lambda, Google Cloud Functions, Azure Functions
- BaaS: managed databases, auth, storage (not writing your own backend services)
- Pay-per-invocation, automatic scaling to zero

## Execution Model
- Cold start vs warm start — latency impact
- Execution time limits: why long-running tasks are not a fit
- Stateless by design: no local state between invocations

## When Serverless Fits
- Event-driven workloads: file processing, webhooks, scheduled jobs
- Unpredictable or spiky traffic: scale to zero when idle
- Glue code and automation: not the hot path of a high-traffic service

## Patterns
- Fan-out: one event → trigger multiple functions in parallel
- Step Functions / orchestration: chaining functions for complex workflows
- Saga with serverless: orchestrating distributed transactions

## Operational Model
- Observability challenges: distributed traces across functions, cold start attribution
- Vendor lock-in: function signatures, event formats differ between clouds
- Cost model: compute vs reserved capacity at sustained high throughput

## Pros and Cons Table
## When to Use / When to Avoid
## Key Architect Takeaways
```

**Target:** ~300 lines.

---

### Task 5f: Write `04-architecture-patterns/comparison.md`

**Section headings to include:**

```markdown
# Architecture Pattern Comparison

## Decision Matrix
- Table: Pattern → Team Size → Deployment Complexity → Data Consistency → Latency → Scalability → When to Start Here

## Monolith (baseline, for comparison)
## Migration Paths
- Monolith → Modular Monolith → Microservices (Strangler Fig)
- When NOT to migrate: premature decomposition costs

## Pattern Selection Flowchart (text description)
- Is your team small? → Monolith/Modular Monolith
- Do you need independent deployment? → Microservices
- Do you have event-driven workflows? → EDA
- Do you have unpredictable spiky traffic? → Serverless
- Do you value testability and domain purity? → Hexagonal

## Combining Patterns
- Hexagonal + Microservices: each service uses hexagonal internally
- EDA + Microservices: services communicate via events
- Serverless + EDA: functions triggered by events

## Key Architect Takeaways
```

**Target:** ~300 lines.

**Step 1: Write all 6 files** (Tasks 5a–5f above), one at a time.

**Step 2: Update `04-architecture-patterns/README.md`** — mark all topics `[x]`.

**Step 3: Commit**

```bash
git add 04-architecture-patterns/
git commit -m "docs: add architecture patterns section"
```

---

## Task 6: Section 05 — Data

**Files:**
- Create: `05-data/sql-vs-nosql.md`
- Create: `05-data/caching.md`
- Create: `05-data/messaging.md`
- Create: `05-data/data-modeling.md`
- Modify: `05-data/README.md`

---

### Task 6a: Write `05-data/sql-vs-nosql.md`

**Section headings to include:**

```markdown
# SQL vs NoSQL

## Relational Databases (SQL)
- ACID properties: Atomicity, Consistency, Isolation, Durability — what each means
- Schema-on-write: strict schema, migration discipline
- Joins: power and cost at scale
- Transactions: multi-row atomic operations
- Indexing: B-tree, covering index, index scan vs seq scan
- Examples: PostgreSQL, MySQL, Aurora

## NoSQL Database Types
### Key-Value Stores
- Data model, access pattern (only by key)
- Use cases: session store, caching, shopping cart
- Examples: Redis, DynamoDB

### Document Stores
- JSON/BSON documents, flexible schema, nested data
- When embedding vs referencing: 1:1 and 1:few embed, 1:many reference
- Use cases: user profiles, product catalogs, CMS
- Examples: MongoDB, Firestore

### Column-Family Stores
- Wide-column model: rows have variable columns grouped into column families
- Write-optimized, time-series data, high ingest
- Use cases: analytics, IoT, activity feeds
- Examples: Apache Cassandra, HBase, Google Bigtable

### Graph Databases
- Nodes, edges, properties
- When relationships ARE the data
- Use cases: social graph, fraud detection, recommendation engine
- Examples: Neo4j, Amazon Neptune

### Time-Series Databases
- Optimized for append-only, time-ordered data with retention policies
- Use cases: metrics, monitoring, IoT sensor data
- Examples: InfluxDB, TimescaleDB, Prometheus

## Decision Matrix
- Table: Requirement → Best DB Type → Examples

## Scaling Comparison
- SQL horizontal scaling challenges (sharding complexity, cross-shard joins)
- NoSQL designed-for-scale trade-offs (limited query flexibility)

## NewSQL
- Attempt to get ACID + horizontal scale
- Examples: CockroachDB, Google Spanner, TiDB

## When to Use What
- Start with PostgreSQL (proven, flexible, underrated NoSQL capabilities via JSONB)
- Reach for NoSQL when: specific access pattern, horizontal scale mandate, schema flexibility needed

## Key Architect Takeaways
```

**Target:** ≥800 lines.

---

### Task 6b: Write `05-data/caching.md`

**Section headings to include:**

```markdown
# Caching

## Why Cache?
- Latency numbers: cache hit vs DB query (reference algorithms-complexity.md latency table)
- Reduce DB load, improve throughput, handle traffic spikes

## Cache Placement
- Client-side cache (browser, app local)
- CDN cache (static assets, API responses with Cache-Control)
- Reverse proxy cache (Nginx, Varnish)
- Application cache (in-process, in-memory: HashMap, LRU)
- Distributed cache (Redis, Memcached)
- Database query cache (limited, often disabled)

## Caching Strategies
### Cache-Aside (Lazy Loading)
- Flow: read → cache miss → read DB → populate cache → return
- Python pseudocode
- Pros: only caches what's requested; Cons: cache miss latency, potential thundering herd

### Read-Through
- Cache sits in front of DB, auto-populates on miss
- Good for read-heavy workloads

### Write-Through
- Write to cache and DB synchronously
- High write latency, but cache always consistent

### Write-Behind (Write-Back)
- Write to cache, async flush to DB
- Low write latency, risk of data loss on cache failure

### Refresh-Ahead
- Proactively refresh before expiry based on predicted access

- Table: strategy → consistency → write latency → data loss risk → best for

## Cache Invalidation
- TTL (Time To Live): simple, eventual consistency
- Event-based invalidation: write triggers cache delete
- Cache stampede / thundering herd: multiple cache misses hit DB simultaneously
  - Mitigation: probabilistic early expiration, distributed lock on cache miss

## Eviction Policies
- LRU (Least Recently Used), LFU (Least Frequently Used), FIFO, Random
- Table: policy → when to use

## Redis vs Memcached
- Table: feature comparison (data structures, persistence, replication, cluster, pub/sub)
- When to choose each

## Cache Consistency Patterns
- Cache invalidation on write: delete vs update cache entry
- Two-phase invalidation in distributed systems
- Read-your-own-writes with cache

## What Not to Cache
- Highly personalized data (per-user, per-request unique)
- Security-sensitive data (auth tokens beyond TTL)
- Data that changes every request

## Key Architect Takeaways
```

**Target:** ≥800 lines.

---

### Task 6c: Write `05-data/messaging.md`

**Section headings to include:**

```markdown
# Messaging

## Why Messaging?
- Decoupling: producer and consumer don't need to be available simultaneously
- Buffering: handle traffic spikes, smooth load
- Parallelism: multiple consumers process concurrently

## Message Queues vs Event Streams
- Table: dimension → message queue → event stream
- Queue: message consumed and deleted; Stream: retained log, replayable

## Core Concepts
- Producer, Consumer, Topic/Queue, Broker
- Consumer Group: horizontal scaling, each message to one consumer in group (Kafka)
- Fan-out: each subscriber gets a copy (SNS, pub/sub)
- Dead Letter Queue (DLQ): messages that fail repeatedly, inspect and reprocess

## Delivery Guarantees
- At-most-once: fire-and-forget, possible message loss
- At-least-once: acknowledge after processing, possible duplicates
- Exactly-once: hardest, requires idempotent consumers + broker support
- Idempotency implementation: idempotency key, dedupe table, upsert semantics

## Apache Kafka Deep Dive
- Log-structured storage: partitions, offsets
- Consumer group: partition assigned to one consumer per group
- Ordering: guaranteed within a partition, not across
- Retention: time-based or size-based, replay capability
- Compaction: keep only latest value per key
- Use cases: event sourcing, CDC (Change Data Capture), analytics pipelines

## RabbitMQ
- Exchange types: direct, topic, fanout, headers
- Acknowledgment modes: auto-ack, manual-ack
- Priority queues, delayed messages, DLX (Dead Letter Exchange)
- Use cases: task queues, RPC, workflow routing

## Cloud Managed Services
- AWS SQS: standard (at-least-once) vs FIFO (exactly-once, limited throughput)
- AWS SNS + SQS: fan-out pattern
- Google Pub/Sub, Azure Service Bus

- Table: broker → delivery guarantee → ordering → throughput → replay → use case

## Backpressure and Flow Control
- What happens when consumers are slower than producers
- Solutions: queue depth monitoring, autoscaling consumers, circuit breaker at producer

## Schema Management
- Why schema matters: producer and consumer evolve independently
- Schema Registry (Confluent): Avro, Protobuf, JSON Schema
- Backward/forward compatibility rules

## Key Architect Takeaways
```

**Target:** ≥800 lines.

---

### Task 6d: Write `05-data/data-modeling.md`

**Section headings to include:**

```markdown
# Data Modeling

## Relational Modeling
- Normalization: 1NF, 2NF, 3NF — what each eliminates
- Denormalization: when to trade storage for read speed
- Entity-Relationship (ER) model: entities, relationships, cardinality
- Foreign keys and referential integrity

## NoSQL Data Modeling Principles
- Model for your access patterns, not your entities
- Embed vs reference: rules of thumb (MongoDB)
- Partition key design in Cassandra/DynamoDB: avoid hot partitions
- Single-table design (DynamoDB): one table, multiple entity types, composite sort key

## CQRS — Command Query Responsibility Segregation
- Separate read model (query side) from write model (command side)
- Why: optimize read and write schemas independently
- Implementation: sync via events, separate databases
- When to use: high read/write imbalance, complex domain, reporting requirements

## Event Sourcing
- State = ordered log of events, never update-in-place
- Aggregate root: apply events to reconstruct current state
- Python pseudocode: event log, apply_event, reconstruct
- Snapshots: avoid replaying all events from the beginning
- Trade-offs: query complexity (projections), eventual consistency, storage growth
- When to use: audit trail required, financial systems, collaborative editing

## Schema Evolution
- Backward compatibility: old consumer reads new schema
- Forward compatibility: new consumer reads old schema
- Strategies: nullable fields, default values, additive changes only

## Data Partitioning Strategies
- Range partitioning: ordered keys, hot at boundary (e.g., timestamp keys)
- Hash partitioning: uniform distribution, loses range queries
- List partitioning: explicit value sets (e.g., by region)
- Composite partitioning: combine strategies

## Key Architect Takeaways
```

**Target:** ≥700 lines.

**Step 1: Write all 4 files** (Tasks 6a–6d), one at a time.

**Step 2: Update `05-data/README.md`** — mark all topics `[x]`.

**Step 3: Commit**

```bash
git add 05-data/
git commit -m "docs: add data section"
```

---

## Task 7: Section 06 — DevOps & Infrastructure

**Files:**
- Create: `06-devops-infrastructure/ci-cd.md`
- Create: `06-devops-infrastructure/containers-and-orchestration.md`
- Create: `06-devops-infrastructure/cloud-fundamentals.md`
- Create: `06-devops-infrastructure/observability.md`
- Modify: `06-devops-infrastructure/README.md`

---

### Task 7a: Write `06-devops-infrastructure/ci-cd.md`

**Section headings to include:**

```markdown
# CI/CD

## What is CI/CD?
- Continuous Integration: merge often, build and test on every commit
- Continuous Delivery: every build is releasable; deploy on demand
- Continuous Deployment: every passing build deploys to production automatically
- Table: CI vs CD vs Continuous Deployment

## Pipeline Stages
- Lint → Unit Tests → Build → Integration Tests → Security Scan → Deploy to Staging → E2E Tests → Deploy to Production
- Fast feedback principle: fail early, fail fast

## Branching Strategies
- Trunk-Based Development: short-lived branches, merge to trunk daily
- GitFlow: release branches, feature branches — when it fits, when it's overhead
- Feature flags: decouple deploy from release, enable trunk-based dev

## Deployment Strategies
- Blue/Green: two identical environments, instant cutover, easy rollback
- Canary: gradual traffic shift (1% → 10% → 100%), monitor error rate
- Rolling: replace instances one at a time
- Table: strategy → rollback speed → blast radius → infra cost

## Infrastructure as Code (IaC)
- Terraform: declarative, provider-agnostic, state management
- Pulumi, AWS CDK: programmatic IaC
- GitOps: Git as source of truth for infrastructure state

## Pipeline Tools Overview
- GitHub Actions, GitLab CI, Jenkins, CircleCI, ArgoCD (GitOps)
- Table: tool → hosting → strengths → weaknesses

## Testing in Pipelines
- Unit tests: fast, run every commit
- Integration tests: test service contracts, run on PR merge
- E2E tests: slow, run before production deploy
- Smoke tests: run after every deployment to verify basic health

## Key Architect Takeaways
```

**Target:** ~500 lines.

---

### Task 7b: Write `06-devops-infrastructure/containers-and-orchestration.md`

**Section headings to include:**

```markdown
# Containers & Orchestration

## Containers
- What a container is: isolated process with its own filesystem, network, PID namespace
- Container vs VM: shared kernel, startup time, density
- Docker: image layers, Dockerfile, registry, build/run/push lifecycle

## Dockerfile Best Practices
- Multi-stage builds: builder stage + minimal runtime image
- Layer caching: order instructions from least to most frequently changed
- Non-root user: security hardening
- Example: multi-stage Python app Dockerfile

## Kubernetes Core Concepts
- Pod: smallest deployable unit, one or more containers, shared network
- Deployment: desired state, rolling updates, replica count
- Service: stable DNS + load balancing across pods (ClusterIP, NodePort, LoadBalancer)
- Ingress: HTTP routing, TLS termination, path-based routing
- ConfigMap & Secret: configuration injection without rebuilding images
- Namespace: logical cluster partition

## Kubernetes Workload Patterns
- Deployment: stateless services
- StatefulSet: ordered pods with stable identities (databases)
- DaemonSet: one pod per node (log agents, monitoring)
- Job / CronJob: batch and scheduled work

## Scaling in Kubernetes
- Horizontal Pod Autoscaler (HPA): scale pods based on CPU/memory/custom metrics
- Vertical Pod Autoscaler (VPA): right-size resource requests
- Cluster Autoscaler: add/remove nodes based on pending pods

## Observability in K8s
- Readiness probe: is the pod ready to receive traffic?
- Liveness probe: should the pod be restarted?
- Startup probe: for slow-starting containers

## Service Mesh Overview
- Sidecar proxy (Envoy), mTLS, traffic management, circuit breaking at infrastructure layer
- Istio, Linkerd — when complexity is justified

## Key Architect Takeaways
```

**Target:** ~500 lines.

---

### Task 7c: Write `06-devops-infrastructure/cloud-fundamentals.md`

**Section headings to include:**

```markdown
# Cloud Fundamentals

## Service Models
- IaaS: you manage OS and above (EC2, GCE)
- PaaS: you manage app and data (App Engine, Elastic Beanstalk, Heroku)
- SaaS: vendor manages everything (Gmail, Salesforce)
- FaaS/Serverless: event-driven compute (Lambda, Cloud Functions)
- Table: model → you manage → vendor manages → example

## Core Cloud Building Blocks
- Compute: VMs, containers, serverless functions
- Storage: object (S3), block (EBS), file (EFS/NFS), archive (Glacier)
- Networking: VPC, subnets, security groups, routing tables, NAT gateway
- Database: managed SQL (RDS), managed NoSQL (DynamoDB), managed cache (ElastiCache)
- Table: building block → AWS → GCP → Azure

## Networking in the Cloud
- VPC: virtual isolated network, CIDR block allocation
- Public vs private subnets: internet-facing vs internal services
- Security Groups: stateful firewall at the instance level
- NACLs: stateless firewall at the subnet level
- Peering, Transit Gateway, VPN, Direct Connect

## Managed Services Philosophy
- Buy not build: managed services reduce operational burden
- Trade-offs: vendor lock-in, less control, cost at scale
- Decision framework: operational cost vs flexibility

## Multi-Region and High Availability
- Regions and Availability Zones: physical separation
- Deploy across AZs for HA; multi-region for DR and low latency
- Global services (Route53, CloudFront, IAM) vs regional services

## Cost Optimization
- Right-sizing: don't over-provision compute
- Reserved Instances / Committed Use Discounts: for predictable baseline load
- Spot Instances / Preemptible VMs: for fault-tolerant batch workloads
- Cost allocation tags: track spend by team/project
- The biggest cost surprises: data transfer fees, NAT gateway, unattached EBS volumes

## IAM and Security Basics
- Principle of least privilege: grant minimum permissions needed
- Roles vs users: prefer roles (no long-lived credentials)
- Service accounts for applications
- Avoid embedding credentials in code (use secrets manager, IAM roles)

## Key Architect Takeaways
```

**Target:** ~500 lines.

---

### Task 7d: Write `06-devops-infrastructure/observability.md`

**Section headings to include:**

```markdown
# Observability

## The Three Pillars
- Metrics: numeric measurements over time (CPU, RPS, latency p50/p99/p999)
- Logs: discrete events with context (timestamp, level, message, structured fields)
- Traces: end-to-end request journey across services (spans, trace ID)
- Observability vs Monitoring: monitoring tells you something is wrong; observability lets you ask why

## Metrics
- Counter: cumulative, only goes up (requests total)
- Gauge: current value, can go up or down (memory used, active connections)
- Histogram: distribution of values, calculate percentiles (latency buckets)
- Summary: pre-calculated percentiles (less flexible than histogram)
- Tools: Prometheus (collection + alerting), Grafana (visualization), DataDog, CloudWatch

## The Four Golden Signals (Google SRE)
- Latency: time to serve a request (distinguish successful vs error latency)
- Traffic: demand on your system (RPS, QPS)
- Errors: rate of failed requests (5xx, timeouts, business-level errors)
- Saturation: how "full" your service is (CPU%, memory%, queue depth)

## Logging
- Structured logging: JSON over plain text (machine-readable, filterable)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL — when to use each
- What to log: request in, response out, external calls, errors with context
- What NOT to log: PII, passwords, full request bodies with sensitive data
- Correlation ID / Trace ID: include in every log line for cross-service correlation
- Tools: ELK Stack (Elasticsearch + Logstash + Kibana), Loki + Grafana, Splunk, CloudWatch Logs

## Distributed Tracing
- Span: single operation with start time, duration, metadata
- Trace: tree of spans representing a request across services
- Propagation: how trace context passes between services (HTTP headers: traceparent)
- Sampling: trace 1-5% of requests in production (full sampling is expensive)
- Tools: Jaeger, Zipkin, AWS X-Ray, Honeycomb, DataDog APM

## Alerting
- Alert on symptoms (high latency, error rate) not causes (CPU%)
- Runbook: every alert should link to a runbook
- Alert fatigue: reduce noise or engineers stop responding
- SLO-based alerting: alert when error budget burn rate is high

## SRE Practices
- Error budget: how much unreliability is acceptable per quarter
- Toil: repetitive manual work that should be automated
- Blameless postmortem: find systemic causes, not people to blame
- Table: SRE practice → purpose → artifact produced

## Key Architect Takeaways
```

**Target:** ~600 lines.

**Step 1: Write all 4 files** (Tasks 7a–7d), one at a time.

**Step 2: Update `06-devops-infrastructure/README.md`** — mark all topics `[x]`.

**Step 3: Commit**

```bash
git add 06-devops-infrastructure/
git commit -m "docs: add devops and infrastructure section"
```

---

## Task 8: Section 07 — Soft Skills

**Files:**
- Create: `07-soft-skills/trade-off-analysis.md`
- Create: `07-soft-skills/architecture-decision-records.md`
- Create: `07-soft-skills/communication.md`
- Create: `07-soft-skills/tech-radar.md`
- Modify: `07-soft-skills/README.md`

---

### Task 8a: Write `07-soft-skills/trade-off-analysis.md`

**Section headings to include:**

```markdown
# Trade-off Analysis

## Why Trade-offs Are Central to Architecture
- Architecture = maximizing options; good decisions reduce future regret
- No universally correct answer: context (team, scale, timeline, budget) determines best choice

## Common Trade-off Dimensions
- Table: dimension → typical tension (e.g., Consistency vs Availability, Build vs Buy, Simplicity vs Flexibility)

## Frameworks for Analysis

### Build vs Buy vs Open Source
- Criteria table: control, cost, time-to-value, maintenance burden, vendor lock-in

### YAGNI and Premature Generalization
- Cost of complexity: harder to change, harder to understand, harder to test
- When to add flexibility: clear evidence of multiple use cases, not speculation

### Reversibility Classification
- Two-way door decisions: experiment freely
- One-way door decisions: invest more analysis time

## Documenting Trade-offs
- Always record what was NOT chosen and why
- Future readers need to know the context, not just the decision

## Key Architect Takeaways
```

**Target:** ~300 lines.

---

### Task 8b: Write `07-soft-skills/architecture-decision-records.md`

**Section headings to include:**

```markdown
# Architecture Decision Records (ADRs)

## What Is an ADR?
- Short document capturing a significant architectural decision
- Captures: context, decision, consequences
- Immutable: once accepted, mark as superseded rather than editing

## Why ADRs Matter
- New team members understand why things are the way they are
- Prevents relitigating settled decisions
- Makes implicit decisions explicit

## ADR Format (MADR — Markdown Architectural Decision Records)

```markdown
# ADR-001: Use PostgreSQL as the primary database

## Status
Accepted

## Context
We need a primary data store for [project]. Requirements: ACID transactions,
relational model, mature tooling, team familiarity.

## Decision
We will use PostgreSQL hosted on AWS RDS.

## Consequences
- Positive: ACID guarantees, excellent JSONB support for semi-structured data,
  strong ecosystem, managed backups and failover via RDS.
- Negative: Horizontal write scaling requires sharding (not needed at current scale).
  Tight coupling to AWS if we ever need to self-host.

## Alternatives Considered
- MySQL: Similar capabilities, PostgreSQL preferred for JSONB and advanced indexing.
- MongoDB: Flexible schema, but ACID only at document level; relational model better fits our domain.
```

## ADR Workflow
- When to write: before implementing a significant decision (not after)
- Who writes: architect or tech lead; reviewed by team
- Where to store: `docs/decisions/ADR-NNN-title.md` in the repo
- How to supersede: create new ADR, link old one

## Example: Three ADRs for a Microservices Migration
- ADR-001: Adopt microservices architecture
- ADR-002: Use Kafka for inter-service events
- ADR-003: Supersede ADR-001 — consolidate to modular monolith (with context)

## Key Architect Takeaways
```

**Target:** ~300 lines.

---

### Task 8c: Write `07-soft-skills/communication.md`

**Section headings to include:**

```markdown
# Communication for Architects

## The Audience Problem
- Developers, product managers, executives, and customers need different abstractions
- C4 Model: Context → Container → Component → Code diagrams (different audiences)
- Rule: always start with the audience's concerns, not the technology

## Writing RFCs (Request for Comments)
- Purpose: structured proposal for significant technical change, invites review
- RFC template: Summary, Motivation, Detailed Design, Trade-offs, Alternatives, Unresolved Questions
- RFC lifecycle: draft → review → accepted/rejected → implementation
- Tips: be specific, link to evidence, list what you're NOT proposing

## Presenting Architecture to Stakeholders
- Executive audience: business impact, risk, cost, timeline — not technical details
- Engineering audience: trade-offs, implementation complexity, failure modes
- "Start with the end in mind": state the recommendation first, then the reasoning

## Running Design Reviews
- Purpose: surface problems early, align the team, distribute knowledge
- Attendees: author, engineers affected, at least one skeptic
- Facilitation: time-box sections, capture decisions and action items
- Common failure mode: rubber-stamp reviews (everyone agrees to be polite)

## Conflict Resolution on Technical Disagreements
- Separate the idea from the person
- Require concrete objections: "what would have to be true for this to fail?"
- When still stuck: time-box an experiment, escalate with documented trade-offs

## Writing for Asynchronous Teams
- Over-document decisions (ADRs, RFCs) — people aren't in the room
- Async-first: Slack/Teams for quick questions; Notion/Confluence/Docs for durable information

## Key Architect Takeaways
```

**Target:** ~300 lines.

---

### Task 8d: Write `07-soft-skills/tech-radar.md`

**Section headings to include:**

```markdown
# Tech Radar

## What Is a Tech Radar?
- Originated by ThoughtWorks; periodic snapshot of technology choices
- Four rings: Adopt → Trial → Assess → Hold
- Four quadrants: Techniques, Tools, Platforms, Languages & Frameworks

## The Four Rings
- Table: ring → meaning → action

## How to Build Your Team's Radar
- Start with inventory: what are you actually using?
- Rate each item: should we use more of this, try it, evaluate it, or stop using it?
- Review cadence: quarterly or biannually
- Keep it small: a radar with 200 entries is useless

## Technology Evaluation Framework
- Maturity: community size, stability, maintenance status
- Fit: does it solve your specific problem well?
- Operational cost: what does running it in production cost?
- Team capability: do you have or can you build the skills?
- Vendor risk: lock-in, pricing changes, deprecation risk

## Managing Technical Debt and Legacy Tech
- "Hold" items: actively discourage new use, plan migration
- Tech debt register: track what needs replacing and why
- Migration strategies: Strangler Fig, feature flag cutover

## Key Architect Takeaways
```

**Target:** ~250 lines.

**Step 1: Write all 4 files** (Tasks 8a–8d), one at a time.

**Step 2: Update `07-soft-skills/README.md`** — mark all topics `[x]`.

**Step 3: Commit**

```bash
git add 07-soft-skills/
git commit -m "docs: add soft skills section"
```

---

## Task 9: Section 08 — Case Studies

**Files:**
- Create: `08-case-studies/url-shortener.md`
- Create: `08-case-studies/twitter-feed.md`
- Create: `08-case-studies/ride-sharing.md`
- Create: `08-case-studies/video-streaming.md`
- Modify: `08-case-studies/README.md`

**Every case study uses this fixed structure:**

```markdown
# [System Name]

## Requirements
### Functional Requirements
### Non-Functional Requirements (Scale, Latency, Availability)
### Out of Scope

## Scale Estimation
- DAU, QPS (read and write), storage per record, total storage, bandwidth

## API Design
- 3–5 key endpoints with method, path, request/response sketch

## High-Level Design
- Component list with one-paragraph description of each
- Data flow for primary use case (numbered steps)

## Data Model
- Key tables/documents with fields and types
- Partition/shard key choice and reasoning

## Component Deep Dives
- 2–3 most interesting components with design decisions

## Trade-offs and Bottlenecks
- What breaks at 10x scale?
- Key consistency/availability decision
- Alternative approaches considered

## Summary
- Table: requirement → design decision → rationale
```

---

### Task 9a: Write `08-case-studies/url-shortener.md`

Key design challenges to address:
- Unique ID generation: Base62 encoding of auto-increment ID vs random ID vs hash
- Why not MD5/SHA hash of URL: collision handling, length
- Redirect: 301 (permanent, browser caches) vs 302 (temporary, server controls analytics)
- Read-heavy (100:1 read/write): cache aggressively (cache-aside with Redis)
- Custom aliases: uniqueness check, profanity filter
- Analytics: async event stream (click → Kafka → analytics consumer)
- Data model: URLs table (id, shortCode, originalUrl, createdAt, userId, expiresAt)
- Scale: 100M URLs, 10B redirects/month, cache hit rate target

---

### Task 9b: Write `08-case-studies/twitter-feed.md`

Key design challenges to address:
- Feed generation: fan-out on write (push) vs fan-out on read (pull) vs hybrid
- Celebrity problem: users with 100M followers break fan-out on write
- Hybrid approach: regular users → push to follower feeds; celebrities → pull at read time
- Tweet storage: relational (tweets table) + timeline storage (Redis sorted set by timestamp)
- Newsfeed cache: Redis sorted set per user, score = timestamp, top 800 tweets
- Fanout service: reads follower list, writes to each follower's timeline cache
- Data model: tweets, users, follows, media
- Non-functional: 300M DAU, 500M tweets/day, 1ms read latency target for feed

---

### Task 9c: Write `08-case-studies/ride-sharing.md`

Key design challenges to address:
- Real-time location tracking: drivers send GPS every 5s via WebSocket
- Geospatial indexing: geohash for driver location storage (Redis geospatial commands)
- Matching service: find nearest available drivers within geohash cell + neighbors
- Ride state machine: requested → driver_assigned → picked_up → in_progress → completed
- Trip pricing service: surge pricing based on supply/demand ratio by geohash cell
- WebSocket for real-time updates to rider and driver
- Data model: rides table, drivers table, location snapshot (Redis), ride events (Kafka)
- Consistency: eventual is acceptable for location; strong for payment

---

### Task 9d: Write `08-case-studies/video-streaming.md`

Key design challenges to address:
- Video upload: chunked multipart upload, resumable (client uploads chunks to object storage directly via presigned URL)
- Video processing pipeline: raw upload → transcoding service (multiple resolutions: 360p, 720p, 1080p, 4K) → CDN origin
- Adaptive bitrate streaming: HLS or DASH — player selects quality based on bandwidth
- CDN: edge nodes serve video chunks, cache-hit ratio is critical (long TTL for immutable chunks)
- Storage: raw video (object storage), processed chunks (object storage), metadata (relational DB)
- Recommendation engine: not in scope (call out as separate system)
- Like/view counter: not strongly consistent (Redis counter + async DB flush acceptable)
- Data model: videos, users, watch_history, comments

**Step 1: Write all 4 case study files** (Tasks 9a–9d), one at a time.

**Step 2: Update `08-case-studies/README.md`** — mark all topics `[x]`.

**Step 3: Commit**

```bash
git add 08-case-studies/
git commit -m "docs: add case studies section"
```

---

## Task 10: Final Polish

**Files:**
- Modify: `README.md` — verify all links work, update progress table
- Create: `.gitignore`

**Step 1: Verify all section README checklists show `[x]` for all topics**

Check each of:
- `01-fundamentals/README.md` (should already be `[x]`)
- `02-design-patterns/README.md` (should already be `[x]`)
- `03-system-design/README.md`
- `04-architecture-patterns/README.md`
- `05-data/README.md`
- `06-devops-infrastructure/README.md`
- `07-soft-skills/README.md`
- `08-case-studies/README.md`

**Step 2: Create `.gitignore`**

```
.DS_Store
Thumbs.db
*.swp
```

**Step 3: Final commit**

```bash
git add .
git commit -m "docs: complete knowledge base — all sections written"
```

---

## Summary

| Task | Section | Files | Status |
|------|---------|-------|--------|
| 4 | System Design | 5 topic files | ⬜ |
| 5 | Architecture Patterns | 6 topic files | ⬜ |
| 6 | Data | 4 topic files | ⬜ |
| 7 | DevOps & Infrastructure | 4 topic files | ⬜ |
| 8 | Soft Skills | 4 topic files | ⬜ |
| 9 | Case Studies | 4 topic files | ⬜ |
| 10 | Final Polish | 2 files | ⬜ |

**Total new files:** 27 topic files + 6 updated section READMEs + 1 .gitignore = 34 files
