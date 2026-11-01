"""Never confuse a successful PDF export with an approved architectural plan."""
import pytest
from mcp_cad_cloud.multifamiliar_partition import build_partitioned_four_apartment_floor
from mcp_cad_cloud.multifamiliar_acceptance import (
    audit_multifamily_architecture, require_architectural_acceptance,
)


def test_unfinished_multifamily_plan_fails_architectural_acceptance():
    model = build_partitioned_four_apartment_floor()
    report = audit_multifamily_architecture(model)
    assert report["ok"] is False
    assert any("stairs not designed" in e for e in report["errors"])
    assert any("interior walls not constructed" in e for e in report["errors"])
    assert any("door swings not detailed" in e for e in report["errors"])
    with pytest.raises(ValueError, match="Architectural drawing rejected"):
        require_architectural_acceptance(model)
