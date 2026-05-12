"""Group and System classes for organizing units."""


class Group:
    """A named collection of units."""

    __slots__ = ("_name", "_unit_names", "_using", "_registry")

    def __init__(self, name, unit_names=(), using=(), registry=None):
        self._name = name
        self._unit_names = frozenset(unit_names)
        self._using = tuple(using)
        self._registry = registry

    @property
    def name(self):
        return self._name

    @property
    def members(self):
        result = set(self._unit_names)
        if self._registry is not None:
            for group_name in self._using:
                group = self._registry.get_group(group_name)
                if group is not None:
                    result |= group.members
        return frozenset(result)

    def __contains__(self, unit_name):
        return unit_name in self.members

    def __repr__(self):
        return f"<Group('{self._name}')>"


class System:
    """A unit system defining preferred base units for each dimension."""

    __slots__ = ("_name", "_base_units", "_rules", "_using", "_registry")

    def __init__(self, name, base_units=(), rules=(), using=(), registry=None):
        self._name = name
        self._base_units = tuple(base_units)
        self._rules = dict(rules)
        self._using = tuple(using)
        self._registry = registry

    @property
    def name(self):
        return self._name

    @property
    def members(self):
        result = set()
        if self._registry is not None:
            for group_name in self._using:
                group = self._registry.get_group(group_name)
                if group is not None:
                    result |= group.members
        for u in self._base_units:
            result.add(u)
        return frozenset(result)

    @property
    def base_units(self):
        return self._base_units

    @property
    def rules(self):
        return dict(self._rules)

    def __repr__(self):
        return f"<System('{self._name}')>"
