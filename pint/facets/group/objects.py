"""
    pint.facets.group.objects
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Group class for unit grouping.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, FrozenSet, Optional, Set

if TYPE_CHECKING:
    from ...registry import UnitRegistry


class Group:
    """A group of units.

    Groups are used to organize units into logical categories.
    """

    def __init__(self, name: str, registry: Optional["UnitRegistry"] = None):
        self.name = name
        self._unit_names: Set[str] = set()
        self._used_groups: Set[str] = set()
        self._used_by: Set[str] = set()
        self._computed_members: Optional[FrozenSet[str]] = None

        if registry is not None:
            self._REGISTRY = registry
            # Register this group
            if hasattr(registry, "_groups"):
                registry._groups[name] = self
                # Add to root group's used_by
                if name != "root" and "root" in registry._groups:
                    registry._groups["root"]._used_groups.add(name)
                    self._used_by.add("root")

    def add_units(self, *names: str) -> None:
        """Add units to this group."""
        for name in names:
            self._unit_names.add(name)
        self.invalidate_members()

    def add_groups(self, *names: str) -> None:
        """Add other groups to this group."""
        for name in names:
            # Check for cycles
            if name == self.name:
                raise ValueError(f"Cannot add group '{name}' to itself")
            if hasattr(self, "_REGISTRY"):
                if name in self._REGISTRY._groups:
                    other = self._REGISTRY._groups[name]
                    if self.name in other._used_groups:
                        raise ValueError(f"Adding group '{name}' would create a cycle")
                    # Check transitive cycles
                    if hasattr(other, "_used_by") and self.name in other._used_by:
                        raise ValueError(f"Adding group '{name}' would create a cycle")
            self._used_groups.add(name)
        self.invalidate_members()

    def invalidate_members(self) -> None:
        """Invalidate the cached members."""
        self._computed_members = None
        # Also invalidate parent groups
        if hasattr(self, "_REGISTRY"):
            for parent_name in self._used_by:
                if parent_name in self._REGISTRY._groups:
                    self._REGISTRY._groups[parent_name].invalidate_members()

    @property
    def members(self) -> FrozenSet[str]:
        """Return all members of this group, including from subgroups."""
        if self._computed_members is not None:
            return self._computed_members

        members = set(self._unit_names)

        # Add members from used groups
        if hasattr(self, "_REGISTRY"):
            for group_name in self._used_groups:
                if group_name in self._REGISTRY._groups:
                    members.update(self._REGISTRY._groups[group_name].members)

        self._computed_members = frozenset(members)
        return self._computed_members

    @classmethod
    def from_lines(
        cls,
        lines: list[str],
        define_func: Optional[Callable] = None,
        non_int_type: type = float,
    ) -> "Group":
        """Create a group from definition lines."""
        # Import here to avoid circular imports
        from ... import get_application_registry

        # Parse the @group line
        header = lines[0].strip()
        if not header.startswith("@group"):
            raise ValueError("Group definition must start with @group")

        # Parse name and using clause
        parts = header[6:].strip()
        using_groups = []

        if "using" in parts:
            name_part, using_part = parts.split("using", 1)
            name = name_part.strip()
            using_groups = [g.strip() for g in using_part.strip().split(",")]
        else:
            name = parts.strip()

        registry = get_application_registry()
        group = cls(name, registry)

        for group_name in using_groups:
            group.add_groups(group_name)

        # Parse unit definitions
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse unit definition like "meter = 2" or just "meter"
            if "=" in line:
                parts = line.split("=", 1)
                unit_name = parts[0].strip()
                # If there's a definition, call define_func
                if define_func is not None:
                    # Create a simple unit definition object
                    from ...facets.plain.definitions import UnitDefinition

                    ud = UnitDefinition(name=unit_name)
                    define_func(ud)
            else:
                unit_name = line.strip()

            group.add_units(unit_name)

        return group
