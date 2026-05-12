"""Tests for the Measurement class with uncertainty propagation."""

import math
import pytest
from pint import UnitRegistry, Measurement


@pytest.fixture(scope="module")
def ureg():
    return UnitRegistry()


@pytest.fixture
def Q(ureg):
    return ureg.Quantity


@pytest.fixture
def M(ureg):
    return ureg.Measurement


# ============================================================
# Measurement creation
# ============================================================

class TestMeasurementCreation:
    def test_create_with_scalars_and_units(self, M):
        m = M(4.0, 0.1, "second")
        assert m.value.magnitude == 4.0
        assert m.error.magnitude == 0.1

    def test_create_from_quantities(self, Q):
        m = Measurement(Q(10, "meter"), Q(0.5, "meter"))
        assert m.value.magnitude == 10
        assert m.error.magnitude == 0.5

    def test_create_with_zero_error(self, M):
        m = M(5.0, 0, "meter")
        assert m.error.magnitude == 0

    def test_error_is_absolute(self, M):
        m = M(5.0, -0.1, "meter")
        assert m.error.magnitude == 0.1

    def test_value_property(self, M, Q):
        m = M(4.0, 0.1, "second")
        assert isinstance(m.value, type(Q(1)))

    def test_error_property(self, M, Q):
        m = M(4.0, 0.1, "second")
        assert isinstance(m.error, type(Q(1)))

    def test_magnitude_property(self, M):
        m = M(4.0, 0.1, "second")
        assert m.magnitude == 4.0

    def test_units_property(self, M):
        m = M(4.0, 0.1, "second")
        assert "second" in str(m.units)


# ============================================================
# Relative error
# ============================================================

class TestRelativeError:
    def test_relative_error(self, M):
        m = M(100.0, 5.0, "meter")
        assert abs(m.rel - 0.05) < 1e-10

    def test_relative_error_zero_value(self, M):
        m = M(0.0, 1.0, "meter")
        assert m.rel == float("inf")

    def test_relative_error_zero_both(self, M):
        m = M(0.0, 0.0, "meter")
        assert m.rel == 0.0

    def test_relative_error_small(self, M):
        m = M(1000.0, 0.1, "meter")
        assert abs(m.rel - 0.0001) < 1e-10


# ============================================================
# Measurement arithmetic — addition/subtraction
# ============================================================

class TestMeasurementAddSub:
    def test_add_same_units(self, M):
        m1 = M(3.0, 0.1, "meter")
        m2 = M(4.0, 0.2, "meter")
        result = m1 + m2
        assert abs(result.value.magnitude - 7.0) < 1e-10
        expected_err = math.sqrt(0.1 ** 2 + 0.2 ** 2)
        assert abs(result.error.magnitude - expected_err) < 1e-10

    def test_subtract_same_units(self, M):
        m1 = M(10.0, 0.3, "meter")
        m2 = M(4.0, 0.1, "meter")
        result = m1 - m2
        assert abs(result.value.magnitude - 6.0) < 1e-10
        expected_err = math.sqrt(0.3 ** 2 + 0.1 ** 2)
        assert abs(result.error.magnitude - expected_err) < 1e-10

    def test_add_zero_error(self, M):
        m1 = M(3.0, 0.1, "meter")
        m2 = M(2.0, 0.0, "meter")
        result = m1 + m2
        assert abs(result.value.magnitude - 5.0) < 1e-10
        assert abs(result.error.magnitude - 0.1) < 1e-10


# ============================================================
# Measurement arithmetic — multiplication/division
# ============================================================

