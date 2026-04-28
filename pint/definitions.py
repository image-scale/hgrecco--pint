"""
    pint.definitions
    ~~~~~~~~~~~~~~~~

    Definition parsing.
"""
from __future__ import annotations

import re
from typing import Union

from .errors import DefinitionSyntaxError
from .facets.plain.definitions import (
    AliasDefinition,
    DimensionDefinition,
    PrefixDefinition,
    ScaleConverter,
    UnitDefinition,
)
from .facets.nonmultiplicative.definitions import (
    LogarithmicConverter,
    OffsetConverter,
)
from .util import UnitsContainer


class Definition:
    """Base class for definitions.

    This class provides a from_string factory method to parse
    definition strings into appropriate definition objects.
    """

    @staticmethod
    def from_string(
        definition: str, non_int_type: type = float
    ) -> Union[
        PrefixDefinition, UnitDefinition, DimensionDefinition, AliasDefinition
    ]:
        """Parse a definition string into a Definition object.

        Parameters
        ----------
        definition : str
            The definition string.
        non_int_type : type
            The type to use for non-integer numbers (default: float).

        Returns
        -------
        Definition
            A PrefixDefinition, UnitDefinition, DimensionDefinition, or AliasDefinition.

        Raises
        ------
        DefinitionSyntaxError
            If the definition string is invalid.
        """
        definition = definition.strip()

        # Handle alias definitions
        if definition.startswith("@alias"):
            parts = definition[6:].strip().split("=")
            name = parts[0].strip()
            aliases = tuple(p.strip() for p in parts[1:] if p.strip())
            return AliasDefinition(name=name, aliases=aliases)

        # Handle dimension definitions
        if definition.startswith("["):
            return _parse_dimension_definition(definition, non_int_type)

        # Handle prefix definitions (end with -)
        if re.match(r"^\w+\-\s*=", definition):
            return _parse_prefix_definition(definition, non_int_type)

        # Handle unit definitions
        return _parse_unit_definition(definition, non_int_type)


def _parse_dimension_definition(
    definition: str, non_int_type: type
) -> DimensionDefinition:
    """Parse a dimension definition."""
    parts = definition.split("=")
    name = parts[0].strip()

    if len(parts) == 1:
        # Base dimension like [length]
        return DimensionDefinition(name=name)

    # Derived dimension like [speed] = [length] / [time]
    reference_str = parts[1].strip()

    # Check for invalid syntax
    if "*" in reference_str and not all(
        c in "[]/ *0-9a-zA-Z_-" for c in reference_str
    ):
        raise DefinitionSyntaxError(f"Invalid dimension definition: {definition}")

    reference = _parse_reference(reference_str)
    return DimensionDefinition(name=name, reference=reference)


def _parse_prefix_definition(
    definition: str, non_int_type: type
) -> PrefixDefinition:
    """Parse a prefix definition."""
    parts = definition.split("=")
    name = parts[0].strip().rstrip("-")
    scale_str = parts[1].strip()

    # Check for additional units in the scale (not allowed for prefixes)
    scale_str_clean = scale_str.split()[0] if " " in scale_str else scale_str
    if any(c.isalpha() for c in scale_str_clean.replace("e", "").replace("E", "")):
        raise ValueError(f"Invalid prefix definition: {definition}")

    # Parse the scale value
    scale = _parse_scale(scale_str, non_int_type)
    converter = ScaleConverter(scale)

    # Parse symbol and aliases
    symbol = None
    aliases = []
    for part in parts[2:]:
        part = part.strip().rstrip("-")
        if not part or part == "_":
            continue
        if symbol is None:
            symbol = part
        else:
            aliases.append(part)

    return PrefixDefinition(
        name=name, symbol=symbol, aliases=tuple(aliases), converter=converter
    )


