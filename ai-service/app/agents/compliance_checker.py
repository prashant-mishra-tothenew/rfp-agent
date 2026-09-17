from typing import Any


def check_compliance(
    requirements: list[dict[str, Any]],
    responses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic compliance checker — runs after LLM generation."""
    response_map = {r["requirementId"]: r for r in responses}

    matrix: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    supported = partial = missing = 0

    for req in requirements:
        req_id = req.get("id", "")
        resp = response_map.get(req_id, {})
        status = resp.get("status", "NOT_SUPPORTED")

        if status == "SUPPORTED":
            supported += 1
            matrix_status = "Supported"
        elif status == "PARTIALLY_SUPPORTED":
            partial += 1
            matrix_status = "Partial"
        else:
            missing += 1
            matrix_status = "Not supported"

        entry = {
            "requirementId": req_id,
            "requirement": req.get("description", ""),
            "response": resp.get("response", ""),
            "evidence": resp.get("evidence", []),
            "status": matrix_status,
            "reviewRequired": resp.get("reviewRequired", True),
        }
        matrix.append(entry)

        if status in ("NOT_SUPPORTED", "HUMAN_VERIFICATION_REQUIRED", "PARTIALLY_SUPPORTED"):
            gaps.append(
                {
                    "requirementId": req_id,
                    "requirement": req.get("description", ""),
                    "status": status,
                    "gaps": resp.get("gaps", []),
                    "mandatory": req.get("mandatory", False),
                }
            )

    total = len(requirements) or 1
    coverage = round((supported + partial * 0.5) / total * 100, 1)

    return {
        "complianceMatrix": matrix,
        "gaps": gaps,
        "summary": {
            "total": len(requirements),
            "supported": supported,
            "partial": partial,
            "missing": missing,
            "coveragePercent": coverage,
        },
    }
