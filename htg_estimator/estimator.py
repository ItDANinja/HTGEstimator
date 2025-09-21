"""Core estimation logic for HTG Pro Services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .market_data import MarketRate, get_market_rate
from .models import (
    DEFAULT_INTERNAL_LABOR_RATE,
    STAGE_SURCHARGE_PER_RETURN,
    Attachment,
    MaterialItem,
    ProjectInput,
    RangeValue,
    ServiceInput,
)


@dataclass(slots=True)
class MaterialCostDetail:
    item: MaterialItem
    cost: RangeValue


@dataclass(slots=True)
class ServiceEstimate:
    service: ServiceInput
    total_hours: RangeValue
    htg_labor: RangeValue
    market_labor: Optional[RangeValue]
    market_source: Optional[str]
    materials_total: RangeValue
    materials_detail: List[MaterialCostDetail]
    stage_surcharge: float

    def stage_surcharge_range(self) -> RangeValue:
        if self.stage_surcharge <= 0:
            return RangeValue.zero()
        return RangeValue(self.stage_surcharge, self.stage_surcharge)

    def total_cost_range(self) -> RangeValue:
        total = self.htg_labor + self.materials_total
        if self.stage_surcharge > 0:
            total += self.stage_surcharge_range()
        return total


@dataclass(slots=True)
class ProjectEstimate:
    project: ProjectInput
    services: List[ServiceEstimate]
    generated_on: str

    def total_labor(self) -> RangeValue:
        total = RangeValue.zero()
        for service in self.services:
            total += service.htg_labor
        return total

    def total_materials(self) -> RangeValue:
        total = RangeValue.zero()
        for service in self.services:
            total += service.materials_total
        return total

    def total_stage_surcharge(self) -> float:
        return sum(service.stage_surcharge for service in self.services)

    def total_cost(self) -> RangeValue:
        total = RangeValue.zero()
        for service in self.services:
            total += service.total_cost_range()
        return total

    @property
    def attachments(self) -> List[Attachment]:
        return self.project.attachments


class Estimator:
    """Primary interface for generating project estimates."""

    def __init__(
        self,
        labor_rate: float = DEFAULT_INTERNAL_LABOR_RATE,
        stage_surcharge_per_return: float = STAGE_SURCHARGE_PER_RETURN,
    ) -> None:
        self.labor_rate = labor_rate
        self.stage_surcharge_per_return = stage_surcharge_per_return

    def build_estimate(self, project: ProjectInput) -> ProjectEstimate:
        services = [self._estimate_service(service) for service in project.services]
        from datetime import date

        return ProjectEstimate(
            project=project,
            services=services,
            generated_on=date.today().isoformat(),
        )

    # -- Internal helpers -------------------------------------------------
    def _estimate_service(self, service: ServiceInput) -> ServiceEstimate:
        total_hours = RangeValue.zero()
        for phase in service.breakdown:
            total_hours += phase.hours

        htg_labor = total_hours.scale(self.labor_rate)

        market_rate = self._resolve_market_rate(service)
        market_labor_range: Optional[RangeValue] = None
        market_source: Optional[str] = None
        if market_rate:
            market_labor_range = total_hours.scale(market_rate.low_rate, market_rate.high_rate)
            market_source = market_rate.formatted_source()

        materials_detail = [
            MaterialCostDetail(item=item, cost=item.total_cost_range()) for item in service.materials
        ]
        materials_total = RangeValue.zero()
        for detail in materials_detail:
            materials_total += detail.cost

        stage_surcharge = float(service.stage_returns or 0) * self.stage_surcharge_per_return

        return ServiceEstimate(
            service=service,
            total_hours=total_hours,
            htg_labor=htg_labor,
            market_labor=market_labor_range,
            market_source=market_source,
            materials_total=materials_total,
            materials_detail=materials_detail,
            stage_surcharge=stage_surcharge,
        )

    def _resolve_market_rate(self, service: ServiceInput) -> Optional[MarketRate]:
        if service.market_rate_override is not None:
            # Interpret override as an hourly rate range
            return MarketRate(
                low_rate=service.market_rate_override.low,
                high_rate=service.market_rate_override.high,
                source="Client-supplied market override",
            )
        return get_market_rate(service.service_type)

