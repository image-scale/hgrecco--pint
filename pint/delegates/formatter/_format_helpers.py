"""
    pint.delegates.formatter._format_helpers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatting helper functions.
"""
from __future__ import annotations

from typing import Iterable, Tuple


def join_u(fmt: str, items: Iterable[str]) -> str:
    """Join items with a format string.

    Parameters
    ----------
    fmt : str
        Format string. Can be a simple separator or a format with {0} and {1} placeholders.
    items : Iterable[str]
        Items to join.

    Returns
    -------
    str
        Joined string.
    """
    items = list(items)
    if not items:
        return ""

    if "{0}" in fmt and "{1}" in fmt:
        result = items[0]
        for item in items[1:]:
            result = fmt.format(result, item)
        return result
    else:
        return fmt.join(items)


def formatter(
    num_items: Iterable[Tuple[str, int]],
    den_items: Iterable[Tuple[str, int]] = (),
    *,
    as_ratio: bool = True,
    single_denominator: bool = False,
    product_fmt: str = " * ",
    division_fmt: str = " / ",
    power_fmt: str = "{} ** {}",
    parentheses_fmt: str = "({0})",
    exp_call: callable = "{} ** {}".format,
    sort: bool = True,
) -> str:
    """Format units as a string.

    Parameters
    ----------
    num_items : Iterable[Tuple[str, int]]
        Numerator items as (unit, power) pairs.
    den_items : Iterable[Tuple[str, int]]
        Denominator items as (unit, power) pairs.
    as_ratio : bool
        If True, format as a ratio with /. If False, use negative exponents.
    single_denominator : bool
        If True, group denominator in parentheses.
    product_fmt : str
        Format string for product.
    division_fmt : str
        Format string for division.
    power_fmt : str
        Format string for powers.
    parentheses_fmt : str
        Format string for parentheses.
    exp_call : callable
        Function to format exponents.
    sort : bool
        If True, sort units alphabetically.

    Returns
    -------
    str
        Formatted string.
    """
    num_items = list(num_items)
    den_items = list(den_items)

    if sort:
        num_items = sorted(num_items, key=lambda x: x[0])
        den_items = sorted(den_items, key=lambda x: x[0])

    def format_power(unit: str, power: int) -> str:
        if power == 1:
            return unit
        return exp_call(unit, power)

    # Format numerator
    num_parts = [format_power(unit, abs(power)) for unit, power in num_items if power > 0]

    if as_ratio:
        # Format denominator as division
        den_parts = [format_power(unit, abs(power)) for unit, power in den_items]

        if num_parts:
            result = join_u(product_fmt, num_parts)
        else:
            if den_parts:
                result = "1"
            else:
                return ""

        if den_parts:
            if single_denominator and len(den_parts) > 1:
                den_str = parentheses_fmt.format(join_u(product_fmt, den_parts))
                result = result + division_fmt + den_str
            else:
                for part in den_parts:
                    result = result + division_fmt + part
    else:
        # Use negative exponents
        all_parts = num_parts + [
            format_power(unit, -abs(power)) for unit, power in den_items
        ]
        result = join_u(product_fmt, all_parts)

    return result
