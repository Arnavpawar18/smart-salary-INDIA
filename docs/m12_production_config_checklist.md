# Milestone M12: Production Configuration & Hardening Checklist

**Target**: Production Launch  
**Verification Date**: August 20, 2026

---

## 1. Production Hardening Checklist

- [x] **Database Isolation**: PostgreSQL instance on secure subnet with connection pooling and SSL mode `require`.
- [x] **Secret Management**: Zero hardcoded secrets in codebase; environment variables loaded from secure vault.
- [x] **Security Headers**: HSTS, X-Content-Type-Options, X-Frame-Options, CSP, and Referrer-Policy active.
- [x] **Rate Limiting**: Sliding window rate limiter enabled for `/auth/*` and `/chat/*` endpoints.
- [x] **Audit Immutability**: Cryptographic hash chaining active across audit log records.
- [x] **Statutory Fail-Closed Mode**: Any unconfigured state or unverified financial year fails closed safely.
- [x] **Release Tag**: Codebase frozen at verified commit milestone gate.
