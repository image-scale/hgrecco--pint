"""
    pint.facets.numpy.numpy_func
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    NumPy function overloads for pint.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ...compat import HAS_NUMPY

if HAS_NUMPY:
    from ...compat import np


# Global registries for handled functions and ufuncs
HANDLED_FUNCTIONS: Dict[str, Callable] = {}
HANDLED_UFUNCS: Dict[str, Callable] = {}


def implements(func_name: str, func_type: str = "function"):
    """Decorator to register a numpy function implementation.

    Parameters
    ----------
    func_name : str
        Name of the numpy function to implement.
    func_type : str
        Type of function: "function" or "ufunc".

    Returns
    -------
    Callable
        Decorator that registers the implementation.
    """

    def decorator(func):
        if func_type == "function":
            HANDLED_FUNCTIONS[func_name] = func
        elif func_type == "ufunc":
            HANDLED_UFUNCS[func_name] = func
        else:
            raise ValueError(f"Invalid func_type: {func_type}")
        return func

    return decorator


def _is_quantity(obj) -> bool:
    """Check if an object is a pint Quantity."""
    return hasattr(obj, "_magnitude") and hasattr(obj, "_units")


def _is_sequence_with_quantity_elements(obj) -> bool:
    """Check if an object is a sequence containing Quantity elements."""
    if isinstance(obj, (list, tuple)):
        return any(_is_quantity(item) for item in obj)
    if HAS_NUMPY and isinstance(obj, np.ndarray):
        if obj.dtype == object:
            return any(_is_quantity(item) for item in obj.flat)
    return False


def convert_to_consistent_units(*args, pre_calc_units=None, **kwargs):
    """Convert quantities to consistent units for computation.

    Returns the converted magnitudes and the output units.
    """
    from ...registry import UnitRegistry

    if not args:
        return (), None, kwargs

    # Find the first quantity to get the registry
    registry = None
    for arg in args:
        if _is_quantity(arg):
            registry = arg._REGISTRY
            break

    if registry is None:
        return args, None, kwargs

    # Convert to consistent units
    if pre_calc_units is not None:
        target_units = pre_calc_units
    else:
        # Use the units of the first quantity
        target_units = None
        for arg in args:
            if _is_quantity(arg):
                target_units = arg._units
                break

    magnitudes = []
    for arg in args:
        if _is_quantity(arg):
            if target_units is not None and arg._units != target_units:
                magnitudes.append(arg.to(target_units)._magnitude)
            else:
                magnitudes.append(arg._magnitude)
        else:
            magnitudes.append(arg)

    return tuple(magnitudes), target_units, kwargs


def get_op_output_unit(
    unit, operation: str, other_unit=None, size: Optional[int] = None
):
    """Get the output unit for a given operation.

    Parameters
    ----------
    unit : UnitsContainer
        Input unit.
    operation : str
        Name of the operation.
    other_unit : UnitsContainer, optional
        Second input unit for binary operations.
    size : int, optional
        Size for operations like sum, prod.

    Returns
    -------
    UnitsContainer
        Output unit.
    """
    from ...util import UnitsContainer

    if unit is None:
        return UnitsContainer()

    # Operations that preserve units
    preserve_ops = {
        "add",
        "subtract",
        "sum",
        "nansum",
        "cumsum",
        "mean",
        "nanmean",
        "average",
        "median",
        "nanmedian",
        "std",
        "nanstd",
        "var",
        "nanvar",
        "ptp",
        "min",
        "max",
        "minimum",
        "maximum",
        "argmin",
        "argmax",
        "amin",
        "amax",
        "nanmin",
        "nanmax",
        "clip",
        "where",
        "abs",
        "absolute",
        "negative",
        "positive",
        "sign",
        "diff",
        "ediff1d",
        "gradient",
    }

    # Operations that return dimensionless
    dimensionless_ops = {
        "equal",
        "not_equal",
        "less",
        "less_equal",
        "greater",
        "greater_equal",
        "isnan",
        "isinf",
        "isfinite",
        "all",
        "any",
        "count_nonzero",
    }

    # Operations that square units
    square_ops = {"var", "nanvar"}

    # Operations that take square root
    sqrt_ops = {"std", "nanstd"}

    if operation in dimensionless_ops:
        return UnitsContainer()

    if operation in preserve_ops:
        return unit

    if operation == "multiply":
        if other_unit is not None:
            return unit * other_unit
        return unit * unit if size and size > 1 else unit

    if operation == "divide":
        if other_unit is not None:
            return unit / other_unit
        return UnitsContainer()

    if operation == "power":
        return unit  # Power is handled specially

    if operation == "sqrt":
        return unit**0.5

    if operation in ("prod", "nanprod", "cumprod"):
        if size is not None:
            return unit**size
        return unit

    return unit


def unwrap_and_wrap_consistent_units(*args, **kwargs):
    """Unwrap quantities, compute, and rewrap result.

    Returns a function that wraps the result.
    """
    from ...util import UnitsContainer

    magnitudes, units, new_kwargs = convert_to_consistent_units(*args, **kwargs)

    def wrapper(result):
        if units is not None:
            from ...registry import UnitRegistry

            # Get registry from first quantity arg
            registry = None
            for arg in args:
                if _is_quantity(arg):
                    registry = arg._REGISTRY
                    break

            if registry is not None:
                return registry.Quantity(result, units)
        return result

    return magnitudes, wrapper


def numpy_wrap(func_type: str, func, args, kwargs, types):
    """Wrap a numpy function to handle quantities.

    Parameters
    ----------
    func_type : str
        Type of function: "function" or "ufunc".
    func : Callable
        The numpy function to wrap.
    args : tuple
        Positional arguments.
    kwargs : dict
        Keyword arguments.
    types : tuple
        Types of arguments.

    Returns
    -------
    Any
        Result of the function call.
    """
    # Get the function name
    func_name = func.__name__

    # Check if we have a handler
    if func_type == "function" and func_name in HANDLED_FUNCTIONS:
        return HANDLED_FUNCTIONS[func_name](*args, **kwargs)
    if func_type == "ufunc" and func_name in HANDLED_UFUNCS:
        return HANDLED_UFUNCS[func_name](*args, **kwargs)

    # Default: convert to magnitudes, call function, wrap result
    magnitudes, wrapper = unwrap_and_wrap_consistent_units(*args, **kwargs)
    result = func(*magnitudes, **kwargs)
    return wrapper(result)
