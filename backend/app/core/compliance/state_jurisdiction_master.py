"""
SmartSalary India — Regulatory Coverage Matrix & State/UT Master (M2.13)
Maintains comprehensive jurisdictional coverage tracking across all 28 States and 8 Union Territories.
Prevents cross-jurisdiction bleeding of Professional Tax, Shops & Establishments, and Labour rules.
"""

from dataclasses import dataclass
from enum import StrEnum


class RegulatoryDomain(StrEnum):
    INCOME_TAX = "INCOME_TAX"
    TDS = "TDS"
    EPF = "EPF"
    EPS = "EPS"
    EDLI = "EDLI"
    ESI = "ESI"
    PROFESSIONAL_TAX = "PROFESSIONAL_TAX"
    MINIMUM_WAGES = "MINIMUM_WAGES"
    GRATUITY = "GRATUITY"
    STATUTORY_BONUS = "STATUTORY_BONUS"
    LABOUR_REGULATIONS = "LABOUR_REGULATIONS"
    SALARY_ALLOWANCES = "SALARY_ALLOWANCES"
    PERQUISITES = "PERQUISITES"
    GOVERNMENT_PAYROLL = "GOVERNMENT_PAYROLL"
    STATE_LABOUR_RULES = "STATE_LABOUR_RULES"


class JurisdictionStatus(StrEnum):
    ACTIVE_APPLICABLE = "ACTIVE_APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # e.g., States with zero Professional Tax
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


@dataclass(frozen=True)
class StateJurisdictionProfile:
    state_code: str
    state_name: str
    is_union_territory: bool
    pt_status: JurisdictionStatus
    pt_rule_id: str | None
    shops_establishment_act_title: str
    statutory_holidays_mandatory: int
    labour_welfare_fund_applicable: bool


