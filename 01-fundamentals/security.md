# Security Fundamentals

## Authentication vs Authorization

| Concept | Question answered | Example |
|---------|-------------------|--------|
| Authentication | Who are you? | Login with username/password |
| Authorization | What can you do? | Role-based access control |

---

## Common Auth Mechanisms

### Session-Based Auth
```
Client → POST /login → Server creates session → Returns session cookie
Client → GET /data + cookie → Server validates session → Returns data
```
- State stored server-side
- Easy to revoke
- Doesn't scale horizontally without shared session store (Redis)

### JWT (JSON Web Token)
```
Header.Payload.Signature
```
- Stateless — server doesn't store sessions
- Self-contained: claims embedded in token
- Cannot be revoked without token blocklist
- Use short expiry (15min) + refresh tokens

### OAuth 2.0 Flows
| Flow | Use case |
|------|----------|
| Authorization Code | Web apps with server-side backend |
| Authorization Code + PKCE | SPAs and mobile apps |
| Client Credentials | Machine-to-machine (M2M) |
| Device Code | TVs, CLI tools |

### API Keys
- Simple, but no expiry by default
- Must be rotatable, never embedded in client code
- Use for server-to-server, not end-user auth

---

## Encryption

### Symmetric vs Asymmetric
| | Symmetric | Asymmetric |
|--|-----------|------------|
| Keys | One shared key | Public + private key pair |
| Speed | Fast | Slow |
| Use | Bulk data encryption (AES) | Key exchange, signatures (RSA, EC) |
| Examples | AES-256, ChaCha20 | RSA-2048, ECDSA |

### TLS Handshake (simplified)
```
1. Client Hello (supported cipher suites)
2. Server Hello + Certificate
3. Client verifies certificate (via CA chain)
4. Key exchange → derive session keys
5. Encrypted communication begins
```

### Hashing
- One-way function: `hash(data) → digest`
- **SHA-256/SHA-3** for data integrity
- **bcrypt/Argon2** for passwords (slow by design, salted)
- Never store plaintext passwords; never use MD5 or SHA-1 for passwords

---

## OWASP Top 10 (2021)

| Rank | Vulnerability | Mitigation |
|------|--------------|------------|
| A01 | Broken Access Control | Deny by default, enforce server-side |
| A02 | Cryptographic Failures | Use TLS, strong algorithms, no MD5 |
| A03 | Injection (SQL, NoSQL, OS) | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, security in SDLC |
| A05 | Security Misconfiguration | Hardened defaults, disable unused features |
| A06 | Vulnerable Components | Dependency scanning, patch regularly |
| A07 | Auth Failures | MFA, rate limiting, secure session mgmt |
| A08 | Data Integrity Failures | CI/CD integrity checks, signed packages |
| A09 | Logging Failures | Centralized logging, alerting |
| A10 | SSRF | Allowlist outbound requests, metadata endpoint protection |

---

## Common Attacks & Defenses

### SQL Injection
```sql
-- Vulnerable
SELECT * FROM users WHERE name = '" + userInput + "'

-- Safe: parameterized query
SELECT * FROM users WHERE name = ?
```

### XSS (Cross-Site Scripting)
- **Stored XSS**: malicious script saved in DB, served to other users
- **Reflected XSS**: script in URL, reflected back in response
- Defense: escape output, Content-Security-Policy headers, HttpOnly cookies

### CSRF (Cross-Site Request Forgery)
- Attacker tricks authenticated user into submitting requests
- Defense: CSRF tokens, SameSite cookie attribute, verify Origin header

### SSRF (Server-Side Request Forgery)
- Attacker makes server fetch internal URLs (e.g., `http://169.254.169.254/` AWS metadata)
- Defense: allowlist outbound destinations, block RFC-1918 ranges

---

## Security at the Architecture Level

### Defense in Depth
- Multiple layers: WAF → API Gateway → App → DB
- No single point of failure in security controls

### Principle of Least Privilege
- Services/users get only the permissions they need
- Separate DB credentials per service
- IAM roles with minimal policy scope

### Zero Trust
- Never trust, always verify — even internal traffic
- mTLS between microservices
- Network segmentation, service mesh

### Secret Management
- Never hardcode secrets in code or Docker images
- Use Vault, AWS Secrets Manager, or GCP Secret Manager
- Rotate secrets regularly

---

## Key Architect Takeaways

1. Auth belongs at the gateway — don't re-implement in every service.
2. Use JWT for stateless APIs but plan for token revocation.
3. Encrypt data at rest and in transit — always TLS 1.2+.
4. Parameterize all queries — injection is still the #1 class of vulnerability.
5. Least privilege for every service account and IAM role.
