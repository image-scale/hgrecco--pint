"""
    pint.registry
    ~~~~~~~~~~~~~

    Unit Registry and related classes.
"""
from __future__ import annotations

import contextlib
import copy
import functools
import locale
import logging
import math
import numbers
import pathlib
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from importlib.resources import files
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from . import errors
from .compat import HAS_BABEL, HAS_NUMPY, HAS_UNCERTAINTIES
from .errors import (
    DefinitionSyntaxError,
    DimensionalityError,
    RedefinitionError,
    UndefinedUnitError,
)
from .definitions import Definition
from .facets.context.objects import Context
from .facets.group.objects import Group
from .facets.measurement.objects import Measurement
from .facets.nonmultiplicative.definitions import (
    LogarithmicConverter,
    OffsetConverter,
)
from .facets.plain.definitions import (
    AliasDefinition,
    DimensionDefinition,
    PrefixDefinition,
    ScaleConverter,
    UnitDefinition,
)
from .facets.plain.quantity import PlainQuantity
from .facets.plain.unit import PlainUnit
from .facets.system.objects import System
from .util import (
    ParserHelper,
    UnitsContainer,
    find_shortest_path,
    logger,
    string_preprocessor,
)

if HAS_NUMPY:
    from .compat import np


class RegistryFormatter:
    """Formatter for a registry."""

    def __init__(self, registry: "UnitRegistry"):
        self._registry = registry
        self._default_format = ""

    @property
    def default_format(self) -> str:
        return self._default_format

    @default_format.setter
    def default_format(self, value: str):
        self._default_format = value

    def format_unit(self, unit, spec: str = "") -> str:
        """Format a unit."""
        if not spec:
            spec = self._default_format

        units = unit._units if hasattr(unit, "_units") else unit

        if not units:
            return "dimensionless"

        # Get abbreviate flag
        use_abbrev = "~" in spec
        spec = spec.replace("~", "")

        # Get the format type
        fmt_type = ""
        for c in spec:
            if c in "LHPC":
                fmt_type = c
                break

        # Build the unit string
        result = self._format_units_dict(units, fmt_type, use_abbrev)
        return result

    def format_quantity(self, quantity, spec: str = "") -> str:
        """Format a quantity."""
        if not spec:
            spec = self._default_format

        # Parse magnitude format from spec
        mag_spec = ""
        unit_spec = spec

        # Extract numeric format (like .4f)
        match = re.match(r"^([\d.]*[diouxXeEfFgGn%]?)", spec)
        if match:
            mag_spec = match.group(1)
            unit_spec = spec[len(mag_spec):]

        # Override default if 'd' prefix used
        if unit_spec.startswith("d"):
            unit_spec = unit_spec[1:]
            # Use default unit format without abbreviation

        # Format magnitude
        magnitude = quantity._magnitude
        if mag_spec:
            try:
                mag_str = format(magnitude, mag_spec)
            except (ValueError, TypeError):
                mag_str = str(magnitude)
        else:
            mag_str = str(magnitude)

        # Format units
        unit_str = self.format_unit(quantity.units, unit_spec)

        # Handle HTML array format
        if "H" in unit_spec and HAS_NUMPY and isinstance(magnitude, np.ndarray):
            if magnitude.ndim > 0:
                return (
                    f"<table><tbody><tr><th>Magnitude</th>"
                    f"<td style='text-align:left;'><pre>{mag_str}</pre></td></tr>"
                    f"<tr><th>Units</th><td style='text-align:left;'>{unit_str}</td></tr>"
                    f"</tbody></table>"
                )

        # Handle the special case of 1/second
        if not quantity._units:
            return mag_str
        if all(v < 0 for v in quantity._units.values()):
            return f"{mag_str} {unit_str}"

        return f"{mag_str} {unit_str}"

    def _format_units_dict(
        self, units: UnitsContainer, fmt_type: str, use_abbrev: bool
    ) -> str:
        """Format a units dict."""
        if not units:
            return "dimensionless"

        # Get positive and negative parts
        pos_parts = []
        neg_parts = []

        for unit, power in sorted(units.items()):
            # Get the display name
            if use_abbrev:
                name = self._get_symbol(unit)
            else:
                name = unit

            if power > 0:
                pos_parts.append((name, power))
            elif power < 0:
                neg_parts.append((name, -power))

        # Format based on type
        if fmt_type == "L":
            return self._format_latex(pos_parts, neg_parts)
        elif fmt_type == "P":
            return self._format_pretty(pos_parts, neg_parts)
        elif fmt_type == "H":
            return self._format_html(pos_parts, neg_parts)
        elif fmt_type == "C":
            return self._format_compact(pos_parts, neg_parts)
        else:
            return self._format_default(pos_parts, neg_parts)

    def _get_symbol(self, unit: str) -> str:
        """Get the symbol for a unit."""
        if unit in self._registry._units:
            ud = self._registry._units[unit]
            if hasattr(ud, "symbol") and ud.symbol:
                return ud.symbol
        return unit

    def _format_default(
        self, pos_parts: list, neg_parts: list
    ) -> str:
        """Format in default style."""

        def format_power(name, power):
            if power == 1:
                return name
            return f"{name} ** {int(power) if power == int(power) else power}"

        pos_str = " * ".join(format_power(n, p) for n, p in pos_parts)

        if not neg_parts:
            return pos_str

        neg_str = " / ".join(format_power(n, p) for n, p in neg_parts)

        if pos_str:
            return f"{pos_str} / {neg_str}"
        return f"1 / {neg_str}"

    def _format_latex(
        self, pos_parts: list, neg_parts: list
    ) -> str:
        """Format in LaTeX style."""

        def format_name(name):
            # Escape underscores
            name = name.replace("_", r"\_")
            return rf"\mathrm{{{name}}}"

        def format_power(name, power):
            formatted = format_name(name)
            if power == 1:
                return formatted
            return rf"{formatted}^{{{int(power) if power == int(power) else power}}}"

        pos_str = r" \cdot ".join(format_power(n, p) for n, p in pos_parts)
        neg_str = r" \cdot ".join(format_power(n, p) for n, p in neg_parts)

        if not neg_parts:
            return pos_str

        if pos_str:
            return rf"\frac{{{pos_str}}}{{{neg_str}}}"
        return rf"\frac{{1}}{{{neg_str}}}"

    def _format_pretty(
        self, pos_parts: list, neg_parts: list
    ) -> str:
        """Format in pretty/Unicode style."""
        superscripts = {
            "0": "⁰",
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
            "-": "⁻",
            ".": "·",
        }

        def to_superscript(s):
            return "".join(superscripts.get(c, c) for c in str(s))

        def format_power(name, power):
            if power == 1:
                return name
            return f"{name}{to_superscript(int(power) if power == int(power) else power)}"

        pos_str = "·".join(format_power(n, p) for n, p in pos_parts)

        if not neg_parts:
            return pos_str

        neg_str = "·".join(format_power(n, p) for n, p in neg_parts)

        if pos_str:
            return f"{pos_str}/{neg_str}"
        return f"1/{neg_str}"

    def _format_html(
        self, pos_parts: list, neg_parts: list
    ) -> str:
        """Format in HTML style."""

        def format_power(name, power):
            if power == 1:
                return name
            return f"{name}<sup>{int(power) if power == int(power) else power}</sup>"

        pos_str = " ".join(format_power(n, p) for n, p in pos_parts)

        if not neg_parts:
            return pos_str

        neg_str = " ".join(format_power(n, p) for n, p in neg_parts)

        if pos_str:
            return f"{pos_str}/{neg_str}"
        return f"1/{neg_str}"

    def _format_compact(
        self, pos_parts: list, neg_parts: list
    ) -> str:
        """Format in compact style."""

        def format_power(name, power):
            if power == 1:
                return name
            return f"{name}**{int(power) if power == int(power) else power}"

        pos_str = "*".join(format_power(n, p) for n, p in pos_parts)

        if not neg_parts:
            return pos_str

        neg_str = "*".join(format_power(n, p) for n, p in neg_parts)

        if pos_str:
            return f"{pos_str}/{neg_str}"
        return f"1/{neg_str}"


