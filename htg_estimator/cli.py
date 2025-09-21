"""Command line entry point for HTG Estimator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import yaml

from .estimator import Estimator
from .formatter import format_estimate
from .parser import load_project


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="htg-estimator",
        description="Generate construction estimates using HTG Pro Services rules.",
    )
    subparsers = parser.add_subparsers(dest="command")

    estimate_parser = subparsers.add_parser("estimate", help="Build an estimate from an input file")
    estimate_parser.add_argument("input", help="Path to JSON or YAML file describing the client's request")
    estimate_parser.add_argument(
        "--output",
        "-o",
        help="Optional file path to write the formatted estimate (defaults to stdout)",
    )
    estimate_parser.add_argument(
        "--suppress-stdout",
        action="store_true",
        help="Skip printing to stdout when --output is provided.",
    )

    sample_parser = subparsers.add_parser("sample", help="Print a sample request template")
    sample_parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Output format for the template",
    )

    args = parser.parse_args()

    if args.command == "estimate":
        project = load_project(args.input)
        estimator = Estimator()
        project_estimate = estimator.build_estimate(project)
        content = format_estimate(project_estimate)
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
        if not args.output or not args.suppress_stdout:
            print(content)
        return

    if args.command == "sample":
        template = _build_sample_template()
        if args.format == "yaml":
            print(yaml.safe_dump(template, sort_keys=False))
        else:
            print(json.dumps(template, indent=2))
        return

    parser.print_help()


def _build_sample_template() -> Dict[str, Any]:
    return {
        "client_name": "Jane Smith",
        "project_address": "123 Orange Ave, Orlando, FL",
        "request_description": "Convert existing lanai into conditioned sunroom with new flooring and finishes.",
        "site_conditions": [
            "Occupied residence",
            "Limited driveway parking (2 vehicles)",
        ],
        "attachments": [
            {"path": "photos/lanai-existing.jpg", "kind": "photo", "description": "Existing lanai"},
            {"path": "drawings/sunroom-sketch.pdf", "kind": "drawing", "description": "Client sketch"},
        ],
        "services": [
            {
                "name": "Sunroom Conversion",
                "service_type": "general_carpentry",
                "breakdown": [
                    {"phase": "Prep", "description": "Protect adjacent interior and set dust control", "hours": {"low": 4, "high": 6}},
                    {"phase": "Demo", "description": "Remove screens, framing, and finishes", "hours": {"low": 10, "high": 14}},
                    {"phase": "Framing", "description": "Frame new walls, headers, and rough openings", "hours": {"low": 18, "high": 24}},
                    {"phase": "Rough-in", "description": "Coordinate electrical rough-in (allowance)", "hours": {"low": 6, "high": 8}},
                    {"phase": "Insulation", "description": "Install batt insulation and vapor barrier", "hours": {"low": 4, "high": 6}},
                    {"phase": "Drywall & Finish", "description": "Hang, finish, sand drywall", "hours": {"low": 16, "high": 22}},
                    {"phase": "Flooring", "description": "Install LVP flooring and base", "hours": {"low": 8, "high": 12}},
                    {"phase": "Trim & Paint", "description": "Install trim, caulk, and paint surfaces", "hours": {"low": 14, "high": 18}},
                    {"phase": "Cleanup", "description": "Final clean and punch support", "hours": {"low": 4, "high": 6}},
                ],
                "materials": [
                    {"name": "2x4 SPF Lumber", "quantity": 120, "unit": "lf", "unit_cost_low": 1.95, "unit_cost_high": 2.4},
                    {"name": "Drywall (1/2\" sheets)", "quantity": 20, "unit": "sheet", "unit_cost_low": 14.0, "unit_cost_high": 18.0},
                    {"name": "LVP Flooring", "quantity": 240, "unit": "sq.ft", "unit_cost_low": 2.85, "unit_cost_high": 4.25},
                    {"name": "Insulation Batts", "quantity": 220, "unit": "sq.ft", "unit_cost_low": 0.85, "unit_cost_high": 1.15},
                    {"name": "Paint & Sundries", "quantity": 1, "unit": "lot", "unit_cost_low": 280, "unit_cost_high": 420},
                ],
                "assumptions": [
                    "Electrical rough-in handled by licensed trade partner under separate allowance.",
                    "Existing slab is level and suitable for LVP install without extensive prep.",
                ],
                "exclusions": [
                    "HVAC load calculations or new system sizing.",
                    "Glazing upgrades beyond code minimums.",
                ],
                "stage_returns": 1,
                "permit_required": True,
            }
        ],
    }


if __name__ == "__main__":
    main()

