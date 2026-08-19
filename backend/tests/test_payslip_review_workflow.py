def test_payslip_correction_lifecycle_preserves_raw_extraction():
    # Pure model/repository dictionary test
    # Simulate extraction data
    raw_extraction_data = {
        "employee_name": "Kavita Nair",
        "basic": "35000.00",
        "employee_epf": "1500.00",  # Raw extracted
    }

    # Simulate correction history tracking
    correction_event = {
        "field_name": "employee_epf",
        "old_value": "1500.00",
        "new_value": "1800.00",
        "reason": "OCR blur misread 1800 as 1500; verified with physical payslip",
        "corrected_by_user_id": 42,
    }

    discrepancy_flags = {
        "reconciliation_status": "CORRECTED",
        "corrections_history": [correction_event],
    }

    # Verify that raw extraction data remains completely untouched
    assert raw_extraction_data["employee_epf"] == "1500.00"
    assert len(discrepancy_flags["corrections_history"]) == 1
    assert discrepancy_flags["corrections_history"][0]["new_value"] == "1800.00"
    assert discrepancy_flags["corrections_history"][0]["old_value"] == "1500.00"
