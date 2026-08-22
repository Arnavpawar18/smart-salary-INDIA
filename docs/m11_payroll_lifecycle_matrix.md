# Milestone M11: Payroll Lifecycle State Machine Matrix

**Scope**: Lifecycle transitions and correction workflows for enterprise payroll periods.

---

## 1. State Machine Transitions

| From State | Action / Trigger | Allowed Next State | Disallowed Transitions |
|---|---|---|---|
| `OPEN` / `DRAFT` | Calculate Batch | `CALCULATED` | Cannot jump to `LOCKED` directly |
| `CALCULATED` | Review & Approve | `APPROVED` or `HR_REVIEW` | Re-calculating without incrementing version |
| `APPROVED` | Disburse & Lock | `LOCKED` | Cannot revert to `OPEN` without creating correction version |
| `LOCKED` | Re-run Request | Creates new `run_version` (e.g. v2) | Cannot overwrite locked snapshot v1 |

---

## 2. Verdict
**Status**: **PASSED**  
Milestone M11 is officially closed and verified.
