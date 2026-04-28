"""
    pint.errors
    ~~~~~~~~~~~

    Pint exception classes.
"""
from __future__ import annotations

from typing import Any

OFFSET_ERROR_DOCS_HTML = "https://pint.readthedocs.io/en/stable/user/nonmult.html"
LOG_ERROR_DOCS_HTML = "https://pint.readthedocs.io/en/stable/user/log_units.html"


class PintError(Exception):
    """Base class for all Pint errors."""

    pass


class DefinitionSyntaxError(PintError, SyntaxError):
    """Raised when there is a syntax error in a definition."""

    def __init__(self, msg: str, **kwargs):
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        return self.msg

    def __eq__(self, other):
        if not isinstance(other, DefinitionSyntaxError):
            return NotImplemented
        return self.msg == other.msg

    def __reduce__(self):
        return self.__class__, (self.msg,)


class RedefinitionError(PintError, ValueError):
    """Raised when trying to redefine a unit."""

    def __init__(self, name: str, definition_type: str):
        self.name = name
        self.definition_type = definition_type
        super().__init__(name, definition_type)

    def __str__(self) -> str:
        return f"Cannot redefine '{self.name}' ({self.definition_type})"

    def __eq__(self, other):
        if not isinstance(other, RedefinitionError):
            return NotImplemented
        return self.name == other.name and self.definition_type == other.definition_type

    def __reduce__(self):
        return self.__class__, (self.name, self.definition_type)


class UndefinedUnitError(PintError, AttributeError):
    """Raised when a unit is not defined in the registry."""

    def __init__(self, unit_names):
        if isinstance(unit_names, (set, frozenset)):
            unit_names = tuple(sorted(unit_names))
        elif isinstance(unit_names, (list, tuple)) and len(unit_names) == 1:
            unit_names = unit_names[0]
        self.unit_names = unit_names
        super().__init__(unit_names)

    def __str__(self) -> str:
        if isinstance(self.unit_names, str):
            return f"'{self.unit_names}' is not defined in the unit registry"
        return f"{self.unit_names!r} are not defined in the unit registry"

    def __eq__(self, other):
        if not isinstance(other, UndefinedUnitError):
            return NotImplemented
        return self.unit_names == other.unit_names

    def __reduce__(self):
        return self.__class__, (self.unit_names,)


class DimensionalityError(PintError, TypeError):
    """Raised when dimensions do not match."""

    def __init__(
        self,
        units1: Any,
        units2: Any,
        dim1: Any = "",
        dim2: Any = "",
        *,
        extra_msg: str = "",
    ):
        self.units1 = units1
        self.units2 = units2
        self.dim1 = dim1
        self.dim2 = dim2
        self.extra_msg = extra_msg
        super().__init__(units1, units2, dim1, dim2, extra_msg)

    def __str__(self) -> str:
        if self.dim1 or self.dim2:
            return (
                f"Cannot convert from '{self.units1}' ({self.dim1}) "
                f"to '{self.units2}' ({self.dim2}){self.extra_msg}"
            )
        return f"Cannot convert from '{self.units1}' to '{self.units2}'"

    def __eq__(self, other):
        if not isinstance(other, DimensionalityError):
            return NotImplemented
        return (
            self.units1 == other.units1
            and self.units2 == other.units2
            and self.dim1 == other.dim1
            and self.dim2 == other.dim2
            and self.extra_msg == other.extra_msg
        )

    def __reduce__(self):
        return (
            self.__class__,
            (self.units1, self.units2, self.dim1, self.dim2),
            {"extra_msg": self.extra_msg},
        )

    def __setstate__(self, state):
        self.extra_msg = state.get("extra_msg", "")


class OffsetUnitCalculusError(PintError, TypeError):
    """Raised when an operation with offset units is ambiguous."""

    def __init__(self, units1=None, units2=None):
        self.units1 = units1
        self.units2 = units2
        super().__init__(units1, units2)

    def __str__(self) -> str:
        if self.units2:
            return (
                f"Ambiguous operation with offset unit ({self.units1}, {self.units2}). "
                f"See {OFFSET_ERROR_DOCS_HTML} for guidance."
            )
        return (
            f"Ambiguous operation with offset unit ({self.units1}). "
            f"See {OFFSET_ERROR_DOCS_HTML} for guidance."
        )

    def __eq__(self, other):
        if not isinstance(other, OffsetUnitCalculusError):
            return NotImplemented
        return self.units1 == other.units1 and self.units2 == other.units2

    def __reduce__(self):
        return self.__class__, (self.units1, self.units2)


class LogarithmicUnitCalculusError(PintError, TypeError):
    """Raised when an operation with logarithmic units is ambiguous."""

    def __init__(self, units1=None, units2=None):
        self.units1 = units1
        self.units2 = units2
        super().__init__(units1, units2)

    def __str__(self) -> str:
        if self.units2:
            return (
                f"Ambiguous operation with logarithmic unit ({self.units1}, {self.units2}). "
                f"See {LOG_ERROR_DOCS_HTML} for guidance."
            )
        return (
            f"Ambiguous operation with logarithmic unit ({self.units1}). "
            f"See {LOG_ERROR_DOCS_HTML} for guidance."
        )

    def __eq__(self, other):
        if not isinstance(other, LogarithmicUnitCalculusError):
            return NotImplemented
        return self.units1 == other.units1 and self.units2 == other.units2

    def __reduce__(self):
        return self.__class__, (self.units1, self.units2)


class UnitStrippedWarning(UserWarning):
    """Warning raised when a unit is stripped from a quantity."""

    pass


class UndefinedBehavior(UserWarning):
    """Warning raised when behavior is undefined."""

    pass
