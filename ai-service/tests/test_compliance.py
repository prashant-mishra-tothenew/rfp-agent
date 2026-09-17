from app.agents.compliance_checker import check_compliance


def test_compliance_checker_supported():
    requirements = [{"id": "REQ-001", "description": "Must support Kubernetes"}]
    responses = [
        {
            "requirementId": "REQ-001",
            "response": "We support Kubernetes.",
            "status": "SUPPORTED",
            "reviewRequired": False,
        }
    ]
    result = check_compliance(requirements, responses)
    assert result["summary"]["supported"] == 1
    assert result["summary"]["coveragePercent"] == 100.0


def test_compliance_checker_missing():
    requirements = [{"id": "REQ-002", "description": "ISO 27001 required"}]
    responses = [
        {
            "requirementId": "REQ-002",
            "response": "No evidence found.",
            "status": "HUMAN_VERIFICATION_REQUIRED",
            "reviewRequired": True,
            "gaps": ["No certification evidence"],
        }
    ]
    result = check_compliance(requirements, responses)
    assert result["summary"]["missing"] == 1
    assert result["complianceMatrix"][0]["status"] == "Not supported"
    assert len(result["gaps"]) == 1
