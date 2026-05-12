"""Tests for the core pint functionality: registry, quantity, unit, and conversion."""

import math
import pytest
from pint import UnitRegistry, Quantity, Unit, UnitMap
from pint.errors import IncompatibleDimensionError, UnitNotFoundError


@pytest.fixture(scope="module")
def ureg():
    return UnitRegistry()


@pytest.fixture
def Q(ureg):
    return ureg.Quantity


@pytest.fixture
def U(ureg):
    return ureg.Unit


# ============================================================
# Registry loading and configuration
# ============================================================

class TestRegistryLoading:
    def test_registry_loads_default_definitions(self, ureg):
        assert len(ureg._units) > 50
        assert len(ureg._prefixes) > 10
        assert len(ureg._dimensions) > 5

    def test_registry_has_base_units(self, ureg):
        for name in ["meter", "second", "gram", "ampere", "kelvin", "mole", "candela"]:
            assert name in ureg._units
            assert ureg._units[name].is_base

    def test_registry_has_prefixes(self, ureg):
        for name in ["kilo", "milli", "micro", "mega", "giga", "centi"]:
            assert name in ureg._prefixes

    def test_registry_has_derived_units(self, ureg):
        for name in ["newton", "joule", "watt", "pascal", "hertz", "volt"]:
            assert name in ureg._units
            assert not ureg._units[name].is_base

    def test_registry_has_dimensions(self, ureg):
        for dim in ["[length]", "[time]", "[mass]", "[current]", "[temperature]"]:
            assert dim in ureg._dimensions

    def test_registry_parses_constants(self, ureg):
        assert "speed_of_light" in ureg._units or "speed_of_light" in ureg._name_map

    def test_import_directive_loads_constants(self, ureg):
        c = ureg.Quantity(1, "speed_of_light")
        base = c.to_base_units()
        assert abs(base.magnitude - 299792458.0) < 1.0

    def test_prefix_resolution(self, ureg):
        canonical = ureg.get_canonical_name("kilometer")
        assert canonical == "kilometer"
        q = ureg.Quantity(1, "kilometer")
        base = q.to_base_units()
        assert abs(base.magnitude - 1000.0) < 1e-10

    def test_symbol_resolution(self, ureg):
        canonical = ureg.get_canonical_name("m")
        assert canonical == "meter"

    def test_alias_resolution(self, ureg):
        canonical = ureg.get_canonical_name("metre")
        assert canonical == "meter"

    def test_derived_dimension_parsing(self, ureg):
        area_dim = ureg._dimensions.get("[area]")
        assert area_dim is not None
        assert area_dim.reference is not None

    def test_undefined_unit_raises(self, ureg):
        with pytest.raises(UnitNotFoundError):
            ureg.get_canonical_name("nonexistent_xyz")


# ============================================================
# Quantity creation
# ============================================================

class TestQuantityCreation:
    def test_create_with_string_units(self, Q):
        q = Q(5.0, "meter")
        assert q.magnitude == 5.0
        assert q.unit_map == UnitMap({"meter": 1})

    def test_create_with_unit_map(self, Q):
        q = Q(3.0, UnitMap({"meter": 1}))
        assert q.magnitude == 3.0

    def test_create_with_no_units(self, Q):
        q = Q(7.0)
        assert q.magnitude == 7.0
        assert q.dimensionless

    def test_create_from_another_quantity(self, Q):
        q1 = Q(5.0, "meter")
        q2 = Q(q1)
        assert q2.magnitude == 5.0
        assert q2.unit_map == q1.unit_map

    def test_create_from_quantity_with_conversion(self, Q):
        q1 = Q(1.0, "kilometer")
        q2 = Q(q1, "meter")
        assert abs(q2.magnitude - 1000.0) < 1e-10

    def test_magnitude_property(self, Q):
        q = Q(42.0, "second")
        assert q.magnitude == 42.0
        assert q.m == 42.0

    def test_units_property(self, Q, ureg):
        q = Q(5.0, "meter")
        u = q.units
        assert isinstance(u, Unit)
        assert str(u) == "meter"


# ============================================================
# Quantity arithmetic
# ============================================================

