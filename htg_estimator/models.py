"""Data models for HTG Estimator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

DEFAULT_INTERNAL_LABOR_RATE = 90.0
DEFAULT_MATERIAL_WASTE = 0.12  # 12% waste factor
DEFAULT_PRICE_DRIFT = 0.05  # 5% pricing volatility buffer
STAGE_SURCHARGE_PER_RETURN = 50.0


@dataclass(slots=True)
class RangeValue:
    """Represents a numeric low/high range."""

    low: float
    high: Optional[float] = None

    def __post_init__(self) -> None:
        if self.high is None:
            self.high = self.low
        if self.low > self.high:
            # Swap to keep ordering consistent
            self.low, self.high = self.high, self.low

    @classmethod
    def zero(cls) -> "RangeValue":
        return cls(0.0, 0.0)

    def copy(self) -> "RangeValue":
        return RangeValue(self.low, self.high)

    def __add__(self, other: "RangeValue") -> "RangeValue":
        return RangeValue(self.low + other.low, self.high + other.high)

    def __iadd__(self, other: "RangeValue") -> "RangeValue":
        self.low += other.low
        self.high += other.high
        return self

    def scale(self, low_factor: float, high_factor: Optional[float] = None) -> "RangeValue":
        if high_factor is None:
            high_factor = low_factor
        return RangeValue(self.low * low_factor, self.high * high_factor)

    def format_hours(self) -> str:
        return _format_range(self.low, self.high, suffix="hrs")

    def format_currency(self) -> str:
        return _format_range(self.low, self.high, prefix="$")

    def format_plain(self, suffix: str = "") -> str:
        return _format_range(self.low, self.high, suffix=suffix)


def _format_range(low: float, high: float, prefix: str = "", suffix: str = "") -> str:
    if abs(high - low) < 1e-6:
        return f"{prefix}{low:,.2f}{suffix}" if prefix or suffix else f"{low:,.2f}"
    return f"{prefix}{low:,.2f}{suffix}–{prefix}{high:,.2f}{suffix}" if prefix or suffix else f"{low:,.2f}–{high:,.2f}"


def parse_range(value: Any) -> RangeValue:
    """Normalize an incoming value into a RangeValue."""
    if isinstance(value, RangeValue):
        return value.copy()
    if isinstance(value, dict):
        low_raw = value.get("low", value.get("min", value.get("from")))
        high_raw = value.get("high", value.get("max", value.get("to")))
        if low_raw is None and high_raw is not None:
            low_raw = high_raw
        if low_raw is None:
            raise ValueError(f"Range object must include 'low'/'min' or 'high'/'max': {value!r}")
        low = float(low_raw)
        high = float(high_raw) if high_raw is not None else None
        return RangeValue(low, high)
    if isinstance(value, (int, float)):
        return RangeValue(float(value))
    if isinstance(value, Iterable):
        items = list(value)
        if not items:
            raise ValueError("Cannot parse an empty iterable into a range")
        if len(items) == 1:
            return RangeValue(float(items[0]))
        if len(items) >= 2:
            return RangeValue(float(items[0]), float(items[1]))
    raise TypeError(f"Unsupported range specification: {value!r}")


@dataclass(slots=True)
class Attachment:
    path: str
    kind: str = "photo"
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attachment":
        return cls(
            path=data.get("path", ""),
            kind=data.get("kind", data.get("type", "photo")),
            description=data.get("description"),
        )


@dataclass(slots=True)
class LaborPhase:
    phase: str
    description: str
    hours: RangeValue

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LaborPhase":
        phase = data.get("phase") or data.get("name") or "Task"
        description = data.get("description") or data.get("detail") or ""
        hours_value = data.get("hours") or {
            "low": data.get("hours_low"),
            "high": data.get("hours_high"),
        }
        hours = parse_range(hours_value)
        return cls(phase=phase, description=description, hours=hours)


@dataclass(slots=True)
class MaterialItem:
    name: str
    quantity: float
    unit_cost_low: float
    unit_cost_high: Optional[float] = None
    unit: Optional[str] = None
    waste_factor: Optional[float] = None
    price_drift: Optional[float] = None
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaterialItem":
        return cls(
            name=data.get("name", "Material"),
            quantity=float(data.get("quantity", 0.0)),
            unit_cost_low=float(data.get("unit_cost_low", data.get("unit_cost", 0.0))),
            unit_cost_high=(
                float(data.get("unit_cost_high"))
                if data.get("unit_cost_high") is not None
                else None
            ),
            unit=data.get("unit"),
            waste_factor=(float(data["waste_factor"]) if data.get("waste_factor") is not None else None),
            price_drift=(float(data["price_drift"]) if data.get("price_drift") is not None else None),
            notes=data.get("notes"),
        )

    @property
    def normalized_unit_cost_high(self) -> float:
        return self.unit_cost_high if self.unit_cost_high is not None else self.unit_cost_low

    def waste_multiplier(self) -> float:
        waste = DEFAULT_MATERIAL_WASTE if self.waste_factor is None else self.waste_factor
        return 1.0 + waste

    def drift_multiplier(self) -> float:
        drift = DEFAULT_PRICE_DRIFT if self.price_drift is None else self.price_drift
        return 1.0 + drift

    def adjusted_quantity(self) -> float:
        return self.quantity * self.waste_multiplier()

    def total_cost_range(self) -> RangeValue:
        adjusted_qty = self.adjusted_quantity()
        drift_mult = self.drift_multiplier()
        low_cost = adjusted_qty * self.unit_cost_low * drift_mult
        high_cost = adjusted_qty * self.normalized_unit_cost_high * drift_mult
        return RangeValue(low_cost, high_cost)

    def quantity_display(self) -> str:
        qty = f"{self.quantity:,.2f}".rstrip("0").rstrip(".")
        if self.unit:
            return f"{qty} {self.unit}"
        return qty


@dataclass(slots=True)
class ServiceInput:
    name: str
    service_type: str
    breakdown: list[LaborPhase] = field(default_factory=list)
    materials: list[MaterialItem] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    market_rate_override: Optional[RangeValue] = None
    stage_returns: int = 0
    permit_required: Optional[bool] = None
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceInput":
        breakdown_data = data.get("breakdown") or []
        if not breakdown_data and (data.get("labor_hours") is not None or data.get("hours") is not None):
            hours_value = data.get("labor_hours", data.get("hours"))
            description = data.get("labor_description") or data.get("description") or "General labor"
            breakdown_data = [
                {
                    "phase": data.get("default_phase", "Install"),
                    "description": description,
                    "hours": hours_value,
                }
            ]
        materials_data = data.get("materials") or []
        market_override_data = data.get("market_rate_override") or data.get("market_labor_rate")
        return cls(
            name=data.get("name", "Service"),
            service_type=data.get("service_type", data.get("category", "general_contracting")),
            breakdown=[LaborPhase.from_dict(item) for item in breakdown_data],
            materials=[MaterialItem.from_dict(item) for item in materials_data],
            assumptions=list(data.get("assumptions", [])),
            exclusions=list(data.get("exclusions", [])),
            market_rate_override=(parse_range(market_override_data) if market_override_data else None),
            stage_returns=int(data.get("stage_returns", data.get("extra_site_visits", 0) or 0)),
            permit_required=data.get("permit_required"),
            notes=data.get("notes"),
        )


@dataclass(slots=True)
class ProjectInput:
    client_name: str
    project_address: Optional[str]
    request_description: Optional[str]
    services: list[ServiceInput]
    attachments: list[Attachment] = field(default_factory=list)
    site_conditions: list[str] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectInput":
        services = [ServiceInput.from_dict(item) for item in data.get("services", [])]
        if not services:
            raise ValueError("At least one service must be provided to build an estimate.")
        attachments = [Attachment.from_dict(item) for item in data.get("attachments", [])]
        site_conditions = list(data.get("site_conditions", []))
        clarifying_questions = list(data.get("clarifying_questions", []))
        return cls(
            client_name=data.get("client_name", data.get("client", "Client")),
            project_address=data.get("project_address"),
            request_description=data.get("request_description", data.get("scope", "")),
            services=services,
            attachments=attachments,
            site_conditions=site_conditions,
            clarifying_questions=clarifying_questions,
        )

