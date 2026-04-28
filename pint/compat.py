"""
    pint.compat
    ~~~~~~~~~~~

    Compatibility layer for different Python versions and optional dependencies.
"""
from __future__ import annotations

import math
import tokenize
from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction
from numbers import Number
from typing import Any, NoReturn, TypeVar

# NumPy support
HAS_NUMPY = False
HAS_NUMPY_ARRAY_FUNCTION = False
NUMPY_VER = "0"
try:
    import numpy as np

    HAS_NUMPY = True
    NUMPY_VER = np.__version__
    HAS_NUMPY_ARRAY_FUNCTION = True
except ImportError:
    np = None  # type: ignore


# Uncertainties support
HAS_UNCERTAINTIES = False
try:
    import uncertainties

    HAS_UNCERTAINTIES = True
except ImportError:
    uncertainties = None  # type: ignore


# Babel support
HAS_BABEL = False
try:
    import babel

    HAS_BABEL = True
except ImportError:
    babel = None  # type: ignore


# SciPy support
HAS_SCIPY = False
try:
    import scipy

    HAS_SCIPY = True
except ImportError:
    scipy = None  # type: ignore


# Dask support
HAS_DASK = False
try:
    import dask

    HAS_DASK = True
except ImportError:
    dask = None  # type: ignore


T = TypeVar("T")


def is_duck_array_type(cls: type) -> bool:
    """Check if cls is a type that should be treated as a duck array."""
    if not HAS_NUMPY:
        return False
    # NumPy arrays
    if issubclass(cls, np.ndarray):
        return True
    # Duck arrays - check for __array_ufunc__ or __array_function__
    return hasattr(cls, "__array_ufunc__") or hasattr(cls, "__array_function__")


def is_duck_array(obj) -> bool:
    """Check if obj is a duck array (numpy-like)."""
    if obj is None:
        return False
    return is_duck_array_type(type(obj))


def _to_magnitude(value, force_ndarray=False, force_ndarray_like=False):
    """Convert value to magnitude."""
    if isinstance(value, (int, float, complex, Decimal, Fraction)):
        return value
    if HAS_NUMPY and isinstance(value, np.ndarray):
        return value
    if isinstance(value, (list, tuple)):
        if HAS_NUMPY and (force_ndarray or force_ndarray_like):
            return np.asarray(value)
        return value
    if is_duck_array(value):
        return value
    return value


def eq(lhs, rhs, check_all: bool):
    """Check equality between lhs and rhs.

    If check_all is True, return a single boolean (all elements must match).
    If check_all is False, return element-wise comparison.
    """
    if HAS_NUMPY:
        if isinstance(lhs, np.ndarray) or isinstance(rhs, np.ndarray):
            result = np.equal(lhs, rhs)
            if check_all:
                return bool(np.all(result))
            return result
    return lhs == rhs


def isnan(value, check_all: bool):
    """Check if value is NaN.

    If check_all is True, return a single boolean (any element is NaN).
    If check_all is False, return element-wise comparison.
    """
    if HAS_NUMPY:
        if isinstance(value, np.ndarray):
            # Handle datetime64 NaT
            if np.issubdtype(value.dtype, np.datetime64):
                result = np.isnat(value)
            elif np.issubdtype(value.dtype, np.floating):
                result = np.isnan(value)
            else:
                # Non-numeric types - can't be NaN
                result = np.zeros(value.shape, dtype=bool)
            if check_all:
                return bool(np.any(result))
            return result
        # Scalar numpy datetime64
        if isinstance(value, np.datetime64):
            result = np.isnat(value)
            return bool(result) if check_all else result
        if isinstance(value, np.floating):
            result = np.isnan(value)
            return bool(result) if check_all else result
    # Regular Python types
    try:
        result = math.isnan(value)
        return result
    except (TypeError, ValueError):
        return False


def zero_or_nan(value, check_all: bool):
    """Check if value is zero or NaN.

    If check_all is True, return a single boolean (all elements are zero or NaN).
    If check_all is False, return element-wise comparison.
    """
    if HAS_NUMPY:
        if isinstance(value, np.ndarray):
            # Handle datetime64 NaT
            if np.issubdtype(value.dtype, np.datetime64):
                result = np.isnat(value)
            elif np.issubdtype(value.dtype, np.floating):
                result = np.isnan(value) | (value == 0)
            elif np.issubdtype(value.dtype, np.number):
                result = value == 0
            else:
                # Non-numeric types
                result = np.zeros(value.shape, dtype=bool)
            if check_all:
                return bool(np.all(result))
            return result
        if isinstance(value, np.floating):
            result = np.isnan(value) or value == 0
            return bool(result) if check_all else result
    # Regular Python types
    try:
        if math.isnan(value):
            return True
    except (TypeError, ValueError):
        pass
    try:
        return value == 0
    except (TypeError, ValueError):
        return False


# Type alias for numeric types
Numeric = Number
