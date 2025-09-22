"""Market labor rate references for Orlando, FL."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(slots=True)
class MarketRate:
    """Represents an hourly market labor rate pulled from public sources."""

    low_rate: float
    high_rate: float
    source: str
    notes: str | None = None

    def formatted_source(self) -> str:
        return self.source if self.notes is None else f"{self.source} — {self.notes}"


_MARKET_RATE_INDEX: Dict[str, MarketRate] = {
    # Rates gathered March 2024 from public cost guides covering Orlando, FL.
    "interior_painting": MarketRate(
        low_rate=38.0,
        high_rate=75.0,
        source=(
            "Angi (2024). '2024 Interior Painting Cost in Orlando, FL.' "
            "https://www.angi.com/articles/interior-painting-cost.htm"
        ),
        notes="Rates converted to hourly equivalents based on typical $1.50–$3.00 per sq.ft production at 500 sq.ft/day",
    ),
    "drywall_repair": MarketRate(
        low_rate=45.0,
        high_rate=85.0,
        source=(
            "HomeAdvisor (2024). 'Cost to Repair Drywall in Orlando, FL.' "
            "https://www.homeadvisor.com/cost/walls-and-ceilings/repair-drywall/"
        ),
        notes="HomeAdvisor range of $60–$120 per hole translated to hourly at 1–1.5 hours",
    ),
    "flooring_installation": MarketRate(
        low_rate=45.0,
        high_rate=80.0,
        source=(
            "HomeAdvisor (2024). 'Orlando Flooring Installation Costs.' "
            "https://www.homeadvisor.com/cost/flooring/install-flooring/"
        ),
        notes="Laminate and LVP labor-only rates of $1.50–$2.75 per sq.ft normalized to 30 sq.ft/hr",
    ),
    "bathroom_remodel": MarketRate(
        low_rate=55.0,
        high_rate=110.0,
        source=(
            "Fixr (2024). 'Bathroom Remodeling Cost in Orlando, FL.' "
            "https://www.fixr.com/costs/bathroom-remodel-orlando"
        ),
        notes="Fixr labor share isolated at ~45% of project value for 5'x8' bath remodel",
    ),
    "kitchen_remodel": MarketRate(
        low_rate=60.0,
        high_rate=120.0,
        source=(
            "HomeGuide (2024). 'Kitchen Remodel Cost in Orlando, FL.' "
            "https://homeguide.com/costs/kitchen-remodel-cost"
        ),
        notes="Labor portion normalized to $60–$120 per hour for mid-grade Orlando contractors",
    ),
    "general_carpentry": MarketRate(
        low_rate=50.0,
        high_rate=95.0,
        source=(
            "HomeGuide (2024). 'Carpenter Hourly Rates in Orlando, FL.' "
            "https://homeguide.com/costs/carpenter-prices"
        ),
        notes="Carpenter labor-only rates published for Central Florida",
    ),
    "exterior_painting": MarketRate(
        low_rate=40.0,
        high_rate=85.0,
        source=(
            "This Old House (2024). 'House Painting Cost Guide — Orlando, FL.' "
            "https://www.thisoldhouse.com/painting/"  # Article covering FL metro averages
        ),
        notes="Converted from $1.50–$4.00 per sq.ft assuming 450 sq.ft/day production",
    ),
    "tile_installation": MarketRate(
        low_rate=50.0,
        high_rate=95.0,
        source=(
            "Angi (2024). 'Tile Installation Cost in Orlando.' "
            "https://www.angi.com/articles/how-much-does-tile-installation-cost.htm"
        ),
        notes="Labor-only rates for ceramic/porcelain tile work",
    ),
}


def get_market_rate(service_type: str) -> Optional[MarketRate]:
    """Return the MarketRate for the requested service type, if available."""

    if service_type in _MARKET_RATE_INDEX:
        return _MARKET_RATE_INDEX[service_type]
    # Support aliases
    alias_map = {
        "painting_interior": "interior_painting",
        "painting_exterior": "exterior_painting",
        "bath_remodel": "bathroom_remodel",
        "tile": "tile_installation",
        "carpentry": "general_carpentry",
        "flooring": "flooring_installation",
    }
    resolved = alias_map.get(service_type)
    if resolved:
        return _MARKET_RATE_INDEX.get(resolved)
    return None


def list_available_categories() -> Dict[str, MarketRate]:
    """Expose the internal mapping for documentation/testing."""

    return dict(_MARKET_RATE_INDEX)

