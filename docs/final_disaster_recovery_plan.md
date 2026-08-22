# SmartSalary India — Disaster Recovery Plan (DRP)

**Document Version**: 1.0  
**Effective Date**: August 20, 2026  
**Scope**: High availability, failover protocols, data loss mitigation, and incident runbooks.

---

## 1. Disaster Recovery Objectives
- **RPO (Recovery Point Objective)**: Maximum 15 minutes of transactional ledger data.
- **RTO (Recovery Time Objective)**: Maximum 30 minutes to spin up redundant platform in alternative AZ.

---

## 2. Failover Runbook

1. **Step 1: Outage Detection & Triage**: Automatic health check failures (`/api/v1/health/readiness`) trigger incident alerts within 60 seconds.
2. **Step 2: Database Failover**: Promote standby PostgreSQL replica to Primary.
3. **Step 3: DNS & Ingress Rerouting**: Shift traffic to warm standby cluster.
4. **Step 4: Audit Chain Verification**: Run `AuditService.verify_ledger_integrity()` immediately upon boot.
5. **Step 5: Status Notification**: Publish system status update with verifiable incident hash.