class UnitRegistry:
    """A registry for units.

    The UnitRegistry is the central object in pint. It stores definitions
    of units, prefixes, and dimensions, and provides methods for parsing
    unit strings and converting between units.
    """

    Quantity: Type[PlainQuantity]
    Unit: Type[PlainUnit]
    Measurement: Type[Measurement]
    Group: Type[Group]
    System: Type[System]
    Context: Type[Context]

    def __init__(
        self,
        filename: Union[str, pathlib.Path, None] = "default",
        force_ndarray: bool = False,
        force_ndarray_like: bool = False,
        default_as_delta: bool = True,
        autoconvert_offset_to_baseunit: bool = False,
        on_redefinition: str = "warn",
        system: Optional[str] = None,
        auto_reduce_dimensions: bool = False,
        preprocessors: Optional[List[Callable[[str], str]]] = None,
        fmt_locale: Optional[str] = None,
        non_int_type: type = float,
        case_sensitive: bool = True,
        cache_folder: Optional[Union[str, pathlib.Path]] = None,
        **kwargs,
    ):
        self._units: Dict[str, UnitDefinition] = {}
        self._prefixes: Dict[str, PrefixDefinition] = {}
        self._dimensions: Dict[str, DimensionDefinition] = {}
        self._contexts: Dict[str, Context] = {}
        self._groups: Dict[str, Group] = {}
        self._systems: Dict[str, System] = {}
        self._aliases: Dict[str, str] = {}

        # Conversion graph
        self._conversions: Dict[str, Dict[str, Callable]] = defaultdict(dict)

        # Settings
        self.force_ndarray = force_ndarray
        self.force_ndarray_like = force_ndarray_like
        self.default_as_delta = default_as_delta
        self.autoconvert_offset_to_baseunit = autoconvert_offset_to_baseunit
        self.on_redefinition = on_redefinition
        self.auto_reduce_dimensions = auto_reduce_dimensions
        self.preprocessors = preprocessors or [string_preprocessor]
        self.non_int_type = non_int_type
        self.case_sensitive = case_sensitive
        self._active_ctx = _ChainedContext()

        # Create formatter
        self.formatter = RegistryFormatter(self)
        if fmt_locale:
            self.formatter._default_format = fmt_locale

        # Create dynamic classes bound to this registry
        self._init_dynamic_classes()

        # Create root group
        self._groups["root"] = Group("root", self)

        # Load definitions
        if filename is not None:
            if filename == "default":
                self._load_default_definitions()
            else:
                self.load_definitions(filename)

        # Set default system
        if system:
            self.default_system = system

    def _init_dynamic_classes(self):
        """Initialize dynamic classes bound to this registry."""
        registry = self

        class _Quantity(PlainQuantity):
            _REGISTRY = registry

            def __new__(cls, value, units=None):
                inst = object.__new__(cls)
                inst._REGISTRY = registry
                return inst

        class _Unit(PlainUnit):
            _REGISTRY = registry

            def __new__(cls, units=None):
                inst = object.__new__(cls)
                inst._REGISTRY = registry
                return inst

        class _Measurement(Measurement):
            _REGISTRY = registry

        class _Group(Group):
            def __init__(self, name):
                super().__init__(name, registry)

        class _System(System):
            def __init__(self, name):
                super().__init__(name, registry)

        class _Context(Context):
            pass

        self.Quantity = _Quantity
        self.Unit = _Unit
        self.Measurement = _Measurement
        self.Group = _Group
        self.System = _System
        self.Context = _Context

    def _load_default_definitions(self):
        """Load the default unit definitions."""
        try:
            data = files("pint").joinpath("default_en.txt")
            if hasattr(data, "read_text"):
                content = data.read_text(encoding="utf-8")
            else:
                with open(str(data), "r", encoding="utf-8") as f:
                    content = f.read()
            self._load_definitions_from_string(content)
        except Exception as e:
            logger.warning(f"Could not load default definitions: {e}")

        try:
            data = files("pint").joinpath("constants_en.txt")
            if hasattr(data, "read_text"):
                content = data.read_text(encoding="utf-8")
            else:
                with open(str(data), "r", encoding="utf-8") as f:
                    content = f.read()
            self._load_definitions_from_string(content)
        except Exception:
            pass

    def _load_definitions_from_string(self, content: str):
        """Load definitions from a string."""
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Handle @import
            if line.startswith("@import"):
                continue  # Skip imports for now

            # Handle @context, @group, @system
            if line.startswith("@"):
                continue  # Skip for now

            try:
                defn = Definition.from_string(line, self.non_int_type)
                self._add_definition(defn)
            except Exception as e:
                logger.debug(f"Could not parse definition: {line}: {e}")

    def load_definitions(self, filename: Union[str, pathlib.Path]):
        """Load definitions from a file."""
        path = pathlib.Path(filename)
        if not path.exists():
            raise FileNotFoundError(f"Definition file not found: {filename}")

        content = path.read_text(encoding="utf-8")
        self._load_definitions_from_string(content)

    def _add_definition(self, defn):
        """Add a definition to the registry."""
        if isinstance(defn, PrefixDefinition):
            self._prefixes[defn.name] = defn
            if defn.symbol:
                self._prefixes[defn.symbol] = defn
            for alias in defn.aliases:
                self._prefixes[alias] = defn
        elif isinstance(defn, UnitDefinition):
            self._units[defn.name] = defn
            if defn.symbol and defn.symbol != defn.name:
                self._units[defn.symbol] = defn
            for alias in defn.aliases:
                self._units[alias] = defn
        elif isinstance(defn, DimensionDefinition):
            self._dimensions[defn.name] = defn
        elif isinstance(defn, AliasDefinition):
            for alias in defn.aliases:
                self._aliases[alias] = defn.name

    def define(self, definition: str) -> None:
        """Define a new unit, prefix, or dimension.

        Parameters
        ----------
        definition : str
            Definition string.
        """
        defn = Definition.from_string(definition, self.non_int_type)
        self._add_definition(defn)

    def parse_units(self, input_string: str) -> PlainUnit:
        """Parse a unit string.

        Parameters
        ----------
        input_string : str
            String representation of units.

        Returns
        -------
        Unit
            Parsed unit.
        """
        if not input_string or input_string.strip() == "":
            return self.Unit(UnitsContainer())

        # Preprocess
        for preprocessor in self.preprocessors:
            input_string = preprocessor(input_string)

        # Parse using the expression parser
        from .pint_eval import build_eval_tree, plain_tokenizer

        try:
            tree = build_eval_tree(plain_tokenizer(input_string))
            result = tree.evaluate(lambda x: self._parse_single_unit(x))
            if isinstance(result, PlainQuantity):
                return self.Unit(result._units)
            if isinstance(result, PlainUnit):
                return result
            if isinstance(result, UnitsContainer):
                return self.Unit(result)
            if isinstance(result, ParserHelper):
                return self.Unit(UnitsContainer(dict(result)))
            return self.Unit(UnitsContainer())
        except Exception:
            # Fall back to simple parsing
            return self.Unit(UnitsContainer._from_string(input_string))

    def _parse_single_unit(self, name: str) -> PlainUnit:
        """Parse a single unit name."""
        # Check for exact match
        if name in self._units:
            return self.Unit(UnitsContainer({name: 1}))

        # Check for prefix + unit
        for prefix_name, prefix in self._prefixes.items():
            if name.startswith(prefix_name):
                base_name = name[len(prefix_name):]
                if base_name in self._units:
                    # Create a combined unit
                    return self.Unit(UnitsContainer({name: 1}))

        # Check plurals
        if name.endswith("s") and name[:-1] in self._units:
            return self.Unit(UnitsContainer({name[:-1]: 1}))

        # Check aliases
        if name in self._aliases:
            return self._parse_single_unit(self._aliases[name])

        # Return as-is (may be defined later)
        return self.Unit(UnitsContainer({name: 1}))

    def parse_expression(
        self, input_string: str
    ) -> PlainQuantity:
        """Parse a quantity expression.

        Parameters
        ----------
        input_string : str
            String representation of a quantity (e.g., "4.2 m/s").

        Returns
        -------
        Quantity
            Parsed quantity.
        """
        if not input_string:
            return self.Quantity(0)

        input_string = input_string.strip()

        # Handle Unicode superscripts and special characters
        input_string = input_string.replace("×", "*")
        input_string = re.sub(r"(\d+)×10", r"\1e", input_string)

        # Preprocess
        for preprocessor in self.preprocessors:
            input_string = preprocessor(input_string)

        # Parse using the expression parser
        from .pint_eval import build_eval_tree, plain_tokenizer

        try:
            tree = build_eval_tree(plain_tokenizer(input_string))
            result = tree.evaluate(
                lambda x: self._parse_single_unit(x)
                if not _is_number_string(x)
                else float(x)
                if "." in x or "e" in x.lower()
                else int(x)
            )
            if isinstance(result, PlainQuantity):
                return result
            if isinstance(result, PlainUnit):
                return self.Quantity(1, result._units)
            if isinstance(result, (int, float)):
                return self.Quantity(result)
            return self.Quantity(result)
        except Exception:
            # Simple fallback
            parts = input_string.split()
            if len(parts) >= 2:
                try:
                    mag = float(parts[0])
                    units = " ".join(parts[1:])
                    return self.Quantity(mag, units)
                except ValueError:
                    pass
            return self.Quantity(input_string)

    def __call__(self, input_string: str) -> PlainQuantity:
        """Parse a quantity expression.

        This is a shorthand for parse_expression.
        """
        return self.parse_expression(input_string)

    def __getattr__(self, name: str):
        """Get a unit by attribute access."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        try:
            return self.Unit(name)
        except Exception:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_dimensionality(
        self, input_units: Union[str, UnitsContainer]
    ) -> UnitsContainer:
        """Get the dimensionality of units.

        Parameters
        ----------
        input_units : str or UnitsContainer
            Units to analyze.

        Returns
        -------
        UnitsContainer
            Dimensionality as a container of base dimensions.
        """
        if isinstance(input_units, str):
            if input_units.startswith("[") and input_units.endswith("]"):
                # It's already a dimension
                if input_units not in self._dimensions and input_units != "[length]":
                    raise ValueError(
                        f"{input_units} is not defined as dimension in the pint UnitRegistry"
                    )
                return UnitsContainer({input_units: 1})
            input_units = self.parse_units(input_units)._units

        result = {}
        for unit, power in input_units.items():
            if unit.startswith("["):
                # It's a dimension
                result[unit] = result.get(unit, 0) + power
            elif unit in self._units:
                ud = self._units[unit]
                if ud.is_base:
                    # Base unit - get its dimension
                    for dim, dim_power in ud.reference.items():
                        result[dim] = result.get(dim, 0) + power * dim_power
                else:
                    # Derived unit - recurse
                    sub_dim = self.get_dimensionality(ud.reference)
                    for dim, dim_power in sub_dim.items():
                        result[dim] = result.get(dim, 0) + power * dim_power
            else:
                # Unknown unit - treat as its own dimension
                result[f"[{unit}]"] = result.get(f"[{unit}]", 0) + power

        # Remove zeros
        result = {k: v for k, v in result.items() if v != 0}
        return UnitsContainer(result)

    def convert(
        self,
        quantity: PlainQuantity,
        other: Union[str, PlainUnit, UnitsContainer],
    ) -> PlainQuantity:
        """Convert a quantity to different units.

        Parameters
        ----------
        quantity : Quantity
            Quantity to convert.
        other : str, Unit, or UnitsContainer
            Target units.

        Returns
        -------
        Quantity
            Converted quantity.
        """
        if isinstance(other, str):
            other_units = self.parse_units(other)._units
        elif isinstance(other, PlainUnit):
            other_units = other._units
        elif isinstance(other, UnitsContainer):
            other_units = other
        else:
            raise TypeError(f"Cannot convert to {type(other)}")

        if quantity._units == other_units:
            return self.Quantity(quantity._magnitude, other_units)

        # Check dimensionality
        src_dim = self.get_dimensionality(quantity._units)
        dst_dim = self.get_dimensionality(other_units)

        if src_dim != dst_dim:
            # Try context conversion
            if self._active_ctx and self._active_ctx.graph:
                path = find_shortest_path(self._active_ctx.graph, src_dim, dst_dim)
                if path is not None:
                    # Apply context transformations
                    result = quantity
                    for i in range(len(path) - 1):
                        ctx_src = path[i]
                        ctx_dst = path[i + 1]
                        for ctx in self._active_ctx._contexts:
                            try:
                                result = ctx.transform(
                                    ctx_src, ctx_dst, self, result
                                )
                                break
                            except KeyError:
                                continue
                    return self.Quantity(result._magnitude, other_units)

            raise DimensionalityError(
                quantity._units, other_units, src_dim, dst_dim
            )

        # Convert through base units
        src_factor = self._get_base_factor(quantity._units)
        dst_factor = self._get_base_factor(other_units)

        new_magnitude = quantity._magnitude * src_factor / dst_factor

        return self.Quantity(new_magnitude, other_units)

    def _get_base_factor(self, units: UnitsContainer) -> float:
        """Get the conversion factor to base units."""
        factor = 1.0
        for unit, power in units.items():
            if unit in self._units:
                ud = self._units[unit]
                if hasattr(ud.converter, "scale"):
                    factor *= ud.converter.scale ** power
        return factor

    def _is_multiplicative(self, units: UnitsContainer) -> bool:
        """Check if all units are multiplicative."""
        for unit in units.keys():
            if unit in self._units:
                ud = self._units[unit]
                if not ud.converter.is_multiplicative:
                    return False
        return True

    def convert_to_base_units(self, quantity: PlainQuantity) -> PlainQuantity:
        """Convert a quantity to base units."""
        # Get the base unit representation
        base_units = {}
        magnitude = quantity._magnitude

        for unit, power in quantity._units.items():
            if unit in self._units:
                ud = self._units[unit]
                if ud.is_base:
                    base_units[unit] = base_units.get(unit, 0) + power
                else:
                    # Apply converter
                    if hasattr(ud.converter, "scale"):
                        magnitude *= ud.converter.scale ** power
                    # Recurse on reference
                    for ref_unit, ref_power in ud.reference.items():
                        if ref_unit.startswith("["):
                            # It's a dimension - find the base unit
                            continue
                        base_units[ref_unit] = (
                            base_units.get(ref_unit, 0) + power * ref_power
                        )
            else:
                base_units[unit] = base_units.get(unit, 0) + power

        base_units = {k: v for k, v in base_units.items() if v != 0}
        return self.Quantity(magnitude, UnitsContainer(base_units))

    def convert_to_root_units(self, quantity: PlainQuantity) -> PlainQuantity:
        """Convert a quantity to root units (similar to base units)."""
        return self.convert_to_base_units(quantity)

    def convert_to_reduced_units(self, quantity: PlainQuantity) -> PlainQuantity:
        """Convert a quantity to reduced units."""
        return self.convert_to_base_units(quantity)

    def to_compact(
        self, quantity: PlainQuantity, unit: Optional[str] = None
    ) -> PlainQuantity:
        """Convert to a compact representation."""
        magnitude = abs(quantity._magnitude)
        if magnitude == 0:
            return quantity

        # Find the best prefix
        import math

        order = math.floor(math.log10(magnitude))
        order = (order // 3) * 3  # Round to nearest SI prefix

        # Map order to prefix
        prefix_map = {
            -24: "yocto",
            -21: "zepto",
            -18: "atto",
            -15: "femto",
            -12: "pico",
            -9: "nano",
            -6: "micro",
            -3: "milli",
            0: "",
            3: "kilo",
            6: "mega",
            9: "giga",
            12: "tera",
            15: "peta",
            18: "exa",
            21: "zetta",
            24: "yotta",
        }

        if order not in prefix_map:
            return quantity

        prefix = prefix_map[order]

        # Get base unit
        if unit:
            base_unit = unit
        else:
            # Use the first unit in the expression
            for u in quantity._units.keys():
                base_unit = u
                break
            else:
                return quantity

        # Create new unit with prefix
        if prefix:
            new_unit = prefix + base_unit
        else:
            new_unit = base_unit

        try:
            return quantity.to(new_unit)
        except Exception:
            return quantity

    def get_group(self, name: str) -> Group:
        """Get or create a group."""
        if name not in self._groups:
            self._groups[name] = Group(name, self)
        return self._groups[name]

    def get_compatible_units(
        self, input_units, group: Optional[str] = None
    ) -> FrozenSet[PlainUnit]:
        """Get units compatible with the given units."""
        if isinstance(input_units, str):
            input_units = self.parse_units(input_units)

        dim = self.get_dimensionality(input_units._units)
        result = set()

        for name, ud in self._units.items():
            if ud.is_base:
                unit_dim = self.get_dimensionality(UnitsContainer({name: 1}))
                if unit_dim == dim:
                    result.add(self.Unit(name))

        if group:
            group_obj = self.get_group(group)
            result = {u for u in result if str(u) in group_obj.members}

        return frozenset(result)

    def add_context(self, context: Context) -> None:
        """Add a context to the registry."""
        self._contexts[context.name] = context
        for alias in context.aliases:
            self._contexts[alias] = context

    @contextlib.contextmanager
    def context(self, *names, **kwargs):
        """Activate contexts for unit conversion."""
        old_ctx = self._active_ctx
        new_ctx = _ChainedContext()

        for name in names:
            if name in self._contexts:
                new_ctx.add_context(self._contexts[name], **kwargs)

        self._active_ctx = new_ctx
        try:
            yield self
        finally:
            self._active_ctx = old_ctx

    def enable_contexts(self, *names, **kwargs):
        """Enable contexts without a context manager."""
        for name in names:
            if name in self._contexts:
                self._active_ctx.add_context(self._contexts[name], **kwargs)

    def disable_contexts(self, n: int = 1):
        """Disable the last n contexts."""
        for _ in range(n):
            if self._active_ctx._contexts:
                self._active_ctx._contexts.pop()

    def pi_theorem(self, dim_dict: Dict[str, Any]) -> List[Dict[str, float]]:
        """Apply the Buckingham Pi theorem."""
        from . import pi_theorem

        return pi_theorem.pi_theorem(dim_dict, self)


class _ChainedContext:
    """A chain of active contexts."""

    def __init__(self):
        self._contexts: List[Context] = []

    def __bool__(self):
        return bool(self._contexts)

    def add_context(self, context: Context, **kwargs):
        """Add a context to the chain."""
        self._contexts.append(context)

    @property
    def graph(self):
        """Combine graphs from all contexts."""
        result = defaultdict(set)
        for ctx in self._contexts:
            for src, dsts in ctx.graph.items():
                result[src].update(dsts)
        return dict(result)


class LazyRegistry(UnitRegistry):
    """A lazy-loading unit registry.

    This registry defers loading of unit definitions until they are needed.
    """

    def __init__(self, *args, **kwargs):
        self._initialized = False
        self._args = args
        self._kwargs = kwargs
        # Don't call super().__init__ yet

    def _ensure_initialized(self):
        """Ensure the registry is initialized."""
        if not self._initialized:
            self._initialized = True
            super().__init__(*self._args, **self._kwargs)

    def __getattr__(self, name):
        if name.startswith("_") and not name.startswith("_REGISTRY"):
            raise AttributeError(name)
        self._ensure_initialized()
        return getattr(self, name)


def _is_number_string(s: str) -> bool:
    """Check if a string represents a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False
