"""Parser for unit definition text files."""

import os
import re
import math
from dataclasses import dataclass, field
from typing import Optional

from .converters import ScaleConverter, OffsetConverter, IdentityConverter
from .expression_parser import parse_and_eval, _parse_number


@dataclass
class PrefixDef:
    name: str
    factor: float
    symbol: Optional[str] = None
    aliases: tuple = ()


@dataclass
class DimensionDef:
    name: str
    reference: Optional[dict] = None  # None for base dimensions


@dataclass
class UnitDef:
    name: str
    converter: object  # ScaleConverter / OffsetConverter / IdentityConverter
    reference: dict  # {unit_name: exponent}
    dimension: Optional[str] = None  # e.g. "[length]" for base units
    symbol: Optional[str] = None
    aliases: tuple = ()
    is_base: bool = False


@dataclass
class ConstantDef:
    name: str
    value: float
    reference: dict
    symbol: Optional[str] = None
    aliases: tuple = ()


@dataclass
class GroupDef:
    name: str
    using: tuple = ()
    unit_names: tuple = ()


@dataclass
class SystemDef:
    name: str
    using: tuple = ()
    base_units: tuple = ()
    rules: tuple = ()


@dataclass
class ContextDef:
    name: str
    aliases: tuple = ()
    defaults: dict = field(default_factory=dict)
    rules: tuple = ()


def _strip_comment(line):
    in_string = False
    for i, ch in enumerate(line):
        if ch == "#" and not in_string:
            return line[:i].rstrip()
    return line.rstrip()


def _split_definition(line):
    parts = [p.strip() for p in line.split("=")]
    return parts


_DIMENSION_RE = re.compile(r"^\[(\w+)\]$")
_PREFIX_RE = re.compile(r"^(\w+)-$")