class StateJurisdictionMaster:
    """
    Authoritative state & union territory profile registry.
    Ensures state-specific rules are isolated strictly by ISO/State codes.
    Covers all 28 States and 8 Union Territories of India.
    """

    _STATES: dict[str, StateJurisdictionProfile] = {
        # Verified States with Active PT Engine Rules
        "KA": StateJurisdictionProfile("KA", "Karnataka", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-KA-SALARIED", "Karnataka Shops and Commercial Establishments Act, 1961", 10, True),
        "MH": StateJurisdictionProfile("MH", "Maharashtra", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-MH-SALARIED", "Maharashtra Shops and Establishments (Regulation of Employment and Conditions of Service) Act, 2017", 8, True),
        "TS": StateJurisdictionProfile("TS", "Telangana", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-TS-SALARIED", "Telangana Shops and Establishments Act, 1988", 8, True),
        "TN": StateJurisdictionProfile("TN", "Tamil Nadu", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-TN-SALARIED", "Tamil Nadu Shops and Establishments Act, 1947", 9, True),
        "WB": StateJurisdictionProfile("WB", "West Bengal", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-WB-SALARIED", "West Bengal Shops and Establishments Act, 1963", 10, True),
        "GJ": StateJurisdictionProfile("GJ", "Gujarat", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-GJ-SALARIED", "Gujarat Shops and Establishments Act, 2019", 8, True),
        "AP": StateJurisdictionProfile("AP", "Andhra Pradesh", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-AP-SALARIED", "Andhra Pradesh Shops and Establishments Act, 1988", 8, True),
        "KL": StateJurisdictionProfile("KL", "Kerala", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-KL-SALARIED", "Kerala Shops and Commercial Establishments Act, 1960", 13, True),
        "MP": StateJurisdictionProfile("MP", "Madhya Pradesh", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-MP-SALARIED", "Madhya Pradesh Shops and Establishments Act, 1958", 8, True),
        "OR": StateJurisdictionProfile("OR", "Odisha", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-OR-SALARIED", "Odisha Shops and Commercial Establishments Act, 1956", 8, True),
        "AS": StateJurisdictionProfile("AS", "Assam", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-AS-SALARIED", "Assam Shops and Establishments Act, 1971", 8, True),
        "BR": StateJurisdictionProfile("BR", "Bihar", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-BR-SALARIED", "Bihar Shops and Establishments Act, 1953", 8, False),
        "CG": StateJurisdictionProfile("CG", "Chhattisgarh", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-CG-SALARIED", "Chhattisgarh Shops and Establishments Act, 1958", 8, True),
        "JH": StateJurisdictionProfile("JH", "Jharkhand", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-JH-SALARIED", "Jharkhand Shops and Establishments Act, 2000", 8, False),
        "ME": StateJurisdictionProfile("ME", "Meghalaya", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-ME-SALARIED", "Meghalaya Shops and Establishments Act, 2003", 8, False),
        "MN": StateJurisdictionProfile("MN", "Manipur", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-MN-SALARIED", "Manipur Shops and Establishments Act, 1972", 8, False),
        "MZ": StateJurisdictionProfile("MZ", "Mizoram", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-MZ-SALARIED", "Mizoram Shops and Establishments Act, 2010", 8, False),
        "NL": StateJurisdictionProfile("NL", "Nagaland", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-NL-SALARIED", "Nagaland Professions, Trades Tax Act, 1968", 8, False),
        "SK": StateJurisdictionProfile("SK", "Sikkim", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-SK-SALARIED", "Sikkim Tax on Professions, Trades Act, 2006", 8, False),
        "TR": StateJurisdictionProfile("TR", "Tripura", False, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-TR-SALARIED", "Tripura Professions, Trades Tax Act, 1997", 8, False),

        # States with NO Professional Tax (Explicitly Not Applicable)
        "DL": StateJurisdictionProfile("DL", "Delhi (NCT)", True, JurisdictionStatus.NOT_APPLICABLE, None, "Delhi Shops and Establishments Act, 1954", 3, True),
        "HR": StateJurisdictionProfile("HR", "Haryana", False, JurisdictionStatus.NOT_APPLICABLE, None, "Punjab Shops and Commercial Establishments Act, 1958", 8, True),
        "PB": StateJurisdictionProfile("PB", "Punjab", False, JurisdictionStatus.NOT_APPLICABLE, None, "Punjab Shops and Commercial Establishments Act, 1958", 8, True),
        "RJ": StateJurisdictionProfile("RJ", "Rajasthan", False, JurisdictionStatus.NOT_APPLICABLE, None, "Rajasthan Shops and Commercial Establishments Act, 1958", 8, False),
        "UP": StateJurisdictionProfile("UP", "Uttar Pradesh", False, JurisdictionStatus.NOT_APPLICABLE, None, "Uttar Pradesh Dookan Aur Vanijya Adhishthan Adhiniyam, 1962", 8, False),
        "UK": StateJurisdictionProfile("UK", "Uttarakhand", False, JurisdictionStatus.NOT_APPLICABLE, None, "Uttarakhand Shops and Establishments Act, 2017", 8, False),
        "HP": StateJurisdictionProfile("HP", "Himachal Pradesh", False, JurisdictionStatus.NOT_APPLICABLE, None, "Himachal Pradesh Shops and Commercial Establishments Act, 1969", 8, False),
        "GA": StateJurisdictionProfile("GA", "Goa", False, JurisdictionStatus.NOT_APPLICABLE, None, "Goa, Daman and Diu Shops and Establishments Act, 1973", 8, True),
        "AR": StateJurisdictionProfile("AR", "Arunachal Pradesh", False, JurisdictionStatus.NOT_APPLICABLE, None, "Arunachal Pradesh Shops and Establishments Act", 8, False),

        # Union Territories
        "CH": StateJurisdictionProfile("CH", "Chandigarh", True, JurisdictionStatus.NOT_APPLICABLE, None, "Punjab Shops and Commercial Establishments Act, 1958", 8, True),
        "PY": StateJurisdictionProfile("PY", "Puducherry", True, JurisdictionStatus.ACTIVE_APPLICABLE, "PT-2026-27-PY-SALARIED", "Puducherry Shops and Establishments Act, 1964", 8, False),
        "JK": StateJurisdictionProfile("JK", "Jammu & Kashmir", True, JurisdictionStatus.NOT_APPLICABLE, None, "Jammu and Kashmir Shops and Establishments Act, 1966", 8, False),
        "LA": StateJurisdictionProfile("LA", "Ladakh", True, JurisdictionStatus.NOT_APPLICABLE, None, "Jammu and Kashmir Shops and Establishments Act, 1966", 8, False),
        "AN": StateJurisdictionProfile("AN", "Andaman & Nicobar Islands", True, JurisdictionStatus.NOT_APPLICABLE, None, "Andaman and Nicobar Islands Labour Rules", 8, False),
        "DN": StateJurisdictionProfile("DN", "Dadra & Nagar Haveli and Daman & Diu", True, JurisdictionStatus.NOT_APPLICABLE, None, "Daman and Diu Shops and Establishments Act", 8, False),
        "LD": StateJurisdictionProfile("LD", "Lakshadweep", True, JurisdictionStatus.NOT_APPLICABLE, None, "Lakshadweep Labour Administration Rules", 8, False),
    }

    @classmethod
    def get_profile(cls, state_code: str) -> StateJurisdictionProfile | None:
        return cls._STATES.get(state_code.upper())

    @classmethod
    def is_pt_applicable(cls, state_code: str) -> bool:
        prof = cls.get_profile(state_code)
        return prof is not None and prof.pt_status == JurisdictionStatus.ACTIVE_APPLICABLE

    @classmethod
    def list_all(cls) -> list[StateJurisdictionProfile]:
        return sorted(list(cls._STATES.values()), key=lambda x: x.state_name)