class TestQuantityArithmetic:
    def test_add_same_units(self, Q):
        result = Q(3.0, "meter") + Q(2.0, "meter")
        assert result.magnitude == 5.0
        assert result.unit_map == UnitMap({"meter": 1})

    def test_add_compatible_units(self, Q):
        result = Q(1.0, "kilometer") + Q(500.0, "meter")
        assert abs(result.magnitude - 1.5) < 1e-10
        assert result.unit_map == UnitMap({"kilometer": 1})

    def test_add_incompatible_units_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1.0, "meter") + Q(1.0, "second")

    def test_subtract_same_units(self, Q):
        result = Q(5.0, "meter") - Q(2.0, "meter")
        assert result.magnitude == 3.0

    def test_subtract_compatible_units(self, Q):
        result = Q(1.0, "kilometer") - Q(200.0, "meter")
        assert abs(result.magnitude - 0.8) < 1e-10

    def test_multiply_by_scalar(self, Q):
        q = Q(3.0, "meter")
        result = q * 2
        assert result.magnitude == 6.0
        assert result.unit_map == UnitMap({"meter": 1})

    def test_scalar_multiply(self, Q):
        result = 2 * Q(3.0, "meter")
        assert result.magnitude == 6.0

    def test_multiply_quantities(self, Q):
        q1 = Q(3.0, "meter")
        q2 = Q(4.0, "second")
        result = q1 * q2
        assert result.magnitude == 12.0
        assert result.unit_map == UnitMap({"meter": 1, "second": 1})

    def test_divide_by_scalar(self, Q):
        result = Q(6.0, "meter") / 2
        assert result.magnitude == 3.0

    def test_divide_quantities(self, Q):
        result = Q(10.0, "meter") / Q(2.0, "second")
        assert result.magnitude == 5.0
        assert result.unit_map == UnitMap({"meter": 1, "second": -1})

    def test_divide_same_units_gives_dimensionless(self, Q):
        result = Q(10.0, "meter") / Q(2.0, "meter")
        assert result.magnitude == 5.0
        assert result.dimensionless

    def test_power(self, Q):
        result = Q(3.0, "meter") ** 2
        assert result.magnitude == 9.0
        assert result.unit_map == UnitMap({"meter": 2})

    def test_power_negative(self, Q):
        result = Q(2.0, "second") ** -1
        assert result.magnitude == 0.5
        assert result.unit_map == UnitMap({"second": -1})

    def test_negate(self, Q):
        result = -Q(5.0, "meter")
        assert result.magnitude == -5.0

    def test_abs(self, Q):
        result = abs(Q(-5.0, "meter"))
        assert result.magnitude == 5.0

    def test_floor_div(self, Q):
        result = Q(7.0, "meter") // 2
        assert result.magnitude == 3.0

    def test_mod(self, Q):
        result = Q(7.0, "meter") % Q(3.0, "meter")
        assert result.magnitude == 1.0

    def test_scalar_divide(self, Q):
        result = 1 / Q(2.0, "second")
        assert result.magnitude == 0.5
        assert result.unit_map == UnitMap({"second": -1})


# ============================================================
# Quantity conversion
# ============================================================

class TestQuantityConversion:
    def test_convert_length(self, Q):
        q = Q(1.0, "kilometer").to("meter")
        assert abs(q.magnitude - 1000.0) < 1e-10

    def test_convert_back(self, Q):
        q = Q(1000.0, "meter").to("kilometer")
        assert abs(q.magnitude - 1.0) < 1e-10

    def test_convert_time(self, Q):
        q = Q(1.0, "hour").to("second")
        assert abs(q.magnitude - 3600.0) < 1e-10

    def test_convert_compound_units(self, Q):
        q = Q(1.0, "kilometer / hour")
        result = q.to("meter / second")
        expected = 1000.0 / 3600.0
        assert abs(result.magnitude - expected) < 1e-10

    def test_convert_incompatible_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1.0, "meter").to("second")

    def test_to_base_units(self, Q):
        q = Q(5.0, "kilometer")
        base = q.to_base_units()
        assert abs(base.magnitude - 5000.0) < 1e-10
        assert "meter" in base.unit_map

    def test_to_base_units_compound(self, Q):
        q = Q(1.0, "newton")
        base = q.to_base_units()
        assert "meter" in base.unit_map
        assert "gram" in base.unit_map
        assert "second" in base.unit_map

    def test_convert_mass(self, Q):
        q = Q(1.0, "kilogram").to("gram")
        assert abs(q.magnitude - 1000.0) < 1e-10

    def test_convert_energy(self, Q):
        q = Q(1.0, "joule")
        base = q.to_base_units()
        assert abs(base.magnitude - 1000.0) < 1e-6  # 1 J = 1000 g * m^2 / s^2

    def test_inplace_conversion(self, Q):
        q = Q(5.0, "kilometer")
        q.ito("meter")
        assert abs(q.magnitude - 5000.0) < 1e-10

    def test_convert_minute_to_second(self, Q):
        q = Q(2.0, "minute").to("second")
        assert abs(q.magnitude - 120.0) < 1e-10

    def test_convert_preserves_value(self, Q):
        q1 = Q(100.0, "centimeter")
        q2 = q1.to("meter")
        q3 = q2.to("centimeter")
        assert abs(q3.magnitude - 100.0) < 1e-10


