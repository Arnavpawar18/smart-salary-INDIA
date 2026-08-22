class FinancialEngineError(Exception):
    """Base exception for all financial engine errors."""

    pass


class RuleNotFoundError(FinancialEngineError):
    """Raised when an active, verified statutory rule cannot be found."""

    pass


class AmbiguousRuleVersionError(FinancialEngineError):
    """Raised when multiple active rules conflict for the same context."""

    pass


class ProfessionalTaxRuleNotConfiguredError(FinancialEngineError):
    """Raised when Professional Tax is requested for a state whose statutory rule is not verified/configured."""

    pass


class FinancialYearNotFoundError(FinancialEngineError):
    """Raised when a financial year does not exist in statutory tax periods."""

    pass


class InvalidSalaryInputError(FinancialEngineError):
    """Raised when salary input values are mathematically or contractually invalid."""

    pass


class CalculationInvariantViolationError(FinancialEngineError):
    """Raised when a calculation output violates mathematical or financial sanity invariants."""

    pass


class SnapshotIntegrityError(FinancialEngineError):
    """Raised when a calculation snapshot fails hash verification or tampering checks."""

    pass


class AuditImmutabilityError(FinancialEngineError):
    """Raised when an UPDATE, DELETE, or in-place mutation is attempted on append-only audit logs or snapshots."""

    pass


class AuditChainTamperError(FinancialEngineError):
    """Raised when cryptographic hash-chain verification detects an altered, missing, inserted, or reordered event."""

    pass


class AuditConcurrencyError(FinancialEngineError):
    """Raised when atomic chain-head allocation or lock contention fails during concurrent audit writes."""

    pass


class TenantAuditIsolationError(FinancialEngineError):
    """Raised when a cross-tenant audit ledger read, injection, or verification operation is attempted."""

    pass
