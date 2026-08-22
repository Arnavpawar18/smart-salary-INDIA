"""
SmartSalary India — Stage M2.2 Occupation & Profile Tests
Enforces the sovereign invariant:
Occupation selects dynamic questions and income types — NEVER the statutory tax regime.
"""

from app.core.compliance.occupation_catalog_service import OccupationCatalogService
from app.models.occupation_enums import ResidentialStatus, TaxpayerType


def test_occupation_hierarchy_7_tiers():
    """Verify that all occupations have full 7-tier metadata."""
    occupations = OccupationCatalogService.list_all()
    assert len(occupations) >= 5

    for occ in occupations:
        assert occ.industry != ""
        assert occ.sector != ""
        assert occ.activity != ""
        assert occ.occupation != ""
        assert occ.specialization != ""
        assert occ.role != ""
        assert isinstance(occ.default_taxpayer_type, TaxpayerType)
        assert len(occ.applicable_income_types) > 0
        assert len(occ.question_categories) > 0


def test_occupation_never_selects_tax_regime():
    """
    NON-NEGOTIABLE SOVEREIGN INVARIANT TEST:
    Occupation must NEVER dictate or predetermine Old vs New tax regime.
    """
    for occ_key in ["SOFTWARE_ENGINEER", "DOCTOR_PRIVATE_PRACTICE", "FARMER_CROP_PRODUCER"]:
        regime = OccupationCatalogService.determine_regime_from_occupation(occ_key)
        assert regime is None, f"Occupation '{occ_key}' attempted to determine a tax regime!"


def test_residential_status_enum_values():
    """Verify canonical Indian residential status options."""
    assert ResidentialStatus.RESIDENT.value == "RESIDENT"
    assert ResidentialStatus.NON_RESIDENT.value == "NON_RESIDENT"
    assert ResidentialStatus.RNOR.value == "RNOR"
