"""Context class for dimension-dependent conversions."""

import re
from .unit_map import UnitMap


_DIM_PATTERN = re.compile(r"\[[\w]+\]")


class Context:
    """Represents a conversion context that enables normally incompatible conversions."""

    __slots__ = ("_name", "_aliases", "_defaults", "_rules", "_registry")

    def __init__(self, name, aliases=(), defaults=None, rules=(), registry=None):
        self._name = name
        self._aliases = tuple(aliases)
        self._defaults = defaults or {}
        self._rules = list(rules)
        self._registry = registry

    @property
    def name(self):
        return self._name

    @property
    def aliases(self):
        return self._aliases

    @property
    def defaults(self):
        return dict(self._defaults)

    def transform(self, src_dim, dst_dim, value, **kwargs):
        params = dict(self._defaults)
        params.update(kwargs)

        for rule_src, rule_dst, expr_str in self._rules:
            if rule_src == src_dim and rule_dst == dst_dim:
                return self._eval_transform(expr_str, value, params)

        return None

    def has_rule(self, src_dim, dst_dim):
        for rule_src, rule_dst, _ in self._rules:
            if rule_src == src_dim and rule_dst == dst_dim:
                return True
        return False

    def _eval_transform(self, expr_str, value, params):
        from .expression_parser import parse_unit_expression

        ns = {"value": value}
        ns.update(params)

        if self._registry is not None:
            for cname in list(self._registry._units.keys()):
                udef = self._registry._units[cname]
                if cname in ("speed_of_light", "c", "planck_constant",
                             "boltzmann_constant", "N_A", "avogadro_number",
                             "elementary_charge", "e"):
                    scale, base = self._registry.get_root_units(UnitMap({cname: 1}))
                    ns.setdefault(cname, scale)

            for cname, udef in self._registry._units.items():
                if hasattr(udef, 'is_base') and not udef.is_base:
                    if cname not in ns:
                        try:
                            scale, base = self._registry.get_root_units(UnitMap({cname: 1}))
                            if not base._data:
                                ns.setdefault(cname, scale)
                        except Exception:
                            pass

        import math
        safe_ns = {"__builtins__": {}}
        safe_ns["pi"] = math.pi
        safe_ns["π"] = math.pi
        safe_ns.update(ns)

        try:
            return eval(expr_str, safe_ns)
        except Exception:
            return None

    def __repr__(self):
        return f"<Context('{self._name}')>"


def parse_dimension_expr(expr):
    expr = expr.strip()
    dims = {}
    tokens = re.findall(r"\[[\w]+\]|\*\*|[*/]|[\d.]+", expr)
    i = 0
    sign = 1
    while i < len(tokens):
        tok = tokens[i]
        if _DIM_PATTERN.match(tok):
            exp = sign
            if i + 2 < len(tokens) and tokens[i + 1] == "**":
                exp = sign * float(tokens[i + 2])
                if exp == int(exp):
                    exp = int(exp)
                i += 2
            dims[tok] = dims.get(tok, 0) + exp
            sign = 1
        elif tok == "/":
            sign = -1
        elif tok == "*":
            sign = 1
        i += 1
    return UnitMap(dims)
