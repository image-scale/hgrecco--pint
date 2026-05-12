"""Formatting utilities for quantities and units.

Supports multiple output styles:
- D (Default): full names with spaces, e.g. "meter ** 2 / second"
- C (Compact): no spaces around operators, e.g. "meter**2/second"
- P (Pretty): unicode superscripts and dot multiplication, e.g. "meter²·second⁻¹"
- L (LaTeX): LaTeX math notation, e.g. "\\frac{\\mathrm{meter}^{2}}{\\mathrm{second}}"
- H (HTML): HTML with <sup> tags, e.g. "meter<sup>2</sup>/second"
- ~ (abbreviated): use unit symbols instead of full names
"""

import re

_SUPERSCRIPT_MAP = str.maketrans({
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
    ".": "˙",
})

_PINT_FLAGS = {"D", "C", "P", "L", "H", "~", "^"}
_MAGNITUDE_TYPES = set("bcdeEfFgGnosxX%")


def split_format_spec(spec):
    if not spec:
        return "", "D"

    unit_spec = ""
    i = len(spec) - 1
    while i >= 0 and (spec[i] in _PINT_FLAGS or spec[i] in "~^"):
        unit_spec = spec[i] + unit_spec
        i -= 1

    mag_spec = spec[:i + 1]

    if not unit_spec:
        unit_spec = "D"

    return mag_spec, unit_spec


def _to_superscript(exp_str):
    return exp_str.translate(_SUPERSCRIPT_MAP)


def _get_unit_symbol(unit_name, registry):
    if registry is None:
        return unit_name
    udef = registry._units.get(unit_name)
    if udef and udef.symbol and udef.symbol != "_":
        return udef.symbol
    for pname, pdef in registry._prefixes.items():
        if unit_name.startswith(pname):
            base_name = unit_name[len(pname):]
            base_udef = registry._units.get(base_name)
            if base_udef:
                prefix_sym = pdef.symbol if pdef.symbol else pname
                base_sym = base_udef.symbol if base_udef.symbol and base_udef.symbol != "_" else base_name
                return prefix_sym + base_sym
    return unit_name


def _sort_unit_items(unit_map):
    pos = [(k, v) for k, v in sorted(unit_map._data.items()) if v > 0]
    neg = [(k, v) for k, v in sorted(unit_map._data.items()) if v < 0]
    return pos, neg


def format_unit(unit_map, spec="D", registry=None):
    if not unit_map._data:
        return "dimensionless"

    abbreviated = "~" in spec
    as_ratio = "^" not in spec
    mode = "D"
    for ch in spec:
        if ch in ("D", "C", "P", "L", "H"):
            mode = ch
            break

    pos, neg = _sort_unit_items(unit_map)

    def name(uname):
        if abbreviated:
            return _get_unit_symbol(uname, registry)
        return uname

    if mode == "D":
        return _format_default(pos, neg, name, as_ratio)
    elif mode == "C":
        return _format_compact(pos, neg, name, as_ratio)
    elif mode == "P":
        return _format_pretty(pos, neg, name, as_ratio)
    elif mode == "L":
        return _format_latex(pos, neg, name, as_ratio)
    elif mode == "H":
        return _format_html(pos, neg, name, as_ratio)
    else:
        return _format_default(pos, neg, name, as_ratio)


def _format_exp(exp, as_int=True):
    if as_int and exp == int(exp):
        return str(int(abs(exp)))
    return str(abs(exp))


def _format_default(pos, neg, name, as_ratio):
    def fmt_part(items):
        parts = []
        for uname, exp in items:
            aexp = abs(exp)
            if aexp == 1:
                parts.append(name(uname))
            else:
                parts.append(f"{name(uname)} ** {_format_exp(exp)}")
        return " * ".join(parts)

    if as_ratio and neg:
        num = fmt_part(pos) if pos else "1"
        den = fmt_part([(n, -e) for n, e in neg])
        return f"{num} / {den}"
    else:
        all_items = pos + neg
        parts = []
        for uname, exp in all_items:
            if exp == 1:
                parts.append(name(uname))
            elif exp == -1:
                parts.append(f"{name(uname)} ** -1")
            else:
                e = int(exp) if exp == int(exp) else exp
                parts.append(f"{name(uname)} ** {e}")
        return " * ".join(parts)