# ============================================================
# Quantity equality and comparison
# ============================================================

class TestQuantityEquality:
    def test_equal_same_units(self, Q):
        assert Q(5.0, "meter") == Q(5.0, "meter")

    def test_not_equal_different_magnitude(self, Q):
        assert Q(5.0, "meter") != Q(6.0, "meter")

    def test_equal_different_units(self, Q):
        assert Q(1000.0, "millimeter") == Q(1.0, "meter")

    def test_equal_compatible_conversion(self, Q):
        assert Q(1.0, "kilometer") == Q(1000.0, "meter")

    def test_not_equal_incompatible(self, Q):
        assert Q(1.0, "meter") != Q(1.0, "second")

    def test_hash_equal_same_quantity(self, Q):
        q1 = Q(1.0, "meter")
        q2 = Q(1.0, "meter")
        assert hash(q1) == hash(q2)

    def test_hash_equal_converted(self, Q):
        q1 = Q(1000.0, "millimeter")
        q2 = Q(1.0, "meter")
        assert hash(q1) == hash(q2)

    def test_less_than(self, Q):
        assert Q(1.0, "meter") < Q(2.0, "meter")

    def test_less_than_different_units(self, Q):
        assert Q(500.0, "meter") < Q(1.0, "kilometer")

    def test_greater_than(self, Q):
        assert Q(2.0, "meter") > Q(1.0, "meter")

    def test_less_equal(self, Q):
        assert Q(1.0, "meter") <= Q(1.0, "meter")
        assert Q(1.0, "meter") <= Q(2.0, "meter")

    def test_greater_equal(self, Q):
        assert Q(2.0, "meter") >= Q(1.0, "meter")
        assert Q(2.0, "meter") >= Q(2.0, "meter")


# ============================================================
# Quantity type conversions
# ============================================================

class TestQuantityTypeConversion:
    def test_float_dimensionless(self, Q):
        q = Q(5.0, "meter") / Q(2.0, "meter")
        assert float(q) == 2.5

    def test_int_dimensionless(self, Q):
        q = Q(6.0, "meter") / Q(2.0, "meter")
        assert int(q) == 3

    def test_float_with_units_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            float(Q(5.0, "meter"))

    def test_int_with_units_raises(self, Q):
        with pytest.raises(IncompatibleDimensionError):
            int(Q(5.0, "meter"))

    def test_bool_nonzero(self, Q):
        assert bool(Q(1.0, "meter"))

    def test_bool_zero(self, Q):
        assert not bool(Q(0.0, "meter"))

    def test_round(self, Q):
        q = Q(3.7, "meter")
        result = round(q)
        assert result.magnitude == 4


# ============================================================
# Dimensionality
# ============================================================

class TestDimensionality:
    def test_base_unit_dimensionality(self, ureg):
        dim = ureg.get_dimensionality("meter")
        assert dim == UnitMap({"[length]": 1})

    def test_derived_unit_dimensionality(self, ureg):
        dim = ureg.get_dimensionality("newton")
        assert dim["[mass]"] == 1
        assert dim["[length]"] == 1
        assert dim["[time]"] == -2

    def test_compound_dimensionality(self, Q):
        q = Q(1.0, "meter / second")
        dim = q.dimensionality
        assert dim["[length]"] == 1
        assert dim["[time]"] == -1

    def test_dimensionless_quantity(self, Q):
        q = Q(5.0)
        assert q.dimensionless

    def test_non_dimensionless(self, Q):
        q = Q(5.0, "meter")
        assert not q.dimensionless

    def test_dimensionality_after_multiplication(self, Q):
        q = Q(3.0, "meter") * Q(2.0, "second")
        dim = q.dimensionality
        assert dim["[length]"] == 1
        assert dim["[time]"] == 1


# ============================================================
# Unit class
# ============================================================

