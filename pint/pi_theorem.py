"""
    pint.pi_theorem
    ~~~~~~~~~~~~~~~

    Buckingham Pi theorem implementation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .util import UnitsContainer

logger = logging.getLogger(__name__)


def pi_theorem(
    quantities: Dict[str, Any],
    registry: Optional[Any] = None,
) -> List[Dict[str, float]]:
    """Apply the Buckingham Pi theorem.

    Given a set of dimensional quantities, find the dimensionless
    combinations that can be formed from them.

    Parameters
    ----------
    quantities : dict
        Dictionary mapping quantity names to their units/dimensions.
        Units can be strings, Quantity objects, Unit objects, or
        UnitsContainer objects.
    registry : UnitRegistry, optional
        Registry to use for parsing units. If not provided, the
        application registry is used.

    Returns
    -------
    list of dict
        List of dictionaries, each representing a dimensionless
        combination. Keys are quantity names, values are exponents.
    """
    if registry is None:
        from . import get_application_registry

        registry = get_application_registry()

    # Get the dimensionality of each quantity
    dim_matrix = {}
    all_dims = set()

    for name, unit_like in quantities.items():
        # Convert to dimensionality
        if isinstance(unit_like, str):
            dim = registry.get_dimensionality(unit_like)
        elif hasattr(unit_like, "dimensionality"):
            dim = unit_like.dimensionality
        elif hasattr(unit_like, "_units"):
            dim = registry.get_dimensionality(unit_like._units)
        elif isinstance(unit_like, UnitsContainer):
            dim = registry.get_dimensionality(unit_like)
        else:
            dim = registry.get_dimensionality(str(unit_like))

        dim_matrix[name] = dict(dim)
        all_dims.update(dim.keys())

        logger.debug(f"Quantity {name}: dimensionality = {dim}")

    # Build the matrix
    dims = sorted(all_dims)
    names = sorted(quantities.keys())

    logger.debug(f"Dimensions: {dims}")
    logger.debug(f"Quantities: {names}")

    matrix = []
    for dim in dims:
        row = [dim_matrix[name].get(dim, 0) for name in names]
        matrix.append(row)

    logger.debug(f"Matrix: {matrix}")

    # Find the null space of the matrix
    # This gives us the dimensionless combinations
    null_space = _find_null_space(matrix, len(names))

    logger.debug(f"Null space: {null_space}")

    # Convert to output format
    result = []
    for vec in null_space:
        combo = {}
        for i, name in enumerate(names):
            if vec[i] != 0:
                combo[name] = vec[i]
        if combo:
            result.append(combo)

    return result


def _find_null_space(matrix: List[List[float]], n_cols: int) -> List[List[float]]:
    """Find the null space of a matrix using Gaussian elimination."""
    if not matrix:
        return [[1.0] * n_cols]

    # Make a copy and convert to float
    m = [[float(x) for x in row] for row in matrix]
    n_rows = len(m)

    # Augment with identity
    for i, row in enumerate(m):
        row.extend([0.0] * n_cols)
        row[n_cols + i] = 1.0

    # Gaussian elimination
    pivot_row = 0
    pivot_cols = []

    for col in range(n_cols):
        # Find pivot
        max_row = pivot_row
        for row in range(pivot_row + 1, n_rows):
            if abs(m[row][col]) > abs(m[max_row][col]):
                max_row = row

        if abs(m[max_row][col]) < 1e-10:
            continue

        # Swap rows
        m[pivot_row], m[max_row] = m[max_row], m[pivot_row]
        pivot_cols.append(col)

        # Scale pivot row
        scale = m[pivot_row][col]
        for j in range(len(m[pivot_row])):
            m[pivot_row][j] /= scale

        # Eliminate column
        for row in range(n_rows):
            if row != pivot_row:
                factor = m[row][col]
                for j in range(len(m[row])):
                    m[row][j] -= factor * m[pivot_row][j]

        pivot_row += 1
        if pivot_row >= n_rows:
            break

    # Find free variables (columns not in pivot_cols)
    free_cols = [i for i in range(n_cols) if i not in pivot_cols]

    if not free_cols:
        return []

    # Build null space vectors
    result = []
    for free_col in free_cols:
        vec = [0.0] * n_cols
        vec[free_col] = 1.0

        # Back substitute
        for i, pivot_col in enumerate(pivot_cols):
            vec[pivot_col] = -m[i][free_col]

        result.append(vec)

    return result