def _format_compact(pos, neg, name, as_ratio):
    def fmt_part(items):
        parts = []
        for uname, exp in items:
            aexp = abs(exp)
            if aexp == 1:
                parts.append(name(uname))
            else:
                parts.append(f"{name(uname)}**{_format_exp(exp)}")
        return "*".join(parts)

    if as_ratio and neg:
        num = fmt_part(pos) if pos else "1"
        den = fmt_part([(n, -e) for n, e in neg])
        return f"{num}/{den}"
    else:
        all_items = pos + neg
        parts = []
        for uname, exp in all_items:
            if exp == 1:
                parts.append(name(uname))
            elif exp == -1:
                parts.append(f"{name(uname)}**-1")
            else:
                e = int(exp) if exp == int(exp) else exp
                parts.append(f"{name(uname)}**{e}")
        return "*".join(parts)


def _format_pretty(pos, neg, name, as_ratio):
    def fmt_item(uname, exp):
        aexp = abs(exp)
        if aexp == 1:
            return name(uname)
        exp_str = _format_exp(exp)
        return f"{name(uname)}{_to_superscript(exp_str)}"

    if as_ratio and neg:
        if pos:
            num = "·".join(fmt_item(n, e) for n, e in pos)
        else:
            num = "1"
        den = "·".join(fmt_item(n, -e) for n, e in neg)
        return f"{num} / {den}"
    else:
        all_items = pos + neg
        parts = []
        for uname, exp in all_items:
            parts.append(fmt_item(uname, exp))
        return "·".join(parts)


def _format_latex(pos, neg, name, as_ratio):
    def fmt_item(uname, exp):
        n = name(uname).replace("_", r"\_")
        aexp = abs(exp)
        if aexp == 1:
            return f"\\mathrm{{{n}}}"
        return f"\\mathrm{{{n}}}^{{{_format_exp(exp)}}}"

    if as_ratio and neg:
        if pos:
            num = " \\cdot ".join(fmt_item(n, e) for n, e in pos)
        else:
            num = "1"
        den = " \\cdot ".join(fmt_item(n, -e) for n, e in neg)
        return f"\\frac{{{num}}}{{{den}}}"
    else:
        all_items = pos + neg
        parts = []
        for uname, exp in all_items:
            n = name(uname).replace("_", r"\_")
            if exp == 1:
                parts.append(f"\\mathrm{{{n}}}")
            else:
                e = int(exp) if exp == int(exp) else exp
                parts.append(f"\\mathrm{{{n}}}^{{{e}}}")
        return " \\cdot ".join(parts)


def _format_html(pos, neg, name, as_ratio):
    def fmt_item(uname, exp):
        aexp = abs(exp)
        if aexp == 1:
            return name(uname)
        return f"{name(uname)}<sup>{_format_exp(exp)}</sup>"

    if as_ratio and neg:
        if pos:
            num = " ".join(fmt_item(n, e) for n, e in pos)
        else:
            num = "1"
        den = " ".join(fmt_item(n, -e) for n, e in neg)
        return f"{num}/{den}"
    else:
        all_items = pos + neg
        parts = []
        for uname, exp in all_items:
            parts.append(fmt_item(uname, exp))
        return " ".join(parts)


def format_quantity(magnitude, unit_map, spec="", registry=None):
    mag_spec, unit_spec = split_format_spec(spec)

    if not unit_map._data:
        if mag_spec:
            return format(magnitude, mag_spec)
        return str(magnitude)

    if mag_spec:
        mag_str = format(magnitude, mag_spec)
    else:
        mag_str = str(magnitude)

    unit_str = format_unit(unit_map, unit_spec, registry)

    if "L" in unit_spec:
        return f"{mag_str}\\ {unit_str}"

    return f"{mag_str} {unit_str}"
