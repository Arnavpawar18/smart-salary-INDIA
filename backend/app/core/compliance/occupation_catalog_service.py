"""
SmartSalary India — Occupation Catalog Service
Provides the 7-tier occupation hierarchy and enforces the sovereign invariant:
Occupation selects dynamic questions, income sources, and facts — NEVER the statutory tax regime.
"""

from dataclasses import dataclass

from app.models.occupation_enums import TaxpayerType


@dataclass(frozen=True)
class OccupationHierarchyNode:
    industry: str
    sector: str
    activity: str
    occupation: str
    specialization: str
    role: str
    default_taxpayer_type: TaxpayerType
    applicable_income_types: list[str]
    question_categories: list[str]


class OccupationCatalogService:
    """
    Catalog of supported Indian professions spanning IT, Healthcare, Agriculture, Legal, Retail, etc.
    """

    _OCCUPATIONS: dict[str, OccupationHierarchyNode] = {
        "SOFTWARE_ENGINEER": OccupationHierarchyNode(
            industry="Information Technology",
            sector="Software Development",
            activity="Application Programming",
            occupation="Software Engineer",
            specialization="Backend / Distributed Systems",
            role="Senior Software Developer",
            default_taxpayer_type=TaxpayerType.SALARIED_INDIVIDUAL,
            applicable_income_types=["SALARY", "CAPITAL", "INTEREST_DIVIDEND"],
            question_categories=["SALARY_DETAILS", "ESOP_RSU", "ALLOWANCES"],
        ),
        "DOCTOR_PRIVATE_PRACTICE": OccupationHierarchyNode(
            industry="Healthcare",
            sector="Medical Services",
            activity="Clinical Medicine",
            occupation="Medical Doctor",
            specialization="General Physician / Cardiology",
            role="Private Practice Clinic Owner",
            default_taxpayer_type=TaxpayerType.SELF_EMPLOYED_PROFESSIONAL,
            applicable_income_types=["PROFESSIONAL", "RENTAL", "INTEREST_DIVIDEND"],
            question_categories=["PROFESSIONAL_RECEIPTS", "CLINIC_EXPENSES", "EQUIPMENT_DEPRECIATION"],
        ),
        "FARMER_CROP_PRODUCER": OccupationHierarchyNode(
            industry="Agriculture",
            sector="Crop Production",
            activity="Grain & Cash Crops",
            occupation="Farmer / Agriculturist",
            specialization="Wheat & Rice Cultivation",
            role="Farm Owner / Operator",
            default_taxpayer_type=TaxpayerType.FARMER_AGRICULTURIST,
            applicable_income_types=["AGRICULTURAL", "OTHER"],
            question_categories=["AGRICULTURAL_LAND", "CROP_CYCLE", "IRRIGATION_EXPENSES"],
        ),
        "ADVOCATE_LEGAL_COUNSEL": OccupationHierarchyNode(
            industry="Legal",
            sector="Legal Practice",
            activity="Litigation & Corporate Law",
            occupation="Advocate / Lawyer",
            specialization="Taxation & Corporate Litigation",
            role="Independent Legal Consultant",
            default_taxpayer_type=TaxpayerType.SELF_EMPLOYED_PROFESSIONAL,
            applicable_income_types=["PROFESSIONAL", "INTEREST_DIVIDEND"],
            question_categories=["PROFESSIONAL_RECEIPTS", "CHAMBER_EXPENSES"],
        ),
        "RETAIL_SHOPKEEPER": OccupationHierarchyNode(
            industry="Retail & Commerce",
            sector="Consumer Goods",
            activity="Grocery & Supermarket",
            occupation="Retail Merchant / Shopkeeper",
            specialization="FMCG Retail",
            role="Store Owner",
            default_taxpayer_type=TaxpayerType.BUSINESS_OWNER,
            applicable_income_types=["BUSINESS", "RENTAL"],
            question_categories=["BUSINESS_TURNOVER", "INVENTORY_COSTS", "COMMERCIAL_RENT"],
        ),
    }

    @classmethod
    def get_occupation(cls, key: str) -> OccupationHierarchyNode | None:
        return cls._OCCUPATIONS.get(key)

    @classmethod
    def list_all(cls) -> list[OccupationHierarchyNode]:
        return list(cls._OCCUPATIONS.values())

    @classmethod
    def determine_regime_from_occupation(cls, occupation_key: str) -> None:
        """
        INVARIANT ENFORCER:
        Occupation must NEVER determine or force a tax regime.
        Always raises NotImplementedError / returns None to prevent regime coupling.
        """
        return None
