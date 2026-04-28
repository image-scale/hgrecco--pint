"""
    pint.testing
    ~~~~~~~~~~~~

    Testing utilities for pint.
"""
from __future__ import annotations

from typing import Any

from .compat import HAS_NUMPY

if HAS_NUMPY:
    from .compat import np


def assert_equal(first: Any, second: Any, check_units: bool = True) -> None:
    """Assert that two quantities are equal.

    Parameters
    ----------
    first : Any
        First value to compare.
    second : Any
        Second value to compare.
    check_units : bool
        Whether to check that units match.

    Raises
    ------
    AssertionError
        If the values are not equal.
    """
    # Check if they're both quantities
    first_is_q = hasattr(first, "_units") and hasattr(first, "_magnitude")
    second_is_q = hasattr(second, "_units") and hasattr(second, "_magnitude")

    if first_is_q and not second_is_q:
        if first.dimensionless:
            first = first.to("").magnitude
        else:
            raise AssertionError("The first is not dimensionless")

    if second_is_q and not first_is_q:
        if second.dimensionless:
            second = second.to("").magnitude
        else:
            raise AssertionError("The second is not dimensionless")

    if first_is_q and second_is_q:
        # Check units
        if check_units and first._units != second._units:
            raise AssertionError(
                f"Units are not equal: {first._units} != {second._units}"
            )

        first_mag = first._magnitude
        second_mag = second._magnitude
    else:
        first_mag = first
        second_mag = second

    # Compare magnitudes
    if HAS_NUMPY:
        if isinstance(first_mag, np.ndarray) or isinstance(second_mag, np.ndarray):
            if not np.array_equal(first_mag, second_mag):
                raise AssertionError(
                    f"Magnitudes are not equal: {first_mag} != {second_mag}"
                )
            return

    if first_mag != second_mag:
        # Check for NaN
        try:
            import math

            if math.isnan(first_mag) and math.isnan(second_mag):
                return
        except (TypeError, ValueError):
            pass

        raise AssertionError(
            f"Magnitudes are not equal: {first_mag} != {second_mag}"
        )


def assert_allclose(
    first: Any,
    second: Any,
    rtol: float = 1e-7,
    atol: float = 0,
    check_units: bool = True,
) -> None:
    """Assert that two quantities are close.

    Parameters
    ----------
    first : Any
        First value to compare.
    second : Any
        Second value to compare.
    rtol : float
        Relative tolerance.
    atol : float
        Absolute tolerance.
    check_units : bool
        Whether to check that units match.

    Raises
    ------
    AssertionError
        If the values are not close.
    """
    # Check if they're both quantities
    first_is_q = hasattr(first, "_units") and hasattr(first, "_magnitude")
    second_is_q = hasattr(second, "_units") and hasattr(second, "_magnitude")

    if first_is_q and second_is_q:
        # Check units
        if check_units and first._units != second._units:
            raise AssertionError(
                f"Units are not equal: {first._units} != {second._units}"
            )

        first_mag = first._magnitude
        second_mag = second._magnitude
    else:
        first_mag = first
        second_mag = second

    # Compare magnitudes
    if HAS_NUMPY:
        np.testing.assert_allclose(first_mag, second_mag, rtol=rtol, atol=atol)
    else:
        diff = abs(first_mag - second_mag)
        tol = atol + rtol * abs(second_mag)
        if diff > tol:
            raise AssertionError(
                f"Values are not close: {first_mag} != {second_mag}"
            )
