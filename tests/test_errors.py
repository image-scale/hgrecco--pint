"""Tests for comprehensive error handling (Task 7)."""

import pickle
import pytest
from pint import UnitRegistry
from pint.errors import (
    PintError,
    IncompatibleDimensionError,
    UnitNotFoundError,
    DefinitionParsingError,
    DuplicateDefinitionError,
    OffsetUnitError,
)


@pytest.fixture
def ureg():
    return UnitRegistry()


@pytest.fixture
def Q(ureg):
    return ureg.Quantity


# ---------------------------------------------------------------------------
# Pickle support (__reduce__)
# ---------------------------------------------------------------------------

class TestErrorPickling:
    def test_pickle_incompatible_dimension_error(self):
        err = IncompatibleDimensionError("meter", "second", "[length]", "[time]")
        restored = pickle.loads(pickle.dumps(err))
        assert str(restored) == str(err)
        assert restored.units_from == "meter"
        assert restored.units_to == "second"
        assert restored.dim_from == "[length]"
        assert restored.dim_to == "[time]"

    def test_pickle_unit_not_found_error(self):
        err = UnitNotFoundError("foo_unit")
        restored = pickle.loads(pickle.dumps(err))
        assert str(restored) == str(err)
        assert restored.unit_name == "foo_unit"

    def test_pickle_definition_parsing_error(self):
        err = DefinitionParsingError("bad syntax", "some_line = ???")
        restored = pickle.loads(pickle.dumps(err))
        assert str(restored) == str(err)
        assert restored.msg == "bad syntax"
        assert restored.line == "some_line = ???"

    def test_pickle_duplicate_definition_error(self):
        err = DuplicateDefinitionError("meter", "unit")
        restored = pickle.loads(pickle.dumps(err))
        assert str(restored) == str(err)
        assert restored.name == "meter"
        assert restored.definition_type == "unit"

    def test_pickle_offset_unit_error(self):
        err = OffsetUnitError("degC", "degF")
        restored = pickle.loads(pickle.dumps(err))
        assert str(restored) == str(err)
        assert restored.units_from == "degC"
        assert restored.units_to == "degF"


# ---------------------------------------------------------------------------
# Error message content
# ---------------------------------------------------------------------------

class TestErrorMessages:
    def test_incompatible_dimension_includes_units(self):
        err = IncompatibleDimensionError("meter", "second")
        msg = str(err)
        assert "meter" in msg
        assert "second" in msg

    def test_incompatible_dimension_includes_dimensions(self):
        err = IncompatibleDimensionError("meter", "second", "[length]", "[time]")
        msg = str(err)
        assert "[length]" in msg
        assert "[time]" in msg
        assert "incompatible" in msg

    def test_unit_not_found_includes_name(self):
        err = UnitNotFoundError("quuxwatt")
        msg = str(err)
        assert "quuxwatt" in msg
        assert "unit registry" in msg

    def test_definition_parsing_includes_line(self):
        err = DefinitionParsingError("invalid format", "foo = bar baz")
        msg = str(err)
        assert "foo = bar baz" in msg
        assert "invalid format" in msg

    def test_definition_parsing_without_line(self):
        err = DefinitionParsingError("something went wrong")
        msg = str(err)
        assert "something went wrong" in msg
        assert "line" not in msg

    def test_duplicate_definition_includes_name_and_type(self):
        err = DuplicateDefinitionError("meter", "unit")
        msg = str(err)
        assert "meter" in msg
        assert "unit" in msg

    def test_offset_unit_error_includes_units(self):
        err = OffsetUnitError("degC", "degF")
        msg = str(err)
        assert "degC" in msg
        assert "degF" in msg
        assert "offset" in msg.lower()

    def test_offset_unit_error_single_unit(self):
        err = OffsetUnitError("degC")
        msg = str(err)
        assert "degC" in msg
        assert "offset" in msg.lower()


# ---------------------------------------------------------------------------
# Errors raised during operations
# ---------------------------------------------------------------------------

class TestErrorsInOperations:
    def test_convert_incompatible_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError) as exc_info:
            Q(1, "meter").to("second")
        assert "meter" in str(exc_info.value)

    def test_add_incompatible_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1, "meter") + Q(1, "second")

    def test_sub_incompatible_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1, "meter") - Q(1, "second")

    def test_undefined_unit_raises(self, Q):
        with pytest.raises(UnitNotFoundError) as exc_info:
            Q(1, "nonexistent_unit")
        assert "nonexistent_unit" in str(exc_info.value)

    def test_float_non_dimensionless_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            float(Q(1, "meter"))

    def test_int_non_dimensionless_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            int(Q(1, "meter"))

    def test_add_scalar_to_dimensioned_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1, "meter") + 5

    def test_sub_scalar_from_dimensioned_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1, "meter") - 5


# ---------------------------------------------------------------------------
# Base class catching
# ---------------------------------------------------------------------------

class TestBaseClassCatching:
    def test_incompatible_caught_as_pint_error(self, Q):
        with pytest.raises(PintError):
            Q(1, "meter").to("second")

    def test_incompatible_caught_as_type_error(self, Q):
        with pytest.raises(TypeError):
            Q(1, "meter").to("second")

    def test_unit_not_found_caught_as_pint_error(self, Q):
        with pytest.raises(PintError):
            Q(1, "nonexistent_unit")

    def test_unit_not_found_caught_as_attribute_error(self, Q):
        with pytest.raises(AttributeError):
            Q(1, "nonexistent_unit")

    def test_definition_parsing_caught_as_pint_error(self):
        with pytest.raises(PintError):
            raise DefinitionParsingError("test")

    def test_definition_parsing_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise DefinitionParsingError("test")

    def test_duplicate_caught_as_pint_error(self):
        with pytest.raises(PintError):
            raise DuplicateDefinitionError("x")

    def test_duplicate_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise DuplicateDefinitionError("x")

    def test_offset_caught_as_pint_error(self):
        with pytest.raises(PintError):
            raise OffsetUnitError("degC")

    def test_offset_caught_as_type_error(self):
        with pytest.raises(TypeError):
            raise OffsetUnitError("degC")