def _parse_unit_definition(
    definition: str, non_int_type: type
) -> UnitDefinition:
    """Parse a unit definition."""
    # Split on semicolon for modifiers
    main_part, *modifiers = definition.split(";")

    parts = main_part.split("=")
    name = parts[0].strip()

    # Handle alias-only definitions
    if len(parts) >= 2:
        # Check for dimension reference (base unit)
        ref_str = parts[1].strip()

        if ref_str.startswith("["):
            # Base unit definition like "meter = [length]"
            reference = UnitsContainer({ref_str: 1})
            converter = ScaleConverter(1.0)

            # Parse symbol and aliases
            symbol = None
            aliases = []
            for part in parts[2:]:
                part = part.strip()
                if not part or part == "_":
                    continue
                if symbol is None:
                    symbol = part
                else:
                    if part != "_":
                        aliases.append(part)

            return UnitDefinition(
                name=name,
                symbol=symbol if symbol else name,
                aliases=tuple(aliases),
                converter=converter,
                reference=reference,
                is_base=True,
            )

        # Check if it's just a unit alias (no scale)
        if _is_unit_name(ref_str) and not any(c in ref_str for c in "*/+-0123456789"):
            # It's an alias like "meter_per_second_squared = acceleration"
            reference = UnitsContainer({ref_str: 1})
            converter = ScaleConverter(1.0)

            # Parse symbol and aliases
            symbol = None
            aliases = []
            for part in parts[2:]:
                part = part.strip()
                if not part or part == "_":
                    continue
                if symbol is None:
                    symbol = part
                else:
                    if part != "_":
                        aliases.append(part)

            return UnitDefinition(
                name=name,
                symbol=symbol if symbol else name,
                aliases=tuple(aliases),
                converter=converter,
                reference=reference,
                is_base=False,
            )

        # Parse the reference and scale
        scale, reference = _parse_unit_reference(ref_str, non_int_type)

    else:
        scale = 1.0
        reference = UnitsContainer()

    # Parse modifiers
    offset = None
    logbase = None
    logfactor = None

    for mod in modifiers:
        mod = mod.strip()
        if mod.startswith("offset:"):
            offset_str = mod[7:].strip()
            # Check for extra junk
            if " " in offset_str and not offset_str.replace(" ", "").replace(".", "").replace("-", "").replace("+", "").replace("e", "").replace("E", "").isdigit():
                raise ValueError(f"Invalid offset modifier: {mod}")
            offset = non_int_type(offset_str.split()[0])
        elif mod.startswith("logbase:"):
            logbase = non_int_type(mod[8:].strip())
        elif mod.startswith("logfactor:"):
            logfactor = non_int_type(mod[10:].strip())

    # Create the appropriate converter
    if logbase is not None and logfactor is not None:
        converter = LogarithmicConverter(scale, logbase, logfactor)
    elif offset is not None:
        converter = OffsetConverter(scale, offset)
    else:
        converter = ScaleConverter(scale)

    # Parse symbol and aliases
    symbol = None
    aliases = []
    for part in parts[2:]:
        part = part.strip()
        if not part or part == "_":
            continue
        if symbol is None:
            symbol = part
        else:
            if part != "_":
                aliases.append(part)

    return UnitDefinition(
        name=name,
        symbol=symbol if symbol else name,
        aliases=tuple(aliases),
        converter=converter,
        reference=reference,
        is_base=False,
    )


def _is_unit_name(s: str) -> bool:
    """Check if a string looks like a unit name."""
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", s))


def _parse_scale(s: str, non_int_type: type) -> float:
    """Parse a scale value from a string."""
    s = s.strip()

    if "**" in s:
        base, exp = s.split("**")
        return float(base.strip()) ** float(exp.strip())
    if "^" in s:
        base, exp = s.split("^")
        return float(base.strip()) ** float(exp.strip())

    return non_int_type(s)


def _parse_reference(s: str) -> UnitsContainer:
    """Parse a reference string into a UnitsContainer."""
    result = {}
    s = s.strip()

    # Split by / for division
    if "/" in s:
        num, *denoms = s.split("/")
        _add_to_ref(result, num.strip(), 1)
        for d in denoms:
            _add_to_ref(result, d.strip(), -1)
    else:
        _add_to_ref(result, s, 1)

    return UnitsContainer(result)


def _add_to_ref(result: dict, s: str, sign: int) -> None:
    """Add a term to the reference dict."""
    s = s.strip()
    if not s:
        return

    # Handle multiplication
    for term in s.split("*"):
        term = term.strip()
        if not term:
            continue

        # Handle exponents
        if "**" in term:
            base, exp = term.split("**")
            result[base.strip()] = result.get(base.strip(), 0) + sign * float(exp.strip())
        else:
            result[term] = result.get(term, 0) + sign


def _parse_unit_reference(
    s: str, non_int_type: type
) -> tuple[float, UnitsContainer]:
    """Parse a unit reference string into a scale and UnitsContainer."""
    s = s.strip()

    # Try to extract a numeric scale
    scale = 1.0
    reference_parts = []

    # Split by * and /
    tokens = re.split(r"(\*|/)", s)
    op = "*"
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token == "*":
            op = "*"
            continue
        if token == "/":
            op = "/"
            continue

        # Check if it's a number
        if _is_number(token):
            val = non_int_type(token)
            if op == "*":
                scale *= val
            else:
                scale /= val
        else:
            # It's a unit reference
            if op == "/":
                reference_parts.append(("div", token))
            else:
                reference_parts.append(("mul", token))

    # Build the reference
    result = {}
    for op, part in reference_parts:
        # Handle exponents
        if "**" in part:
            base, exp = part.split("**")
            exp_val = float(exp.strip())
        else:
            base = part
            exp_val = 1

        if op == "div":
            exp_val = -exp_val

        result[base.strip()] = result.get(base.strip(), 0) + exp_val

    return scale, UnitsContainer(result)


def _is_number(s: str) -> bool:
    """Check if a string is a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False
