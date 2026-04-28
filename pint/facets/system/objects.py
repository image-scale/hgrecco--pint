"""
    pint.facets.system.objects
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    System class for unit systems.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, FrozenSet, Optional, Set

if TYPE_CHECKING:
    from ...registry import UnitRegistry


class System:
    """A system of units (like SI, CGS, etc.).

    Systems define a preferred set of base units for a given set of dimensions.
    """

    def __init__(self, name: str, registry: Optional["UnitRegistry"] = None):
        self.name = name
        self._base_units: dict = {}
        self._derived_units: set = set()
        self._used_groups: Set[str] = set()
        self._REGISTRY = registry

    @property
    def members(self) -> FrozenSet[str]:
        """Return the members (units) of this system."""
        result = set()
        if self._REGISTRY:
            for group_name in self._used_groups:
                if group_name in self._REGISTRY._groups:
                    group = self._REGISTRY._groups[group_name]
                    result.update(group.members)
            # Remove base units
            result -= set(self._base_units.keys())
        return frozenset(result)

    @classmethod
    def from_lines(
        cls,
        lines: list[str],
        get_root_func: Optional[Callable] = None,
        non_int_type: type = float,
    ) -> "System":
        """Create a system from definition lines."""
        from ... import get_application_registry

        # Parse the @system line
        header = lines[0].strip()
        if not header.startswith("@system"):
            raise ValueError("System definition must start with @system")

        # Parse name and using clause
        parts = header[7:].strip()
        using_groups = []

        if "using" in parts:
            name_part, using_part = parts.split("using", 1)
            name = name_part.strip()
            using_groups = [g.strip() for g in using_part.strip().split(",")]
        else:
            name = parts.strip()

        registry = get_application_registry()
        system = cls(name, registry)

        # Add root group by default
        system._used_groups.add("root")
        for group_name in using_groups:
            system._used_groups.add(group_name)

        # Parse base unit definitions
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse unit specification like "meter" or "meter: length"
            if ":" in line:
                unit_name, dimension = line.split(":", 1)
                system._base_units[unit_name.strip()] = dimension.strip()
            else:
                system._base_units[line.strip()] = None

        return system