class DefinitionFile:
    """Parse a unit definition file and yield definition objects."""

    def __init__(self):
        self.prefixes = {}
        self.dimensions = {}
        self.units = {}
        self.constants = {}
        self.groups = {}
        self.systems = {}
        self.contexts = {}
        self._name_to_canonical = {}
        self._loaded_files = set()

    def load(self, filepath):
        filepath = os.path.abspath(filepath)
        if filepath in self._loaded_files:
            return
        self._loaded_files.add(filepath)
        base_dir = os.path.dirname(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self._process_lines(lines, base_dir)

    def _process_lines(self, lines, base_dir=None):
        i = 0
        while i < len(lines):
            line = _strip_comment(lines[i])
            i += 1

            if not line or line.startswith("#"):
                continue

            if line.startswith("@import"):
                fname = line.split(None, 1)[1].strip()
                if base_dir:
                    fpath = os.path.join(base_dir, fname)
                    self.load(fpath)
                continue

            if line.startswith("@defaults"):
                while i < len(lines):
                    dline = _strip_comment(lines[i])
                    i += 1
                    if dline.strip() == "@end":
                        break
                continue

            if line.startswith("@alias"):
                self._parse_alias(line)
                continue

            if line.startswith("@group"):
                block_lines = []
                while i < len(lines):
                    dline = _strip_comment(lines[i])
                    i += 1
                    if dline.strip() == "@end":
                        break
                    block_lines.append(dline)
                self._parse_group(line, block_lines)
                continue

            if line.startswith("@system"):
                block_lines = []
                while i < len(lines):
                    dline = _strip_comment(lines[i])
                    i += 1
                    if dline.strip() == "@end":
                        break
                    block_lines.append(dline)
                self._parse_system(line, block_lines)
                continue

            if line.startswith("@context"):
                block_lines = []
                while i < len(lines):
                    dline = _strip_comment(lines[i])
                    i += 1
                    if dline.strip() == "@end":
                        break
                    block_lines.append(dline)
                self._parse_context(line, block_lines)
                continue

            self._parse_definition(line)

    def _parse_alias(self, line):
        line = line[len("@alias"):].strip()
        parts = _split_definition(line)
        if len(parts) < 2:
            return
        existing_name = parts[0].strip()
        canonical = self._resolve_name(existing_name)
        if canonical is None:
            canonical = existing_name
        for alias in parts[1:]:
            alias = alias.strip()
            if alias and alias != "_":
                self._name_to_canonical[alias] = canonical

    def _parse_definition(self, line):
        offset = None
        if ";" in line:
            line_part, offset_part = line.split(";", 1)
            line = line_part.strip()
            offset_match = re.search(r"offset:\s*(.+)", offset_part)
            if offset_match:
                offset_expr = offset_match.group(1).strip()
                parts_after = _split_definition(offset_expr)
                offset_expr = parts_after[0]
                extra_parts = parts_after[1:]
                try:
                    offset = self._eval_numeric_expr(offset_expr)
                except Exception:
                    offset = 0.0
            else:
                extra_parts = []
        else:
            extra_parts = []

        parts = _split_definition(line)
        if not parts:
            return

        name_raw = parts[0].strip()

        if _PREFIX_RE.match(name_raw):
            self._add_prefix(name_raw, parts[1:])
            return

        if _DIMENSION_RE.match(name_raw):
            self._add_derived_dimension(name_raw, parts[1:])
            return

        if len(parts) < 2:
            return

        relation = parts[1].strip()
        extra = parts[2:]
        if offset is not None:
            extra = extra_parts + extra

        dim_match = _DIMENSION_RE.match(relation)
        if dim_match:
            self._add_base_unit(name_raw, relation, extra, offset)
            return

        if relation == "[]":
            self._add_base_unit(name_raw, relation, extra, offset)
            return

        self._add_derived_unit(name_raw, relation, extra, offset)

    def _add_prefix(self, name_raw, parts):
        name = name_raw[:-1]  # remove trailing -
        if not parts:
            return
        factor_expr = parts[0].strip()
        try:
            factor = self._eval_numeric_expr(factor_expr)
        except Exception:
            return

        symbol = None
        aliases = []
        for p in parts[1:]:
            p = p.strip()
            if not p or p == "_":
                continue
            if p.endswith("-"):
                p = p[:-1]
            if symbol is None:
                symbol = p
            else:
                aliases.append(p)

        pdef = PrefixDef(
            name=name, factor=factor,
            symbol=symbol, aliases=tuple(aliases)
        )
        self.prefixes[name] = pdef
        if symbol:
            self._name_to_canonical[symbol] = name
        for a in aliases:
            self._name_to_canonical[a] = name

    def _add_derived_dimension(self, name_raw, parts):
        dim_name = name_raw
        if parts:
            ref_expr = parts[0].strip()
            try:
                _, ref_units = self._parse_dimension_expr(ref_expr)
            except Exception:
                ref_units = None
            ddef = DimensionDef(name=dim_name, reference=ref_units)
        else:
            ddef = DimensionDef(name=dim_name, reference=None)
        self.dimensions[dim_name] = ddef

    def _parse_dimension_expr(self, expr):
        """Parse a dimension expression like '[length] ** 2' or '[mass] / [volume]'."""
        expr = expr.replace("^", "**")
        dims = {}
        tokens = re.findall(r"\[[\w]+\]|\*\*|[*/]|[\d.]+", expr)
        i = 0
        current_exp_sign = 1
        while i < len(tokens):
            tok = tokens[i]
            if _DIMENSION_RE.match(tok):
                exp = current_exp_sign
                if i + 2 < len(tokens) and tokens[i + 1] == "**":
                    exp = current_exp_sign * float(tokens[i + 2])
                    if exp == int(exp):
                        exp = int(exp)
                    i += 2
                dims[tok] = dims.get(tok, 0) + exp
                current_exp_sign = 1
            elif tok == "/":
                current_exp_sign = -1
            elif tok == "*":
                current_exp_sign = 1
            i += 1
        return 1.0, dims

    def _add_base_unit(self, name, dimension, extra_parts, offset=None):
        if dimension == "[]":
            dim_name = "[]"
        else:
            dim_name = dimension

        if dim_name not in self.dimensions and dim_name != "[]":
            self.dimensions[dim_name] = DimensionDef(name=dim_name)

        symbol = None
        aliases = []
        for p in extra_parts:
            p = p.strip()
            if not p or p == "_":
                if symbol is None:
                    symbol = "_"
                continue
            if symbol is None or symbol == "_":
                if p != "_":
                    symbol = p
                else:
                    symbol = "_"
            else:
                aliases.append(p)

        if symbol == "_":
            symbol = None

        if offset is not None and offset != 0:
            converter = OffsetConverter(factor=1.0, offset=offset)
        else:
            converter = IdentityConverter()

        udef = UnitDef(
            name=name, converter=converter,
            reference={dim_name: 1} if dim_name != "[]" else {},
            dimension=dim_name, symbol=symbol, aliases=tuple(aliases),
            is_base=True
        )
        self.units[name] = udef
        self._name_to_canonical[name] = name
        if symbol and symbol != "_":
            self._name_to_canonical[symbol] = name
        for a in aliases:
            self._name_to_canonical[a] = name

    def _add_derived_unit(self, name, relation, extra_parts, offset=None):
        symbol = None
        aliases = []
        for p in extra_parts:
            p = p.strip()
            if not p:
                continue
            if p == "_":
                if symbol is None:
                    symbol = "_"
                continue
            if symbol is None or symbol == "_":
                if p != "_":
                    symbol = p
                else:
                    symbol = "_"
            else:
                aliases.append(p)

        if symbol == "_":
            symbol = None

        try:
            scale, ref_units = self._parse_unit_relation(relation)
        except Exception:
            return

        if offset is not None:
            converter = OffsetConverter(factor=scale, offset=offset)
        else:
            converter = ScaleConverter(factor=scale)

        udef = UnitDef(
            name=name, converter=converter,
            reference=ref_units, symbol=symbol,
            aliases=tuple(aliases), is_base=False
        )
        self.units[name] = udef
        self._name_to_canonical[name] = name
        if symbol and symbol != "_":
            self._name_to_canonical[symbol] = name
        for a in aliases:
            self._name_to_canonical[a] = name

    def _parse_unit_relation(self, expr):
        """Parse e.g. '60 * second' → (60.0, {'second': 1})
        or 'kilo * meter' → handle later at registry level.
        """
        from .expression_parser import parse_unit_expression
        scale, units = parse_unit_expression(expr)
        return scale, units

    def _eval_numeric_expr(self, expr):
        """Evaluate a numeric expression, supporting ** and basic math."""
        expr = expr.replace("^", "**")
        expr = expr.strip()
        try:
            return eval(expr, {"__builtins__": {}}, {"pi": math.pi, "π": math.pi})
        except Exception:
            return _parse_number(expr)

    def _resolve_name(self, name):
        if name in self._name_to_canonical:
            return self._name_to_canonical[name]
        if name in self.units:
            return name
        if name in self.prefixes:
            return name
        return None

    def _parse_group(self, header, body_lines):
        header = header[len("@group"):].strip()
        using = ()
        if " using " in header:
            name_part, using_part = header.split(" using ", 1)
            name = name_part.strip()
            using = tuple(g.strip() for g in using_part.split(",") if g.strip())
        else:
            name = header.strip()

        unit_names = []
        for line in body_lines:
            line = line.strip()
            if not line:
                continue
            self._parse_definition(line)
            parts = _split_definition(line)
            if parts:
                uname = parts[0].strip()
                if not uname.startswith("[") and not uname.endswith("-"):
                    unit_names.append(uname)

        self.groups[name] = GroupDef(
            name=name, using=using, unit_names=tuple(unit_names)
        )

    def _parse_system(self, header, body_lines):
        header = header[len("@system"):].strip()
        using = ()
        if " using " in header:
            name_part, using_part = header.split(" using ", 1)
            name = name_part.strip()
            using = tuple(g.strip() for g in using_part.split(",") if g.strip())
        else:
            name = header.strip()

        rules = []
        base_units = []
        for line in body_lines:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                new_unit, old_unit = line.split(":", 1)
                rules.append((new_unit.strip(), old_unit.strip()))
                base_units.append(new_unit.strip())
            else:
                base_units.append(line)

        self.systems[name] = SystemDef(
            name=name, using=using,
            base_units=tuple(base_units), rules=tuple(rules)
        )

    def _parse_context(self, header, body_lines):
        header = header[len("@context"):].strip()

        defaults = {}
        if header.startswith("("):
            paren_end = header.index(")")
            defaults_str = header[1:paren_end]
            for item in defaults_str.split(","):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    try:
                        defaults[k.strip()] = self._eval_numeric_expr(v.strip())
                    except Exception:
                        defaults[k.strip()] = 0
            header = header[paren_end + 1:].strip()

        aliases = ()
        if "=" in header:
            parts = header.split("=")
            name = parts[0].strip()
            aliases = tuple(p.strip() for p in parts[1:] if p.strip())
        else:
            name = header.strip()

        rules = []
        for line in body_lines:
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                continue

            arrow_part, expr = line.split(":", 1)
            expr = expr.strip()

            if "<->" in arrow_part:
                left, right = arrow_part.split("<->")
                left = left.strip()
                right = right.strip()
                rules.append((left, right, expr))
                rules.append((right, left, expr))
            elif "->" in arrow_part:
                left, right = arrow_part.split("->")
                rules.append((left.strip(), right.strip(), expr))

        self.contexts[name] = ContextDef(
            name=name, aliases=aliases, defaults=defaults, rules=tuple(rules)
        )
