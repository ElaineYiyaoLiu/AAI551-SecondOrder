"""AAI551 SecondOrder: validated policy inputs and mechanism assumptions.

Author: Elaine Liu, with AI development assistance. Units follow model_spec.md.
"""
from dataclasses import dataclass, asdict
from math import isfinite


def bounded(name, value, low, high):
    """Reject booleans, nonfinite values, and values outside a closed range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and in [{low}, {high}]")


@dataclass(frozen=True)
class EconomicScenario:
    """Economic conditions and policy; percentages are entered as 25, not .25."""
    name: str = "baseline_policy"
    substitution: float = 25
    productivity: float = 30
    speed: float = 10
    ubi: float = 0
    tax: float = 0

    def __post_init__(self):
        """Validate all fields before any simulation can run."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a nonempty string")
        for field, limit in zip(
            ("substitution", "productivity", "speed", "ubi", "tax"),
            (60, 100, 25, 2000, 40),
        ):
            bounded(field, getattr(self, field), 0, limit)

    def __str__(self):
        """Show policy units explicitly; dataclass also implements fieldwise equality."""
        return f"{self.name}: UBI ${self.ubi:g}/month, AI tax {self.tax:g}%"

    def to_dict(self):
        """Return a JSON-compatible copy of the configuration."""
        return asdict(self)


@dataclass(frozen=True)
class ModelAssumptions:
    """Research switches; defaults reproduce the upstream mechanism."""
    feedback: bool = True
    dividend: bool = True
    clipping: bool = True
    demand_strength: float = .42
    tax_adoption_penalty: float = .45

    def __post_init__(self):
        """Validate mechanism switches and the planned stress-test ranges."""
        for name in ("feedback", "dividend", "clipping"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        bounded("demand_strength", self.demand_strength, 0, .84)
        bounded("tax_adoption_penalty", self.tax_adoption_penalty, 0, .9)


if __name__ == "__main__":
    print(EconomicScenario())
