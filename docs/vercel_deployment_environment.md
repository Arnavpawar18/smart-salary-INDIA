# SmartSalary India — Vercel Production Deployment Environment Variables

This document lists all environment variables required or configurable when deploying SmartSalary India to Vercel.

## 1. Required Variables for Production

| Variable Name | Type | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `string` | Set to `production` |
| `DATABASE_URL` | `string` | Authoritative PostgreSQL connection string (e.g., Neon / Supabase / AWS RDS / Vercel Postgres) |
| `OTP_HASH_SECRET` | `string` | High-entropy secret for deterministic OTP HMAC generation |

## 2. Optional Production Services

| Variable Name | Type | Default / Fallback | Description |
| :--- | :--- | :--- | :--- |
| `REDIS_URL` | `string` | `None` (Falls back to `InMemoryRateLimiter`) | Upstash Redis connection string for distributed rate limiting |
| `RATE_LIMIT_REDIS_REQUIRED` | `boolean` | `false` | If true, fails hard when Redis is unavailable |
| `LOG_LEVEL` | `string` | `INFO` | Application log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SMTP_HOST` | `string` | `smtp.gmail.com` | Outbound transactional SMTP host |
| `SMTP_PORT` | `integer` | `587` | Outbound SMTP port |
| `SMTP_USER` | `string` | `None` | SMTP authentication username / email |
| `SMTP_PASSWORD` | `string` | `None` | SMTP authentication app password |
| `SMTP_FROM_EMAIL` | `string` | `None` | Sender email address |
| `SMTP_FROM_NAME` | `string` | `SmartSalary India` | Sender display name |
| `SMTP_USE_TLS` | `boolean` | `true` | Enable TLS encryption |
