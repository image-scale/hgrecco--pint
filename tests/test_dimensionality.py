"""Tests for dimensionality analysis features (Task 6)."""

import pytest
from pint import UnitRegistry
from pint.errors import IncompatibleDimensionError


@pytest.fixture
def ureg():
    return UnitRegistry()


@pytest.fixture
def Q(ureg):
    return ureg.Quantity


# ---------------------------------------------------------------------------
# is_compatible_with — Quantity
# ---------------------------------------------------------------------------

class TestQuantityIsCompatibleWith:
    def test_same_unit(self, Q):
        assert Q(1, "meter").is_compatible_with(Q(1, "meter"))

    def test_compatible_length_units(self, Q):
        assert Q(1, "meter").is_compatible_with(Q(1, "kilometer"))

    def test_compatible_length_centimeter(self, Q):
        assert Q(1, "meter").is_compatible_with(Q(5, "centimeter"))

    def test_incompatible_length_time(self, Q):
        assert not Q(1, "meter").is_compatible_with(Q(1, "second"))

    def test_incompatible_length_mass(self, Q):
        assert not Q(1, "meter").is_compatible_with(Q(1, "kilogram"))

    def test_compatible_with_string(self, Q):
        assert Q(1, "meter").is_compatible_with("kilometer")

    def test_incompatible_with_string(self, Q):
        assert not Q(1, "meter").is_compatible_with("second")

    def test_compatible_derived_units(self, Q):
        assert Q(1, "meter / second").is_compatible_with(Q(1, "kilometer / hour"))

    def test_compatible_with_unit_object(self, ureg, Q):
        assert Q(1, "meter").is_compatible_with(ureg.Unit("kilometer"))

    def test_dimensionless_compatible_with_dimensionless(self, Q):
        q1 = Q(1, "meter / meter")
        q2 = Q(1, "second / second")
        assert q1.is_compatible_with(q2)


# ---------------------------------------------------------------------------
# is_compatible_with — Unit
# ---------------------------------------------------------------------------

class TestUnitIsCompatibleWith:
    def test_same_unit(self, ureg):
        assert ureg.Unit("meter").is_compatible_with(ureg.Unit("meter"))

    def test_compatible_units(self, ureg):
        assert ureg.Unit("meter").is_compatible_with(ureg.Unit("kilometer"))

    def test_incompatible_units(self, ureg):
        assert not ureg.Unit("meter").is_compatible_with(ureg.Unit("second"))

    def test_compatible_with_string(self, ureg):
        assert ureg.Unit("meter").is_compatible_with("centimeter")

    def test_incompatible_with_string(self, ureg):
        assert not ureg.Unit("meter").is_compatible_with("kilogram")


# ---------------------------------------------------------------------------
# to_compact — basic behavior
# ---------------------------------------------------------------------------

class TestToCompact:
    def test_milli_from_small_value(self, Q):
        result = Q(0.001, "meter").to_compact()
        assert abs(result.magnitude - 1.0) < 1e-9
        assert "millimeter" in str(result.unit_map)

    def test_kilo_from_large_value(self, Q):
        result = Q(1500, "meter").to_compact()
        assert abs(result.magnitude - 1.5) < 1e-9
        assert "kilometer" in str(result.unit_map)

    def test_micro_from_very_small(self, Q):
        result = Q(1e-6, "second").to_compact()
        assert abs(result.magnitude - 1.0) < 1e-9
        assert "microsecond" in str(result.unit_map)

    def test_giga_from_very_large(self, Q):
        result = Q(1e9, "watt").to_compact()
        assert abs(result.magnitude - 1.0) < 1e-9
        assert "gigawatt" in str(result.unit_map)

    def test_mega_from_large(self, Q):
        result = Q(1e6, "hertz").to_compact()
        assert abs(result.magnitude - 1.0) < 1e-9
        assert "megahertz" in str(result.unit_map)

    def test_nano_from_small(self, Q):
        result = Q(1e-9, "meter").to_compact()
        assert abs(result.magnitude - 1.0) < 1e-9
        assert "nanometer" in str(result.unit_map)

    def test_value_near_one_stays(self, Q):
        result = Q(1.5, "meter").to_compact()
        assert abs(result.magnitude - 1.5) < 1e-9

    def test_zero_unchanged(self, Q):
        result = Q(0, "meter").to_compact()
        assert result.magnitude == 0

    def test_dimensionless_unchanged(self, Q):
        result = Q(42, "").to_compact()
        assert result.magnitude == 42

    def test_negative_value(self, Q):
        result = Q(-0.001, "meter").to_compact()
        assert abs(result.magnitude - (-1.0)) < 1e-9
        assert "millimeter" in str(result.unit_map)

    def test_compound_unit_unchanged(self, Q):
        result = Q(10, "meter / second").to_compact()
        assert abs(result.magnitude - 10) < 1e-9

    def test_with_explicit_unit(self, Q):
        result = Q(1500, "meter").to_compact("kilometer")
        assert abs(result.magnitude - 1.5) < 1e-9

    def test_no_binary_prefixes(self, Q):
        result = Q(1500, "meter").to_compact()
        unit_str = str(result.unit_map)
        assert "kibi" not in unit_str
        assert "mebi" not in unit_str


