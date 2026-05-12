"""Unit registry that loads unit definitions and manages conversions."""

import os
import math
import re
from .unit_map import UnitMap
from .definition_parser import DefinitionFile, UnitDef, PrefixDef
from .converters import ScaleConverter, OffsetConverter, IdentityConverter
from .errors import (
    IncompatibleDimensionError,
    UnitNotFoundError,
    DefinitionParsingError,
)


_DEFAULT_DEFINITION_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "default_en.txt"
)


class UnitRegistry:
    """Central registry for unit definitions. Creates Quantity and Unit objects."""

    def __init__(self, definition_file=None, default_as_delta=True,
                 autoconvert_offset_to_baseunit=False):
        self._units = {}
        self._prefixes = {}
        self._dimensions = {}
        self._name_map = {}
        self._base_units = []
        self._dim_cache = {}
        self._root_cache = {}
        self._conversion_cache = {}

        self.default_as_delta = default_as_delta
        self.autoconvert_offset_to_baseunit = autoconvert_offset_to_baseunit

        if definition_file is None:
            definition_file = _DEFAULT_DEFINITION_FILE

        self._load_definitions(definition_file)
        self._build_cache()

    def _load_definitions(self, filepath):
        dfile = DefinitionFile()
        dfile.load(filepath)

        for name, pdef in dfile.prefixes.items():
            self._prefixes[name] = pdef
            self._name_map[name] = ("prefix", name)
            if pdef.symbol:
                self._name_map[pdef.symbol] = ("prefix", name)
            for a in pdef.aliases:
                self._name_map[a] = ("prefix", name)

        for name, ddef in dfile.dimensions.items():
            self._dimensions[name] = ddef

        for name, udef in dfile.units.items():
            self._units[name] = udef
            if udef.is_base:
                self._base_units.append(name)
            self._name_map[name] = ("unit", name)
            if udef.symbol:
                self._name_map[udef.symbol] = ("unit", name)
            for a in udef.aliases:
                self._name_map[a] = ("unit", name)

            if udef.converter.is_offset and not udef.is_base:
                self._create_delta_unit(name, udef)

    def _build_cache(self):
        self._dim_cache.clear()
        self._root_cache.clear()
        self._conversion_cache.clear()

        ordered = self._dependency_order()
        for uname in ordered:
            umap = UnitMap({uname: 1})
            try:
                self._compute_dimensionality(umap)
            except Exception:
                pass
            try:
                self._compute_root_units(umap)
            except Exception:
                pass

    def _create_delta_unit(self, name, udef):
        delta_name = "delta_" + name
        delta_aliases = tuple("delta_" + a for a in udef.aliases)
        delta_symbol = None
        if udef.symbol:
            delta_symbol = "Δ" + udef.symbol

        delta_converter = ScaleConverter(factor=udef.converter.factor)
        delta_ref = dict(udef.reference)

        delta_udef = UnitDef(
            name=delta_name,
            converter=delta_converter,
            reference=delta_ref,
            symbol=delta_symbol,
            aliases=delta_aliases,
            is_base=False,
        )
        self._units[delta_name] = delta_udef
        self._name_map[delta_name] = ("unit", delta_name)
        if delta_symbol:
            self._name_map[delta_symbol] = ("unit", delta_name)
        for a in delta_aliases:
            self._name_map[a] = ("unit", delta_name)

    def _dependency_order(self):
        resolved = set()
        order = []
        unresolved = set()

        def resolve(name):
            if name in resolved:
                return
            if name in unresolved:
                resolved.add(name)
                order.append(name)
                unresolved.discard(name)
                return
            unresolved.add(name)
            udef = self._units.get(name)
            if udef and udef.reference:
                for dep in udef.reference:
                    dep_canon = self._resolve_unit_name(dep)
                    if dep_canon and dep_canon in self._units:
                        resolve(dep_canon)
            resolved.add(name)
            unresolved.discard(name)
            order.append(name)

        for name in list(self._units.keys()):
            resolve(name)
        return order

    def _resolve_unit_name(self, name):
        if name in self._units:
            return name

        entry = self._name_map.get(name)
        if entry and entry[0] == "unit":
            return entry[1]

        stripped = name.rstrip("s")
        if stripped in self._units:
            return stripped
        entry = self._name_map.get(stripped)
        if entry and entry[0] == "unit":
            return entry[1]

        prefix_name, base_name = self._split_prefix(name)
        if prefix_name is not None and base_name is not None:
            return self._get_or_create_prefixed_unit(prefix_name, base_name)

        if name != stripped:
            prefix_name, base_name = self._split_prefix(stripped)
            if prefix_name is not None and base_name is not None:
                return self._get_or_create_prefixed_unit(prefix_name, base_name)

        return None

    def _split_prefix(self, name):
        candidates = []
        for pname, pdef in self._prefixes.items():
            if name.startswith(pname) and len(name) > len(pname):
                remainder = name[len(pname):]
                base = self._find_base_unit(remainder)
                if base is not None:
                    candidates.append((pname, base, len(pname)))
            if pdef.symbol and name.startswith(pdef.symbol) and len(name) > len(pdef.symbol):
                remainder = name[len(pdef.symbol):]
                base = self._find_base_unit(remainder)
                if base is not None:
                    candidates.append((pname, base, len(pdef.symbol)))
            for alias in pdef.aliases:
                if name.startswith(alias) and len(name) > len(alias):
                    remainder = name[len(alias):]
                    base = self._find_base_unit(remainder)
                    if base is not None:
                        candidates.append((pname, base, len(alias)))

        if not candidates:
            return None, None

        candidates.sort(key=lambda c: c[2], reverse=True)
        return candidates[0][0], candidates[0][1]

    def _find_base_unit(self, name):
        if name in self._units:
            return name
        entry = self._name_map.get(name)
        if entry and entry[0] == "unit":
            return entry[1]
        stripped = name.rstrip("s")
        if stripped in self._units:
            return stripped
        entry = self._name_map.get(stripped)
        if entry and entry[0] == "unit":
            return entry[1]
        return None

    def _get_or_create_prefixed_unit(self, prefix_name, base_unit_name):
        combined = prefix_name + base_unit_name
        if combined in self._units:
            return combined

        pdef = self._prefixes[prefix_name]
        base_udef = self._units[base_unit_name]

        if not base_udef.converter.is_multiplicative:
            return None

        new_converter = ScaleConverter(factor=pdef.factor)
        new_udef = UnitDef(
            name=combined,
            converter=new_converter,
            reference={base_unit_name: 1},
            symbol=None,
            aliases=(),
            is_base=False,
        )
        self._units[combined] = new_udef
        self._name_map[combined] = ("unit", combined)
        return combined

    def get_canonical_name(self, name):
        resolved = self._resolve_unit_name(name)
        if resolved:
            return resolved
        raise UnitNotFoundError(name)

    def parse_unit_string(self, unit_str, as_delta=None):
        if as_delta is None:
            as_delta = self.default_as_delta

        unit_str = unit_str.strip()
        if not unit_str or unit_str == "dimensionless":
            return UnitMap({})

        from .expression_parser import parse_unit_expression
        scale, raw_units = parse_unit_expression(unit_str)

        if scale != 1.0 and abs(scale - 1.0) > 1e-15:
            pass

        resolved = {}
        for uname, exp in raw_units.items():
            try:
                canonical = self.get_canonical_name(uname)
                resolved[canonical] = resolved.get(canonical, 0) + exp
            except UnitNotFoundError:
                raise

        cleaned = {k: v for k, v in resolved.items() if v != 0}
        return UnitMap(cleaned)

    def parse_expression(self, expr_str):
        from .expression_parser import tokenize_expression, _parse_tokens, evaluate_tree
        import tokenize as _tok

        expr_str = expr_str.strip()
        if not expr_str:
            return self.Quantity(0)

        tokens = tokenize_expression(expr_str)
        if not tokens:
            return self.Quantity(0)

        def resolver(name):
            if name in ("inf", "infinity"):
                return float("inf")
            if name == "nan":
                return float("nan")
            try:
                canonical = self.get_canonical_name(name)
                return self.Quantity(1, UnitMap({canonical: 1}))
            except UnitNotFoundError:
                raise

        tree, _ = _parse_tokens(tokens, 0, 0)
        result = evaluate_tree(tree, resolver)

        if isinstance(result, (int, float)):
            return self.Quantity(result)
        return result

    def get_dimensionality(self, units):
        if isinstance(units, str):
            units = self.parse_unit_string(units)
        if isinstance(units, UnitMap):
            return self._compute_dimensionality(units)
        return UnitMap({})

    def _compute_dimensionality(self, units):
        key = units
        if key in self._dim_cache:
            return self._dim_cache[key]

        accum = {}
        self._dimensionality_recurse(units, 1, accum)
        accum.pop("[]", None)
        cleaned = {k: v for k, v in accum.items() if v != 0}
        result = UnitMap(cleaned)
        self._dim_cache[key] = result
        return result

    def _dimensionality_recurse(self, ref, exp, accum):
        for key in ref:
            exp2 = exp * ref[key]
            if self._is_dimension(key):
                ddef = self._dimensions.get(key)
                if ddef and ddef.reference:
                    self._dimensionality_recurse(ddef.reference, exp2, accum)
                else:
                    accum[key] = accum.get(key, 0) + exp2
            else:
                resolved = self._resolve_unit_name(key)
                if resolved and resolved in self._units:
                    udef = self._units[resolved]
                    if udef.is_base:
                        if udef.dimension:
                            accum[udef.dimension] = accum.get(udef.dimension, 0) + exp2
                        else:
                            accum["[]"] = accum.get("[]", 0) + exp2
                    else:
                        self._dimensionality_recurse(udef.reference, exp2, accum)
                else:
                    raise UnitNotFoundError(key)

    def _is_dimension(self, name):
        return name.startswith("[") and name.endswith("]")

    def get_root_units(self, units):
        if isinstance(units, str):
            units = self.parse_unit_string(units)
        return self._compute_root_units(units)

    def _compute_root_units(self, units):
        key = units
        if key in self._root_cache:
            return self._root_cache[key]

        accum = {}
        scale_factors = {"num": {}, "den": {}}
        self._root_units_recurse(units, 1, accum, scale_factors)

        num = scale_factors["num"]
        den = scale_factors["den"]
        while True:
            common = set(num.keys()) & set(den.keys())
            if not common:
                break
            changed = False
            for k in common:
                mn = min(num[k], den[k])
                num[k] -= mn
                den[k] -= mn
                if num[k] == 0:
                    del num[k]
                if den[k] == 0:
                    del den[k]
                changed = True
            if not changed:
                break

        total_scale = 1.0
        for factor, exp in num.items():
            total_scale *= factor ** exp
        for factor, exp in den.items():
            total_scale /= factor ** exp

        cleaned = {k: v for k, v in accum.items() if v != 0}
        result = UnitMap(cleaned)
        self._root_cache[key] = (total_scale, result)
        return total_scale, result

    def _root_units_recurse(self, ref, exp, accum, scale_factors):
        for key in ref:
            exp2 = exp * ref[key]
            resolved = self._resolve_unit_name(key)
            if resolved is None:
                if self._is_dimension(key):
                    continue
                raise UnitNotFoundError(key)

            udef = self._units.get(resolved)
            if udef is None:
                raise UnitNotFoundError(resolved)

            if udef.is_base:
                accum[resolved] = accum.get(resolved, 0) + exp2
            else:
                scale = udef.converter.factor
                if scale != 1.0:
                    if exp2 > 0:
                        scale_factors["num"][scale] = scale_factors["num"].get(scale, 0) + exp2
                    else:
                        scale_factors["den"][scale] = scale_factors["den"].get(scale, 0) + (-exp2)
                self._root_units_recurse(udef.reference, exp2, accum, scale_factors)

    def get_conversion_factor(self, src_units, dst_units):
        if isinstance(src_units, str):
            src_units = self.parse_unit_string(src_units)
        if isinstance(dst_units, str):
            dst_units = self.parse_unit_string(dst_units)

        cache_key = (src_units, dst_units)
        if cache_key in self._conversion_cache:
            return self._conversion_cache[cache_key]

        src_dim = self._compute_dimensionality(src_units)
        dst_dim = self._compute_dimensionality(dst_units)

        if src_dim != dst_dim:
            raise IncompatibleDimensionError(
                str(src_units), str(dst_units),
                str(src_dim), str(dst_dim)
            )

        combined = src_units / dst_units
        factor, _ = self._compute_root_units(combined)

        self._conversion_cache[cache_key] = factor
        return factor

    def convert(self, value, src_units, dst_units):
        if isinstance(src_units, str):
            src_units = self.parse_unit_string(src_units)
        if isinstance(dst_units, str):
            dst_units = self.parse_unit_string(dst_units)

        src_offset = self._find_offset_unit(src_units)
        dst_offset = self._find_offset_unit(dst_units)

        if not src_offset and not dst_offset:
            factor = self.get_conversion_factor(src_units, dst_units)
            return value * factor

        src_dim = self._compute_dimensionality(src_units)
        dst_dim = self._compute_dimensionality(dst_units)
        if src_dim != dst_dim:
            raise IncompatibleDimensionError(
                str(src_units), str(dst_units),
                str(src_dim), str(dst_dim)
            )

        if src_offset:
            src_udef = self._units[src_offset]
            value = src_udef.converter.to_reference(value)
            remaining_src = {k: v for k, v in src_units._data.items() if k != src_offset}
            ref_units = dict(src_udef.reference)
            for k, v in remaining_src.items():
                ref_units[k] = ref_units.get(k, 0) + v
            src_units = UnitMap({k: v for k, v in ref_units.items() if v != 0})

        if dst_offset:
            dst_udef = self._units[dst_offset]
            remaining_dst = {k: v for k, v in dst_units._data.items() if k != dst_offset}
            ref_units = dict(dst_udef.reference)
            for k, v in remaining_dst.items():
                ref_units[k] = ref_units.get(k, 0) + v
            dst_units_for_mult = UnitMap({k: v for k, v in ref_units.items() if v != 0})
        else:
            dst_units_for_mult = dst_units

        if src_units != dst_units_for_mult:
            try:
                factor = self.get_conversion_factor(src_units, dst_units_for_mult)
                value = value * factor
            except IncompatibleDimensionError:
                pass

        if dst_offset:
            dst_udef = self._units[dst_offset]
            value = dst_udef.converter.from_reference(value)

        return value

    def _find_offset_unit(self, units):
        for uname in units:
            resolved = self._resolve_unit_name(uname)
            if resolved and resolved in self._units:
                udef = self._units[resolved]
                if udef.converter.is_offset and units[uname] == 1:
                    return resolved
        return None

    def Quantity(self, magnitude, units=None):
        from .quantity import Quantity
        return Quantity(magnitude, units, registry=self)

    def Unit(self, units):
        from .unit import Unit
        return Unit(units, registry=self)

    def Measurement(self, value, error=None, units=None):
        from .measurement import Measurement
        return Measurement(value, error, units, registry=self)

    @property
    def sys(self):
        return _SystemAccess(self)


class _SystemAccess:
    def __init__(self, registry):
        self._registry = registry
