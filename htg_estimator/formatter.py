"""Formatting helpers that generate client-ready estimate text."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Sequence

from .estimator import MaterialCostDetail, ProjectEstimate, ServiceEstimate
from .models import RangeValue

DEFAULT_ASSUMPTIONS = [
    "Quantities based on client-supplied drawings/measurements; HTG to field-verify prior to mobilization.",
    "Normal work hours (Mon–Fri, 8a–5p) with clear access for crew and material deliveries.",
]

DEFAULT_EXCLUSIONS = [
    "Permit, impact, or utility fees unless specifically added to scope.",
    "Unforeseen conditions including structural damage, mold, rot, or hazardous material remediation.",
    "Design, engineering, specialty inspections, or third-party testing beyond standard AHJ requirements.",
    "After-hours, weekend, or holiday labor premiums unless noted.",
]

DEFAULT_CLOSING_NOTES = [
    "Changes to scope or unforeseen site conditions may require a written change order adjusting labor and materials.",
    "Estimate prepared in good faith and valid for 14 days due to material volatility.",
]


def format_estimate(project_estimate: ProjectEstimate) -> str:
    """Create a markdown-formatted estimate document."""

    project = project_estimate.project
    lines: List[str] = []
    lines.append("# HTG Pro Services — Preliminary Estimate")
    lines.append("")
    lines.append(f"**Client:** {project.client_name}")
    if project.project_address:
        lines.append(f"**Project Location:** {project.project_address}")
    lines.append(f"**Prepared:** {datetime.fromisoformat(project_estimate.generated_on).strftime('%B %d, %Y')}")
    if project.request_description:
        lines.append("")
        lines.append(f"**Client Request Summary:** {project.request_description.strip()}")
    if project.site_conditions:
        lines.append("")
        lines.append("**Site Conditions / Constraints:**")
        for item in project.site_conditions:
            lines.append(f"- {item}")
    if project_estimate.attachments:
        lines.append("")
        lines.append("**Reference Files Received:**")
        for attachment in project_estimate.attachments:
            desc = f" ({attachment.description})" if attachment.description else ""
            lines.append(f"- {attachment.kind.title()}: {attachment.path}{desc}")

    for service in project_estimate.services:
        lines.append("")
        lines.extend(_format_service_section(service))

    lines.append("")
    lines.append("## Totals Summary — All Services")
    lines.append(_build_totals_table(project_estimate))

    lines.append("")
    lines.append("## Change Orders & Validity")
    for note in DEFAULT_CLOSING_NOTES:
        lines.append(f"- {note}")

    clarifying_questions = list(project.clarifying_questions)
    clarifying_questions.extend(_generate_follow_up_questions(project_estimate))
    if clarifying_questions:
        deduped = _unique(clarifying_questions)
        lines.append("")
        lines.append("## Clarifying Questions")
        for question in deduped:
            lines.append(f"- {question}")

    return "\n".join(lines)


def _format_service_section(service: ServiceEstimate) -> List[str]:
    lines: List[str] = []
    svc = service.service
    lines.append(f"## {svc.name}")

    lines.append("**Scope & Breakdown**")
    if svc.breakdown:
        for phase in svc.breakdown:
            description = phase.description.strip() if phase.description else ""
            detail = f" — {description}" if description else ""
            lines.append(f"- {phase.phase}: {phase.hours.format_hours()}{detail}")
    else:
        lines.append("- Labor plan to be confirmed; allowance shown below.")

    assumption_lines = _unique(DEFAULT_ASSUMPTIONS + list(svc.assumptions))
    if svc.permit_required:
        assumption_lines.append("Based on scope, a building permit may be required; coordination available upon request.")
    if svc.notes:
        assumption_lines.append(svc.notes)
    lines.append("")
    lines.append("**Assumptions**")
    for assumption in assumption_lines:
        lines.append(f"- {assumption}")

    exclusion_lines = _unique(DEFAULT_EXCLUSIONS + list(svc.exclusions))
    if svc.permit_required:
        exclusion_lines.append("Permit procurement fees are excluded unless added by change order.")
    lines.append("")
    lines.append("**Exclusions**")
    for exclusion in exclusion_lines:
        lines.append(f"- {exclusion}")

    lines.append("")
    lines.append("**Pricing Ranges**")
    lines.append(_build_pricing_table(service))

    if service.materials_detail:
        lines.append("")
        lines.append("**Materials Detail**")
        lines.append(_build_materials_table(service.materials_detail))
        lines.append("*Unit costs include default 12% waste and 5% price-drift buffer unless otherwise noted.*")

    lines.append("")
    lines.append("**Totals Summary**")
    lines.append(_build_service_totals_table(service))

    return lines


def _build_pricing_table(service: ServiceEstimate) -> str:
    headers = ["Option", "Hours", "Cost / Notes"]
    rows: List[List[str]] = []

    hours_text = service.total_hours.format_hours()
    rows.append([
        "A. HTG Labor @ $90/hr",
        hours_text,
        f"{service.htg_labor.format_currency()} (90 × hours)",
    ])

    if service.market_labor is not None:
        market_note = service.market_labor.format_currency()
        if service.market_source:
            market_note += f"\nSource: {service.market_source}"
    else:
        market_note = "No published Orlando labor-only data for this scope."
        if service.service.market_rate_override is not None:
            market_note = "Client-provided market override applied."
    rows.append([
        "B. Orlando Market Labor",
        hours_text,
        market_note,
    ])

    material_note = service.materials_total.format_currency()
    if not service.materials_detail:
        material_note += " (Allowance — no specific selections provided)"
    rows.append([
        "C. Materials Estimate",
        "—",
        material_note,
    ])

    return _build_table(headers, rows)


def _build_materials_table(materials: Sequence[MaterialCostDetail]) -> str:
    headers = ["Item", "Qty", "Unit Cost (Low–High)", "Extended (Low–High)", "Notes"]
    rows: List[List[str]] = []
    for detail in materials:
        item = detail.item
        unit_high = item.normalized_unit_cost_high
        unit_range = RangeValue(item.unit_cost_low, unit_high).format_currency()
        total_range = detail.cost.format_currency()
        notes = item.notes or ""
        rows.append([
            item.name,
            item.quantity_display(),
            unit_range,
            total_range,
            notes,
        ])
    return _build_table(headers, rows)


def _build_service_totals_table(service: ServiceEstimate) -> str:
    headers = ["Component", "Low", "High"]
    rows: List[List[str]] = []
    rows.append([
        "HTG Labor @ $90/hr",
        f"${service.htg_labor.low:,.2f}",
        f"${service.htg_labor.high:,.2f}",
    ])
    rows.append([
        "Materials",
        f"${service.materials_total.low:,.2f}",
        f"${service.materials_total.high:,.2f}",
    ])
    if service.stage_surcharge > 0:
        returns = service.service.stage_returns
        label = "return" if returns == 1 else "returns"
        rows.append([
            f"Stage surcharge ({returns} {label} × $50)",
            f"${service.stage_surcharge:,.2f}",
            f"${service.stage_surcharge:,.2f}",
        ])
    total_range = service.total_cost_range()
    rows.append([
        "Service Total",
        f"${total_range.low:,.2f}",
        f"${total_range.high:,.2f}",
    ])
    return _build_table(headers, rows)


def _build_totals_table(project: ProjectEstimate) -> str:
    headers = ["Component", "Low", "High"]
    rows: List[List[str]] = []
    labor_total = project.total_labor()
    materials_total = project.total_materials()
    stage_total = project.total_stage_surcharge()
    rows.append([
        "HTG Labor @ $90/hr",
        f"${labor_total.low:,.2f}",
        f"${labor_total.high:,.2f}",
    ])
    rows.append([
        "Materials",
        f"${materials_total.low:,.2f}",
        f"${materials_total.high:,.2f}",
    ])
    if stage_total > 0:
        rows.append([
            "Stage surcharge",
            f"${stage_total:,.2f}",
            f"${stage_total:,.2f}",
        ])
    grand_total = project.total_cost()
    rows.append([
        "Grand Total",
        f"${grand_total.low:,.2f}",
        f"${grand_total.high:,.2f}",
    ])
    return _build_table(headers, rows)


def _build_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    def _format_row(row: Sequence[str]) -> str:
        return "| " + " | ".join(str(cell).ljust(widths[idx]) for idx, cell in enumerate(row)) + " |"

    separator = "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |"
    lines = [_format_row(headers), separator]
    for row in rows:
        lines.append(_format_row(row))
    return "\n".join(lines)


def _generate_follow_up_questions(project: ProjectEstimate) -> List[str]:
    questions: List[str] = []
    for service in project.services:
        if service.service.stage_returns > 0:
            questions.append(
                f"Please confirm sequencing and downtime between the {service.service.stage_returns + 1} planned mobilizations for {service.service.name}."
            )
        if not service.materials_detail:
            questions.append(f"Provide finish selections or allowance targets for {service.service.name} materials so we can firm pricing.")
    if not project.project.site_conditions:
        questions.append("Let us know about any HOA/COA rules, parking limits, or quiet hours that could impact scheduling.")
    questions.append("Confirm that power, water, and restroom access will be available to the crew during working hours.")
    return questions


def _unique(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)
    return result

