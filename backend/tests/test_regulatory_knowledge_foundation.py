"""
Tests for M2.13 Regulatory Knowledge Foundation:
- Official Source Registry authority hierarchy & validation
- State/UT jurisdiction profiles & Professional Tax boundary isolation
- Strict multi-tier validation (Tier 1 Primary vs Tier 5 Discovery)
"""

from app.core.compliance.source_registry import (
    AuthorityTier,
    OfficialSourceRegistry,
    VerificationStatus,
)
from app.core.compliance.state_jurisdiction_master import (
    JurisdictionStatus,
    StateJurisdictionMaster,
)


def test_source_registry_authority_tiers_and_authorization():
    # 1. Primary Legislation (Income-tax Act, 2025)
    tax_source = OfficialSourceRegistry.get_source("SR-FED-TAX-ACT-2025")
    assert tax_source is not None
    assert tax_source.authority_tier == AuthorityTier.TIER_1_PRIMARY_ACT
    assert tax_source.verification_status == VerificationStatus.REAL_VERIFIED_SOURCE
    assert tax_source.can_authorize_production() is True
    assert "incometaxindia.gov.in" in tax_source.official_url

    # 2. Statutory Rules (EPF Scheme 2026)
    epf_source = OfficialSourceRegistry.get_source("SR-EPFO-SCHEME-2026")
    assert epf_source is not None
    assert epf_source.authority_tier == AuthorityTier.TIER_2_STATUTORY_RULES
    assert epf_source.can_authorize_production() is True


def test_state_jurisdiction_pt_isolation():
    # 1. Karnataka - Active PT
    ka_profile = StateJurisdictionMaster.get_profile("KA")
    assert ka_profile is not None
    assert ka_profile.pt_status == JurisdictionStatus.ACTIVE_APPLICABLE
    assert StateJurisdictionMaster.is_pt_applicable("KA") is True
    assert ka_profile.pt_rule_id == "PT-2026-27-KA-SALARIED"

    # 2. Delhi (NCT) - NO Professional Tax
    dl_profile = StateJurisdictionMaster.get_profile("DL")
    assert dl_profile is not None
    assert dl_profile.pt_status == JurisdictionStatus.NOT_APPLICABLE
    assert dl_profile.pt_rule_id is None
    assert StateJurisdictionMaster.is_pt_applicable("DL") is False

    # 3. Maharashtra - Active PT
    mh_profile = StateJurisdictionMaster.get_profile("MH")
    assert mh_profile is not None
    assert mh_profile.pt_status == JurisdictionStatus.ACTIVE_APPLICABLE
    assert StateJurisdictionMaster.is_pt_applicable("MH") is True
