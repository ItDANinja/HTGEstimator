import json
from pathlib import Path

import pytest

from htg_estimator.estimator import Estimator
from htg_estimator.formatter import format_estimate
from htg_estimator.models import ProjectInput


@pytest.fixture()
def sample_request_dict() -> dict:
    sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample_request.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def test_estimator_calculations(sample_request_dict: dict) -> None:
    project = ProjectInput.from_dict(sample_request_dict)
    estimator = Estimator()
    project_estimate = estimator.build_estimate(project)
    assert len(project_estimate.services) == 1
    service = project_estimate.services[0]

    assert service.total_hours.low == pytest.approx(84.0)
    assert service.total_hours.high == pytest.approx(116.0)
    assert service.htg_labor.low == pytest.approx(7560.0)
    assert service.htg_labor.high == pytest.approx(10440.0)

    assert service.materials_total.low == pytest.approx(1958.04, rel=1e-4)
    assert service.materials_total.high == pytest.approx(2753.016, rel=1e-4)
    assert service.stage_surcharge == pytest.approx(50.0)

    total_range = service.total_cost_range()
    assert total_range.low == pytest.approx(9568.04, rel=1e-4)
    assert total_range.high == pytest.approx(13243.016, rel=1e-4)

    # Overall totals should mirror single service because only one scope present
    assert project_estimate.total_cost().low == pytest.approx(total_range.low, rel=1e-4)
    assert project_estimate.total_cost().high == pytest.approx(total_range.high, rel=1e-4)


def test_formatter_structure(sample_request_dict: dict) -> None:
    project = ProjectInput.from_dict(sample_request_dict)
    estimator = Estimator()
    project_estimate = estimator.build_estimate(project)
    output = format_estimate(project_estimate)

    # Key structural elements
    assert "# HTG Pro Services — Preliminary Estimate" in output
    assert "## Sunroom Conversion" in output
    assert "**Pricing Ranges**" in output
    assert "B. Orlando Market Labor" in output
    assert "Stage surcharge" in output
    assert "## Totals Summary — All Services" in output
    assert "## Change Orders & Validity" in output
    assert "## Clarifying Questions" in output

