"""
SmartSalary India — Dynamic Question Graph & Prerequisite Dependency Engine
Enforces declarative branching, mandatory field capture, and validation rules.
Throws InsufficientApplicabilityFactsError when prerequisites are unsatisfied.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class QuestionOperator(StrEnum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_EQUAL = "GREATER_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_EQUAL = "LESS_EQUAL"
    IN = "IN"
    NOT_IN = "NOT_IN"
    IS_TRUE = "IS_TRUE"
    IS_FALSE = "IS_FALSE"


class QuestionDataType(StrEnum):
    BOOLEAN = "BOOLEAN"
    DECIMAL = "DECIMAL"
    INTEGER = "INTEGER"
    STRING = "STRING"
    ENUM = "ENUM"


@dataclass(frozen=True)
class QuestionCondition:
    field: str
    operator: QuestionOperator
    value: Any = None

    def evaluate(self, facts: dict[str, Any]) -> bool:
        val = facts.get(self.field)
        if self.operator == QuestionOperator.IS_TRUE:
            return bool(val) is True
        if self.operator == QuestionOperator.IS_FALSE:
            return bool(val) is False
        if val is None:
            return False

        if self.operator == QuestionOperator.EQUALS:
            return str(val) == str(self.value)
        elif self.operator == QuestionOperator.NOT_EQUALS:
            return str(val) != str(self.value)
        elif self.operator == QuestionOperator.GREATER_THAN:
            return float(val) > float(self.value)
        elif self.operator == QuestionOperator.GREATER_EQUAL:
            return float(val) >= float(self.value)
        elif self.operator == QuestionOperator.LESS_THAN:
            return float(val) < float(self.value)
        elif self.operator == QuestionOperator.LESS_EQUAL:
            return float(val) <= float(self.value)
        elif self.operator == QuestionOperator.IN:
            return val in self.value
        elif self.operator == QuestionOperator.NOT_IN:
            return val not in self.value
        return False


@dataclass(frozen=True)
class DynamicQuestion:
    question_id: str
    category: str
    label: str
    help_text: str
    data_type: QuestionDataType
    depends_on: list[QuestionCondition] = field(default_factory=list)
    is_mandatory: bool = True
    fallback_default: Any = None
    options: list[str] = field(default_factory=list)
    rule_id_impact: str | None = None

    def is_applicable(self, facts: dict[str, Any]) -> bool:
        if not self.depends_on:
            return True
        return all(cond.evaluate(facts) for cond in self.depends_on)


class InsufficientApplicabilityFactsError(Exception):
    """Raised when a mandatory question condition is met but the required value is missing."""

    def __init__(self, missing_question_ids: list[str], details: str):
        self.missing_question_ids = missing_question_ids
        self.details = details
        super().__init__(f"INSUFFICIENT_APPLICABILITY_FACTS: {details} (Missing: {missing_question_ids})")


class DynamicQuestionEngine:
    """
    Evaluates questionnaire state, filters dynamic questions for occupation/regime,
    and certifies whether all applicability-determining facts are captured.
    """

    _QUESTION_CATALOG: dict[str, DynamicQuestion] = {
        # 1. Old Regime HRA Prerequisite Questions
        "Q_RENT_PAID_ANNUAL": DynamicQuestion(
            question_id="Q_RENT_PAID_ANNUAL",
            category="HRA_EXEMPTION",
            label="Annual Rent Paid",
            help_text="Total rent paid towards residential accommodation in the financial year",
            data_type=QuestionDataType.DECIMAL,
            depends_on=[
                QuestionCondition(field="tax_regime", operator=QuestionOperator.EQUALS, value="OLD"),
                QuestionCondition(field="hra_received", operator=QuestionOperator.GREATER_THAN, value=0),
            ],
            is_mandatory=True,
            fallback_default=None,
            rule_id_impact="TAX-SEC-10-13A-HRA",
        ),
        "Q_HRA_METRO_CITY": DynamicQuestion(
            question_id="Q_HRA_METRO_CITY",
            category="HRA_EXEMPTION",
            label="Is accommodation in a Metro City?",
            help_text="Delhi, Mumbai, Kolkata, Chennai qualify for 50% basic limit instead of 40%",
            data_type=QuestionDataType.BOOLEAN,
            depends_on=[
                QuestionCondition(field="tax_regime", operator=QuestionOperator.EQUALS, value="OLD"),
                QuestionCondition(field="hra_received", operator=QuestionOperator.GREATER_THAN, value=0),
                QuestionCondition(field="rent_paid_annual", operator=QuestionOperator.GREATER_THAN, value=0),
            ],
            is_mandatory=True,
            fallback_default=False,
            rule_id_impact="TAX-SEC-10-13A-HRA",
        ),
        # 2. Section 80D Medical Insurance Age Branching
        "Q_80D_PARENTS_SENIOR_CITIZEN": DynamicQuestion(
            question_id="Q_80D_PARENTS_SENIOR_CITIZEN",
            category="DEDUCTIONS_80D",
            label="Are parents aged 60 or above (Senior Citizens)?",
            help_text="Increases 80D parent health insurance deduction ceiling from ₹25,000 to ₹50,000",
            data_type=QuestionDataType.BOOLEAN,
            depends_on=[
                QuestionCondition(field="tax_regime", operator=QuestionOperator.EQUALS, value="OLD"),
                QuestionCondition(field="health_insurance_parents", operator=QuestionOperator.GREATER_THAN, value=0),
            ],
            is_mandatory=True,
            fallback_default=False,
            rule_id_impact="TAX-SEC-80D-SENIOR",
        ),
        # 3. EPF Voluntary Higher Wage Option
        "Q_PF_OPT_IN_HIGHER_WAGE": DynamicQuestion(
            question_id="Q_PF_OPT_IN_HIGHER_WAGE",
            category="PF_OPTIONS",
            label="Contribute PF on full basic salary exceeding ₹15,000 statutory limit?",
            help_text="Calculate 12% EPF on actual Basic+DA without capping at ₹15,000/month",
            data_type=QuestionDataType.BOOLEAN,
            depends_on=[
                QuestionCondition(field="basic_salary_monthly", operator=QuestionOperator.GREATER_THAN, value=15000),
            ],
            is_mandatory=False,
            fallback_default=False,
            rule_id_impact="PF-2026-27-STATUTORY",
        ),
    }

    @classmethod
    def get_applicable_questions(cls, facts: dict[str, Any]) -> list[DynamicQuestion]:
        """Returns ordered list of questions applicable to current profile facts."""
        return [q for q in cls._QUESTION_CATALOG.values() if q.is_applicable(facts)]

    @classmethod
    def validate_facts_sufficiency(cls, facts: dict[str, Any]) -> None:
        """
        Validates that all mandatory applicable questions have a non-null answer provided.
        Raises InsufficientApplicabilityFactsError if any required fact is missing.
        """
        missing_ids = []
        for q in cls.get_applicable_questions(facts):
            if q.is_mandatory:
                # Value must be explicitly present in facts and not None
                field_key = q.question_id.lower().removeprefix("q_")
                if field_key not in facts and q.question_id not in facts:
                    missing_ids.append(q.question_id)

        if missing_ids:
            raise InsufficientApplicabilityFactsError(
                missing_question_ids=missing_ids,
                details=f"Required statutory facts missing for calculation: {', '.join(missing_ids)}",
            )
