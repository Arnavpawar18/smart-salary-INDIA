# Milestone M10: API Contract & Error Code Matrix

**Verification Scope**: HTTP Status code integrity, payload envelopes, and boundary error responses.

---

## 1. Endpoint Contract Matrix

| Endpoint | Method | Success Code | Error Codes | Schema Envelope |
|---|---|---|---|---|
| `/api/v1/calculations` | POST | `201 CREATED` | `400 BAD_REQUEST`, `422 UNPROCESSABLE_ENTITY`, `500 INTERNAL_SERVER_ERROR` | `CalculationResponse` |
| `/api/v1/calculations/compare-regimes` | POST | `200 OK` | `400 BAD_REQUEST`, `422 UNPROCESSABLE_ENTITY` | `RegimeComparisonResponse` |
| `/api/v1/calculations/history` | GET | `200 OK` | `401 UNAUTHORIZED`, `403 FORBIDDEN` | Paginated Calculation Runs |
| `/api/v1/auth/register` | POST | `201 CREATED` | `400 BAD_REQUEST`, `429 TOO_MANY_REQUESTS` | User Registration Envelope |
| `/api/v1/auth/login` | POST | `200 OK` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `429 TOO_MANY_REQUESTS` | JWT Auth Envelope |
| `/api/v1/scenarios/what-if` | POST | `200 OK` | `400 BAD_REQUEST`, `422 UNPROCESSABLE_ENTITY` | What-If Scenario Matrix |
| `/api/v1/ui/context` | GET | `200 OK` | `500 INTERNAL_SERVER_ERROR` | UI Metadata Context |

---

## 2. Invariant Proof
- All successful calculation operations yield 64-character `input_hash` and `result_hash`.
- Negative/invalid inputs trigger fast rejection before hitting the mathematical calculation pipeline.