class TestMeasurementMulDiv:
    def test_multiply_measurements(self, M):
        m1 = M(5.0, 0.1, "meter")
        m2 = M(2.0, 0.05, "second")
        result = m1 * m2
        assert abs(result.value.magnitude - 10.0) < 1e-10
        rel_err = math.sqrt((0.1 / 5.0) ** 2 + (0.05 / 2.0) ** 2)
        expected_err = 10.0 * rel_err
        assert abs(result.error.magnitude - expected_err) < 1e-8

    def test_divide_measurements(self, M):
        m1 = M(10.0, 0.2, "meter")
        m2 = M(2.0, 0.05, "second")
        result = m1 / m2
        assert abs(result.value.magnitude - 5.0) < 1e-10
        rel_err = math.sqrt((0.2 / 10.0) ** 2 + (0.05 / 2.0) ** 2)
        expected_err = 5.0 * rel_err
        assert abs(result.error.magnitude - expected_err) < 1e-8

    def test_multiply_by_scalar(self, M):
        m = M(3.0, 0.1, "meter")
        result = m * 2
        assert abs(result.value.magnitude - 6.0) < 1e-10
        assert abs(result.error.magnitude - 0.2) < 1e-10

    def test_scalar_multiply(self, M):
        m = M(3.0, 0.1, "meter")
        result = 2 * m
        assert abs(result.value.magnitude - 6.0) < 1e-10
        assert abs(result.error.magnitude - 0.2) < 1e-10

    def test_divide_by_scalar(self, M):
        m = M(6.0, 0.2, "meter")
        result = m / 2
        assert abs(result.value.magnitude - 3.0) < 1e-10
        assert abs(result.error.magnitude - 0.1) < 1e-10

    def test_power(self, M):
        m = M(3.0, 0.1, "meter")
        result = m ** 2
        assert abs(result.value.magnitude - 9.0) < 1e-10
        rel_err = 2 * 0.1 / 3.0
        expected_err = 9.0 * rel_err
        assert abs(result.error.magnitude - expected_err) < 1e-8


# ============================================================
# Unit conversion with uncertainty
# ============================================================

class TestMeasurementConversion:
    def test_convert_length(self, M):
        m = M(1.0, 0.01, "kilometer")
        result = m.to("meter")
        assert abs(result.value.magnitude - 1000.0) < 1e-10
        assert abs(result.error.magnitude - 10.0) < 1e-10

    def test_convert_preserves_relative_error(self, M):
        m = M(100.0, 5.0, "centimeter")
        result = m.to("meter")
        assert abs(result.value.magnitude - 1.0) < 1e-10
        assert abs(result.rel - m.rel) < 1e-10

    def test_convert_time(self, M):
        m = M(1.0, 0.1, "hour")
        result = m.to("minute")
        assert abs(result.value.magnitude - 60.0) < 1e-10
        assert abs(result.error.magnitude - 6.0) < 1e-10


# ============================================================
# String representation
# ============================================================

class TestMeasurementString:
    def test_str_format(self, M):
        m = M(4.0, 0.1, "second")
        s = str(m)
        assert "+/-" in s
        assert "4.0" in s
        assert "0.1" in s
        assert "second" in s

    def test_repr(self, M):
        m = M(4.0, 0.1, "second")
        r = repr(m)
        assert "Measurement" in r

    def test_format_with_precision(self, M):
        m = M(3.14159, 0.001, "meter")
        result = format(m, ".2fD")
        assert "3.14" in result
        assert "0.00" in result

    def test_str_dimensionless(self, M):
        m = M(42.0, 1.0)
        s = str(m)
        assert "42.0" in s
        assert "+/-" in s


# ============================================================
# Edge cases
# ============================================================

class TestMeasurementEdgeCases:
    def test_negate(self, M):
        m = M(5.0, 0.1, "meter")
        result = -m
        assert result.value.magnitude == -5.0
        assert result.error.magnitude == 0.1

    def test_equality(self, M):
        m1 = M(5.0, 0.1, "meter")
        m2 = M(5.0, 0.1, "meter")
        assert m1 == m2

    def test_inequality_magnitude(self, M):
        m1 = M(5.0, 0.1, "meter")
        m2 = M(6.0, 0.1, "meter")
        assert m1 != m2

    def test_inequality_error(self, M):
        m1 = M(5.0, 0.1, "meter")
        m2 = M(5.0, 0.2, "meter")
        assert m1 != m2

    def test_multiply_preserves_units(self, M):
        m = M(3.0, 0.1, "meter")
        result = m * M(2.0, 0.05, "second")
        dim = result.value.dimensionality
        assert dim["[length]"] == 1
        assert dim["[time]"] == 1

    def test_divide_produces_correct_units(self, M):
        m1 = M(10.0, 0.2, "meter")
        m2 = M(2.0, 0.05, "second")
        result = m1 / m2
        dim = result.value.dimensionality
        assert dim["[length]"] == 1
        assert dim["[time]"] == -1
