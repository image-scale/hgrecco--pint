"""Unit registry that loads unit definitions and manages conversions."""

import os
import math
import re
from .unit_map import UnitMap
from .definition_parser import DefinitionFile, UnitDef, PrefixDef, GroupDef, SystemDef, ContextDef
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
        self._groups = {}
        self._systems = {}
        self._contexts = {}
        self._active_contexts = []
        self._active_context_kwargs = []
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

        from .systems import Group, System
        for name, gdef in dfile.groups.items():
            self._groups[name] = Group(
                name=name, unit_names=gdef.unit_names,
                using=gdef.using, registry=self
            )

        for name, sdef in dfile.systems.items():
            self._systems[name] = System(
                name=name, base_units=sdef.base_units,
                rules=sdef.rules, using=sdef.using, registry=self
            )

        from .context import Context as CtxClass
        for name, cdef in dfile.contexts.items():
            ctx = CtxClass(
                name=name, aliases=cdef.aliases,
                defaults=cdef.defaults, rules=cdef.rules, registry=self
            )
            self._contexts[name] = ctx
            for alias in cdef.aliases:
                self._contexts[alias] = ctx

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
            try:
                factor = self.get_conversion_factor(src_units, dst_units)
                return value * factor
            except IncompatibleDimensionError:
                if self._active_contexts:
                    result = self._convert_with_context(value, src_units, dst_units)
                    if result is not None:
                        return result
                raise

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

    def context(self, name, **kwargs):
        return _ContextManager(self, name, kwargs)

    def _convert_with_context(self, value, src_units, dst_units):
        src_dim = self._compute_dimensionality(src_units)
        dst_dim = self._compute_dimensionality(dst_units)

        src_scale, _ = self._compute_root_units(src_units)
        base_value = value * src_scale

        for ctx, ctx_kwargs in zip(reversed(self._active_contexts),
                                    reversed(self._active_context_kwargs)):
            for rule_src, rule_dst, expr_str in ctx._rules:
                rule_src_dim = self._resolve_dim_string(rule_src)
                rule_dst_dim = self._resolve_dim_string(rule_dst)
                if rule_src_dim == src_dim and rule_dst_dim == dst_dim:
                    result = ctx._eval_transform(expr_str, base_value, {**ctx._defaults, **ctx_kwargs})
                    if result is not None:
                        dst_scale, _ = self._compute_root_units(dst_units)
                        return result / dst_scale

        return None

    def _resolve_dim_string(self, dim_str):
        dim_str = dim_str.strip()
        if dim_str.startswith("[") and dim_str.endswith("]") and " " not in dim_str:
            dim_name = dim_str
            if dim_name in self._dimensions:
                ddef = self._dimensions[dim_name]
                if ddef.reference is not None:
                    return self._expand_derived_dim(ddef.reference)
            return UnitMap({dim_name: 1})

        from .context import parse_dimension_expr
        dim_map = parse_dimension_expr(dim_str)
        result = UnitMap({})
        for dname, exp in dim_map._data.items():
            if dname in self._dimensions and self._dimensions[dname].reference is not None:
                expanded = self._expand_derived_dim(self._dimensions[dname].reference)
                for k, v in expanded._data.items():
                    result = UnitMap({**result._data, k: result._data.get(k, 0) + v * exp})
            else:
                result = UnitMap({**result._data, dname: result._data.get(dname, 0) + exp})
        return UnitMap({k: v for k, v in result._data.items() if v != 0})

    def _expand_derived_dim(self, ref_dict):
        result = {}
        for dname, exp in ref_dict.items():
            if dname in self._dimensions and self._dimensions[dname].reference is not None:
                inner = self._expand_derived_dim(self._dimensions[dname].reference)
                for k, v in inner._data.items():
                    result[k] = result.get(k, 0) + v * exp
            else:
                result[dname] = result.get(dname, 0) + exp
        return UnitMap({k: v for k, v in result.items() if v != 0})

    def Quantity(self, magnitude, units=None):
        from .quantity import Quantity
        return Quantity(magnitude, units, registry=self)

    def Unit(self, units):
        from .unit import Unit
        return Unit(units, registry=self)

    def Measurement(self, value, error=None, units=None):
        from .measurement import Measurement
        return Measurement(value, error, units, registry=self)

    def get_compatible_units(self, dimension_or_units, group=None):
        if isinstance(dimension_or_units, str):
            if dimension_or_units.startswith("["):
                target_dim = UnitMap({dimension_or_units: 1})
            else:
                target_dim = self.get_dimensionality(dimension_or_units)
        elif isinstance(dimension_or_units, UnitMap):
            target_dim = self._compute_dimensionality(dimension_or_units)
        else:
            target_dim = dimension_or_units

        result = set()
        for uname in self._units:
            try:
                udim = self._compute_dimensionality(UnitMap({uname: 1}))
                if udim == target_dim:
                    result.add(uname)
            except Exception:
                pass

        if group is not None:
            grp = self._groups.get(group) or self._systems.get(group)
            if grp is not None:
                result = result & grp.members
        return result

    def check(self, *dimensions):
        def decorator(func):
            import functools
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for i, (arg, dim_spec) in enumerate(zip(args, dimensions)):
                    if dim_spec is None:
                        continue
                    if isinstance(dim_spec, str) and dim_spec.startswith("["):
                        expected_dim = UnitMap({dim_spec: 1})
                    elif isinstance(dim_spec, str):
                        expected_dim = self.get_dimensionality(dim_spec)
                    else:
                        expected_dim = dim_spec

                    if isinstance(arg, (int, float)):
                        if bool(expected_dim):
                            raise IncompatibleDimensionError(
                                "dimensionless", str(expected_dim),
                                "dimensionless", str(expected_dim)
                            )
                    else:
                        from .quantity import Quantity
                        if isinstance(arg, Quantity):
                            actual_dim = arg.dimensionality
                            if actual_dim != expected_dim:
                                raise IncompatibleDimensionError(
                                    str(arg._units), str(expected_dim),
                                    str(actual_dim), str(expected_dim)
                                )
                return func(*args, **kwargs)
            return wrapper
        return decorator

    @property
    def sys(self):
        return _SystemAccess(self)

    def get_group(self, name):
        return self._groups.get(name)

    def get_system(self, name):
        return self._systems.get(name)

    def get_base_units(self, units, system=None):
        if isinstance(units, str):
            units = self.parse_unit_string(units)
        elif not isinstance(units, UnitMap):
            from .unit import Unit
            if isinstance(units, Unit):
                units = units.unit_map

        scale, base_units = self.get_root_units(units)

        if system is not None:
            sys_obj = self._systems.get(system)
            if sys_obj is not None:
                replacements = {}
                for new_unit, old_unit in sys_obj.rules.items():
                    resolved_old = self._resolve_unit_name(old_unit)
                    resolved_new = self._resolve_unit_name(new_unit)
                    if resolved_old and resolved_new:
                        replacements[resolved_old] = resolved_new

                for bu in sys_obj.base_units:
                    if bu not in [r[0] for r in sys_obj.rules]:
                        resolved_bu = self._resolve_unit_name(bu)
                        if resolved_bu:
                            bu_dim = self._compute_dimensionality(UnitMap({resolved_bu: 1}))
                            for si_base in list(base_units._data.keys()):
                                si_dim = self._compute_dimensionality(UnitMap({si_base: 1}))
                                if si_dim == bu_dim and si_base != resolved_bu:
                                    replacements[si_base] = resolved_bu

                new_data = dict(base_units._data)
                total_scale = scale
                for old_unit, new_unit in replacements.items():
                    if old_unit in new_data:
                        exp = new_data.pop(old_unit)
                        conv = self.get_conversion_factor(
                            UnitMap({old_unit: 1}),
                            UnitMap({new_unit: 1})
                        )
                        total_scale *= conv ** exp
                        new_data[new_unit] = exp
                return total_scale, UnitMap(new_data)

        return scale, base_units


class _SystemAccess:
    def __init__(self, registry):
        self._registry = registry

    def __getattr__(self, name):
        system = self._registry.get_system(name)
        if system is not None:
            return system
        raise AttributeError(f"System '{name}' is not defined")

    def __dir__(self):
        return list(self._registry._systems.keys())


class _ContextManager:
    def __init__(self, registry, name, kwargs):
        self._registry = registry
        self._name = name
        self._kwargs = kwargs

    def __enter__(self):
        ctx = self._registry._contexts.get(self._name)
        if ctx is None:
            raise KeyError(f"Context '{self._name}' is not defined")
        self._registry._active_contexts.append(ctx)
        self._registry._active_context_kwargs.append(self._kwargs)
        return self._registry

    def __exit__(self, *args):
        self._registry._active_contexts.pop()
        self._registry._active_context_kwargs.pop()
