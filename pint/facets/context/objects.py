"""
    pint.facets.context.objects
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Context class for unit conversions.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union

from ...util import UnitsContainer

if TYPE_CHECKING:
    from ...registry import UnitRegistry


class Context:
    """A context for enabling special unit conversions.

    Contexts are used to allow conversions between incompatible units
    through user-defined transformation functions.
    """

    def __init__(
        self,
        name: str,
        aliases: Tuple[str, ...] = (),
        defaults: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.aliases = aliases
        self.defaults = defaults or {}
        self._funcs: Dict[
            Tuple[UnitsContainer, UnitsContainer],
            Callable,
        ] = {}
        self._relations: list = []

    @property
    def graph(self):
        """Return the transformation graph for this context."""
        g = defaultdict(set)
        for (src, dst) in self._funcs.keys():
            g[src].add(dst)
        return g

    def add_transformation(
        self,
        src: UnitsContainer,
        dst: UnitsContainer,
        func: Callable,
    ) -> None:
        """Add a transformation function between two unit types."""
        self._funcs[(src, dst)] = func

    def transform(
        self,
        src: UnitsContainer,
        dst: UnitsContainer,
        registry: "UnitRegistry",
        value: Any,
        **kwargs,
    ) -> Any:
        """Transform a value between two unit types."""
        # Merge defaults with provided kwargs
        ctx_kwargs = dict(self.defaults)
        ctx_kwargs.update(kwargs)

        func = self._funcs.get((src, dst))
        if func is None:
            raise KeyError(f"No transformation from {src} to {dst}")

        import inspect

        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        if len(params) == 2:
            # (ureg, value) signature
            return func(registry, value)
        else:
            # (ureg, value, **kwargs) signature
            return func(registry, value, **ctx_kwargs)

    @classmethod
    def from_lines(
        cls,
        lines: list[str],
        to_base_func: Optional[Callable] = None,
        non_int_type: type = float,
    ) -> "Context":
        """Create a context from definition lines."""
        # Parse the @context line
        header = lines[0].strip()
        if not header.startswith("@context"):
            raise ValueError("Context definition must start with @context")

        # Parse name and defaults
        parts = header[8:].strip().split("=")
        name_parts = parts[0].strip().split()
        name = name_parts[0]
        aliases = tuple(name_parts[1:]) if len(name_parts) > 1 else ()

        defaults = {}
        if len(parts) > 1:
            # Parse defaults from the rest of the line
            for i in range(1, len(parts)):
                if ":" in parts[i]:
                    break
                default_str = parts[i].strip()
                if "," in default_str:
                    default_str = default_str.split(",")[0].strip()
                # Parse key=value
                if "=" in default_str:
                    k, v = default_str.split("=", 1)
                    defaults[k.strip()] = non_int_type(v.strip())

        ctx = cls(name, aliases, defaults)

        # Parse transformation rules
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Parse transformation rules like "[length] -> [time]: speed_of_light / value"
            # This is a simplified implementation

        return ctx

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Context):
            return self.name == other.name
        return NotImplemented
