# Security Hardening & Remediation Checklist

Hardening configurations implemented on Zayd's API endpoints and network ingress pathways.

## Security Controls and Remediation Checklist

### 1. HTTP Security Headers
Every HTTP response is injected with strict security headers in API middlewares:
- **Content-Security-Policy (CSP)**: `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';` (Gards script injection).
- **X-Frame-Options**: `DENY` (Blocks Clickjacking).
- **X-Content-Type-Options**: `nosniff` (Prevents MIME-type sniffing).
- **X-XSS-Protection**: `1; mode=block` (Configures classical browser protections).
- **Referrer-Policy**: `strict-origin-when-cross-origin` (Redacts referrer values).
- **Strict-Transport-Security**: `max-age=63072000; includeSubDomains; preload` (Forces encrypted connections).
- **Permissions-Policy**: `geolocation=(), microphone=(), camera=()` (Blocks browser sensor access).

### 2. CORS (Cross-Origin Resource Sharing)
- Public wildcards are forbidden.
- Allowed origins are configured via settings `ServiceSettings.allowed_origins` (or environment `ALLOWED_ORIGINS`).
- Default: Restricts access to standard local developer environments (`http://localhost:3000`, `http://localhost:3100`, etc.) in greenfield and local configs.

### 3. API Rate Limiting
Custom token- and IP-based rate limiting middleware guards all endpoints:
- **Sensitive Operations**: Bounded to **10 requests per minute** per hashed token/IP. Covers login, registration, feedback mutations, and connection testing.
- **Normal Operations**: Bounded to **100 requests per minute** per hashed token/IP. Covers general endpoints.
- **Exemptions**: Health `/health` and metrics `/metrics` are excluded from consumer rate-limit tracking.
- Memory protection triggers automatic cache purges when cache exceeds 10,000 entries, preventing memory exhaustion.

### 4. SSRF and DNS Egress Restriction
- Every third-party API pointer must pass loopback and RFC 1918 private network subnet verification.
- Local loopbacks are resolving targets and are rejected by default. In local testing/docker compose setups, validation can be bypassed by setting `ALLOW_PRIVATE_NETWORKS=true` in environment configs.