class TestUnitClass:
    def test_create_unit_from_string(self, U):
        u = U("meter")
        assert u.unit_map == UnitMap({"meter": 1})

    def test_unit_dimensionality(self, U):
        u = U("meter")
        assert u.dimensionality == UnitMap({"[length]": 1})

    def test_unit_multiplication(self, U):
        u1 = U("meter")
        u2 = U("second")
        result = u1 * u2
        assert isinstance(result, Unit)
        assert result.unit_map == UnitMap({"meter": 1, "second": 1})

    def test_unit_division(self, U):
        result = U("meter") / U("second")
        assert result.unit_map == UnitMap({"meter": 1, "second": -1})

    def test_unit_power(self, U):
        result = U("meter") ** 2
        assert result.unit_map == UnitMap({"meter": 2})

    def test_unit_equality(self, U):
        assert U("meter") == U("meter")

    def test_unit_inequality(self, U):
        assert U("meter") != U("second")

    def test_unit_dimensionless(self, U):
        u = U("radian")
        assert u.dimensionless

    def test_scalar_times_unit(self, U, ureg):
        result = 5 * U("meter")
        assert isinstance(result, Quantity)
        assert result.magnitude == 5
        assert result.unit_map == UnitMap({"meter": 1})

    def test_unit_string_representation(self, U):
        u = U("meter")
        assert str(u) == "meter"


# ============================================================
# String representation
# ============================================================

class TestStringRepresentation:
    def test_str_basic(self, Q):
        assert str(Q(5.0, "meter")) == "5.0 meter"

    def test_str_compound(self, Q):
        q = Q(10.0, "meter") / Q(1.0, "second")
        s = str(q)
        assert "meter" in s
        assert "second" in s

    def test_str_dimensionless(self, Q):
        assert str(Q(42.0)) == "42.0"

    def test_repr(self, Q):
        q = Q(5.0, "meter")
        r = repr(q)
        assert "Quantity" in r
        assert "5.0" in r

    def test_str_power(self, Q):
        q = Q(5.0, "meter") ** 2
        s = str(q)
        assert "meter ** 2" in s


# ============================================================
# UnitMap operations
# ============================================================

class TestUnitMap:
    def test_create_empty(self):
        um = UnitMap({})
        assert len(um) == 0

    def test_create_with_units(self):
        um = UnitMap({"meter": 1, "second": -1})
        assert um["meter"] == 1
        assert um["second"] == -1

    def test_multiply(self):
        um1 = UnitMap({"meter": 1})
        um2 = UnitMap({"second": 1})
        result = um1 * um2
        assert result["meter"] == 1
        assert result["second"] == 1

    def test_divide(self):
        um1 = UnitMap({"meter": 1})
        um2 = UnitMap({"second": 1})
        result = um1 / um2
        assert result["meter"] == 1
        assert result["second"] == -1

    def test_power(self):
        um = UnitMap({"meter": 1})
        result = um ** 2
        assert result["meter"] == 2

    def test_cancellation(self):
        um1 = UnitMap({"meter": 1})
        um2 = UnitMap({"meter": 1})
        result = um1 / um2
        assert len(result) == 0

    def test_equality(self):
        assert UnitMap({"meter": 1}) == UnitMap({"meter": 1})

    def test_hash(self):
        um1 = UnitMap({"meter": 1})
        um2 = UnitMap({"meter": 1})
        assert hash(um1) == hash(um2)

    def test_zero_exponent_removed(self):
        um = UnitMap({"meter": 0, "second": 1})
        assert "meter" not in um
        assert len(um) == 1


# ============================================================
# Edge cases and special scenarios
# ============================================================

class TestEdgeCases:
    def test_add_zero_to_quantity(self, Q):
        q = Q(5.0, "meter")
        result = q + 0
        assert result.magnitude == 5.0

    def test_multiply_by_zero(self, Q):
        result = Q(5.0, "meter") * 0
        assert result.magnitude == 0.0

    def test_multiply_by_one(self, Q):
        q = Q(5.0, "meter")
        result = q * 1
        assert result.magnitude == 5.0

    def test_convert_to_same_unit(self, Q):
        q = Q(5.0, "meter")
        result = q.to("meter")
        assert result.magnitude == 5.0

    def test_negative_magnitude(self, Q):
        q = Q(-5.0, "meter")
        assert q.magnitude == -5.0

    def test_chain_operations(self, Q):
        q = Q(10.0, "meter") / Q(2.0, "second") * Q(3.0, "second")
        assert abs(q.magnitude - 15.0) < 1e-10
        assert q.unit_map == UnitMap({"meter": 1})

    def test_conversion_roundtrip(self, Q):
        q1 = Q(100.0, "centimeter")
        q2 = q1.to("meter")
        q3 = q2.to("millimeter")
        q4 = q3.to("centimeter")
        assert abs(q4.magnitude - 100.0) < 1e-8

    def test_quantity_copy_independence(self, Q):
        q1 = Q(5.0, "meter")
        q2 = Q(q1)
        assert q1 == q2
        # They should be equal but modifying one shouldn't affect other
        q3 = q2 * 2
        assert q3.magnitude == 10.0
        assert q1.magnitude == 5.0
