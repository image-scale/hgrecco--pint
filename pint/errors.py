"""Exception classes for the pint library."""


class PintError(Exception):
    """Base exception for all pint errors."""


class IncompatibleDimensionError(PintError, TypeError):
    """Raised when trying to convert or operate on quantities with
    incompatible dimensions."""

    def __init__(self, units_from, units_to, dim_from=None, dim_to=None):
        self.units_from = units_from
        self.units_to = units_to
        self.dim_from = dim_from
        self.dim_to = dim_to

    def __str__(self):
        msg = f"Cannot convert from '{self.units_from}' to '{self.units_to}'"
        if self.dim_from is not None and self.dim_to is not None:
            msg += f" (dimensions '{self.dim_from}' and '{self.dim_to}' are incompatible)"
        return msg


class UnitNotFoundError(PintError, AttributeError):
    """Raised when a unit is not found in the registry."""

    def __init__(self, unit_name):
        self.unit_name = unit_name

    def __str__(self):
        return f"Unit '{self.unit_name}' is not defined"


class DefinitionParsingError(PintError, ValueError):
    """Raised when a unit definition cannot be parsed."""

    def __init__(self, msg, line=None):
        self.msg = msg
        self.line = line

    def __str__(self):
        if self.line is not None:
            return f"Error parsing definition: {self.msg} (line: '{self.line}')"
        return f"Error parsing definition: {self.msg}"


class DuplicateDefinitionError(PintError, ValueError):
    """Raised when a unit is redefined."""

    def __init__(self, name, definition_type="unit"):
        self.name = name
        self.definition_type = definition_type

    def __str__(self):
        return f"Cannot redefine '{self.name}' ({self.definition_type})"


class OffsetUnitError(PintError, TypeError):
    """Raised for ambiguous operations with offset units (like temperature)."""

    def __init__(self, units_from, units_to):
        self.units_from = units_from
        self.units_to = units_to

    def __str__(self):
        return (
            f"Ambiguous operation with offset unit(s): "
            f"'{self.units_from}', '{self.units_to}'"
        )