# ---------------------------------------------------------------------------
# check decorator
# ---------------------------------------------------------------------------

class TestCheckDecorator:
    def test_correct_dimensions_passes(self, ureg, Q):
        @ureg.check('[length]', '[time]')
        def speed(distance, time):
            return distance / time

        result = speed(Q(100, "meter"), Q(10, "second"))
        assert abs(result.magnitude - 10.0) < 1e-9

    def test_wrong_dimensions_raises(self, ureg, Q):
        @ureg.check('[length]', '[time]')
        def speed(distance, time):
            return distance / time

        with pytest.raises(IncompatibleDimensionError):
            speed(Q(100, "meter"), Q(10, "meter"))

    def test_none_dimension_skips_check(self, ureg, Q):
        @ureg.check('[length]', None)
        def func(distance, anything):
            return distance

        result = func(Q(5, "meter"), "not a quantity")
        assert result.magnitude == 5

    def test_scalar_with_dimensionless_ok(self, ureg):
        @ureg.check(None)
        def func(x):
            return x

        assert func(5) == 5

    def test_scalar_with_dimension_raises(self, ureg):
        @ureg.check('[length]')
        def func(x):
            return x

        with pytest.raises(IncompatibleDimensionError):
            func(5)

    def test_preserves_function_name(self, ureg, Q):
        @ureg.check('[length]')
        def my_func(x):
            """My docstring."""
            return x

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My docstring."

    def test_multiple_args_all_checked(self, ureg, Q):
        @ureg.check('[length]', '[time]', '[mass]')
        def func(a, b, c):
            return a

        with pytest.raises(IncompatibleDimensionError):
            func(Q(1, "meter"), Q(1, "second"), Q(1, "second"))

    def test_extra_args_not_checked(self, ureg, Q):
        @ureg.check('[length]')
        def func(a, b):
            return a

        result = func(Q(1, "meter"), "anything")
        assert result.magnitude == 1


# ---------------------------------------------------------------------------
# compatible_units — Quantity property
# ---------------------------------------------------------------------------

class TestCompatibleUnitsQuantity:
    def test_length_includes_meter(self, Q):
        cu = Q(1, "meter").compatible_units
        assert "meter" in cu

    def test_length_includes_kilometer(self, Q):
        cu = Q(1, "meter").compatible_units
        assert "kilometer" in cu

    def test_length_includes_centimeter(self, Q):
        cu = Q(1, "meter").compatible_units
        assert "centimeter" in cu

    def test_length_excludes_second(self, Q):
        cu = Q(1, "meter").compatible_units
        assert "second" not in cu

    def test_length_excludes_kilogram(self, Q):
        cu = Q(1, "meter").compatible_units
        assert "kilogram" not in cu

    def test_time_includes_second(self, Q):
        cu = Q(1, "second").compatible_units
        assert "second" in cu

    def test_time_includes_minute(self, Q):
        cu = Q(1, "second").compatible_units
        assert "minute" in cu

    def test_returns_set(self, Q):
        cu = Q(1, "meter").compatible_units
        assert isinstance(cu, set)


# ---------------------------------------------------------------------------
# compatible_units — Unit property
# ---------------------------------------------------------------------------

class TestCompatibleUnitsUnit:
    def test_length_includes_meter(self, ureg):
        cu = ureg.Unit("meter").compatible_units
        assert "meter" in cu

    def test_length_includes_kilometer(self, ureg):
        cu = ureg.Unit("meter").compatible_units
        assert "kilometer" in cu

    def test_length_excludes_second(self, ureg):
        cu = ureg.Unit("meter").compatible_units
        assert "second" not in cu


# ---------------------------------------------------------------------------
# get_compatible_units — registry method
# ---------------------------------------------------------------------------

class TestRegistryGetCompatibleUnits:
    def test_by_dimension_string(self, ureg):
        units = ureg.get_compatible_units("[length]")
        assert "meter" in units
        assert "kilometer" in units

    def test_by_dimension_excludes_other(self, ureg):
        units = ureg.get_compatible_units("[length]")
        assert "second" not in units

    def test_by_unit_name(self, ureg):
        units = ureg.get_compatible_units("meter")
        assert "kilometer" in units

    def test_time_dimension(self, ureg):
        units = ureg.get_compatible_units("[time]")
        assert "second" in units
        assert "minute" in units
        assert "hour" in units

    def test_mass_dimension(self, ureg):
        units = ureg.get_compatible_units("[mass]")
        assert "kilogram" in units
        assert "gram" in units

    def test_returns_set(self, ureg):
        units = ureg.get_compatible_units("[length]")
        assert isinstance(units, set)
