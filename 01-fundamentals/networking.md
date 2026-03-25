# Networking Fundamentals

## OSI Model

The 7-layer model for understanding network protocols:

| Layer | Name | Protocol Examples | Role |
|-------|------|-------------------|------|
| 7 | Application | HTTP, HTTPS, DNS, SMTP | User-facing protocols |
| 6 | Presentation | TLS/SSL, JPEG, JSON | Encoding, encryption |
| 5 | Session | RPC, NetBIOS | Session management |
| 4 | Transport | TCP, UDP | Reliable/unreliable delivery |
| 3 | Network | IP, ICMP, OSPF | Routing between networks |
| 2 | Data Link | Ethernet, ARP, MAC | Node-to-node on same network |
| 1 | Physical | Cables, radio, fiber | Bits over wire |

**Architect tip:** You mostly operate at L4–L7. Know TCP vs UDP cold.

---

## TCP vs UDP

| Property | TCP | UDP |
|----------|-----|-----|
| Connection | Connection-oriented (3-way handshake) | Connectionless |
| Reliability | Guaranteed delivery, ordering, retransmit | Best-effort |
| Overhead | High (headers, ACKs, flow control) | Low |
| Use cases | HTTP, DB connections, file transfer | DNS, video streaming, gaming, VoIP |

### TCP Handshake
```
Client → Server: SYN
Server → Client: SYN-ACK
Client → Server: ACK
--- connection established ---
Client → Server: FIN
Server → Client: ACK + FIN
Client → Server: ACK
--- connection closed ---
```

---

## HTTP/HTTPS

### HTTP Methods
| Method | Idempotent | Safe | Use |
|--------|-----------|------|-----|
| GET | Yes | Yes | Retrieve resource |
| POST | No | No | Create resource |
| PUT | Yes | No | Replace resource |
| PATCH | No | No | Partial update |
| DELETE | Yes | No | Remove resource |

### HTTP Status Codes
- **2xx** — Success (200 OK, 201 Created, 204 No Content)
- **3xx** — Redirect (301 Moved Permanently, 304 Not Modified)
- **4xx** — Client error (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Too Many Requests)
- **5xx** — Server error (500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable)

### HTTP/1.1 vs HTTP/2 vs HTTP/3
| Version | Transport | Multiplexing | Head-of-line blocking |
|---------|-----------|-------------|----------------------|
| HTTP/1.1 | TCP | No (pipelining only) | Yes |
| HTTP/2 | TCP | Yes (streams) | Yes (TCP level) |
| HTTP/3 | QUIC (UDP) | Yes | No |

---

## DNS

Domain Name System — translates hostnames to IP addresses.

### Resolution chain
```
Browser cache → OS cache → Recursive resolver → Root NS → TLD NS → Authoritative NS
```

### Record Types
| Type | Purpose | Example |
|------|---------|----------|
| A | IPv4 address | `api.example.com → 1.2.3.4` |
| AAAA | IPv6 address | `api.example.com → ::1` |
| CNAME | Alias | `www → example.com` |
| MX | Mail server | `example.com → mail.example.com` |
| TXT | Arbitrary text | SPF, DKIM records |
| NS | Name server | Delegates zone |

**TTL** controls how long resolvers cache records. Low TTL = fast propagation, higher DNS load.

---

## Load Balancing

### Algorithms
- **Round Robin** — requests distributed equally in rotation
- **Least Connections** — to server with fewest active connections
- **IP Hash** — same client always goes to same server (session affinity)
- **Weighted** — heavier traffic to more capable servers

### L4 vs L7 Load Balancing
| | L4 (Transport) | L7 (Application) |
|--|----------------|------------------|
| Operates on | IP + TCP/UDP | HTTP headers, URL, cookies |
| Speed | Faster | Slower |
| Routing logic | IP/port based | Content-based |
| Examples | AWS NLB, HAProxy TCP | AWS ALB, Nginx, Envoy |

---

## CDN (Content Delivery Network)

Distributes static assets (images, JS, CSS) to edge nodes close to users.

- Reduces latency by serving from nearest PoP (Point of Presence)
- Absorbs traffic spikes — origin only handles cache misses
- **Push CDN**: you upload content to CDN proactively
- **Pull CDN**: CDN fetches from origin on first request, caches thereafter

---

## WebSockets & Long Polling

| Technique | Description | Use case |
|-----------|-------------|----------|
| Short polling | Client polls every N seconds | Simple, wasteful |
| Long polling | Server holds request until data ready | Chat, notifications |
| WebSocket | Persistent full-duplex TCP connection | Real-time, low-latency |
| SSE (Server-Sent Events) | Server pushes to client (one-way) | Live feeds, dashboards |

---

## Key Architect Takeaways

1. Know when TCP guarantees matter vs when UDP's speed is worth the trade-off.
2. Design APIs with proper HTTP semantics — idempotency matters for retries.
3. DNS TTL affects deployment strategies (blue/green, canary).
4. L7 load balancers unlock routing flexibility (A/B testing, auth offloading).
5. CDNs are your first line of defense against traffic spikes — use them.
