"""Tests for temperature and offset unit handling."""

import math
import pytest
from pint import UnitRegistry
from pint.errors import IncompatibleDimensionError


@pytest.fixture(scope="module")
def ureg():
    return UnitRegistry()


@pytest.fixture
def Q(ureg):
    return ureg.Quantity


# ============================================================
# Celsius to Kelvin
# ============================================================

class TestCelsiusKelvin:
    def test_0C_to_K(self, Q):
        result = Q(0, "degree_Celsius").to("kelvin")
        assert abs(result.magnitude - 273.15) < 0.01

    def test_100C_to_K(self, Q):
        result = Q(100, "degree_Celsius").to("kelvin")
        assert abs(result.magnitude - 373.15) < 0.01

    def test_minus40C_to_K(self, Q):
        result = Q(-40, "degree_Celsius").to("kelvin")
        assert abs(result.magnitude - 233.15) < 0.01

    def test_0K_to_C(self, Q):
        result = Q(0, "kelvin").to("degree_Celsius")
        assert abs(result.magnitude - (-273.15)) < 0.01

    def test_373K_to_C(self, Q):
        result = Q(373.15, "kelvin").to("degree_Celsius")
        assert abs(result.magnitude - 100.0) < 0.01

    def test_roundtrip_C_K_C(self, Q):
        original = 37.5
        result = Q(original, "degree_Celsius").to("kelvin").to("degree_Celsius")
        assert abs(result.magnitude - original) < 1e-10

    def test_degC_alias(self, Q):
        result = Q(100, "degC").to("kelvin")
        assert abs(result.magnitude - 373.15) < 0.01

    def test_celsius_alias(self, Q):
        result = Q(0, "celsius").to("kelvin")
        assert abs(result.magnitude - 273.15) < 0.01


# ============================================================
# Fahrenheit to Kelvin
# ============================================================

class TestFahrenheitKelvin:
    def test_32F_to_K(self, Q):
        result = Q(32, "degree_Fahrenheit").to("kelvin")
        assert abs(result.magnitude - 273.15) < 0.01

    def test_212F_to_K(self, Q):
        result = Q(212, "degree_Fahrenheit").to("kelvin")
        assert abs(result.magnitude - 373.15) < 0.01

    def test_0F_to_K(self, Q):
        result = Q(0, "degree_Fahrenheit").to("kelvin")
        assert abs(result.magnitude - 255.372) < 0.01

    def test_minus40F_to_K(self, Q):
        result = Q(-40, "degree_Fahrenheit").to("kelvin")
        assert abs(result.magnitude - 233.15) < 0.01

    def test_K_to_F(self, Q):
        result = Q(273.15, "kelvin").to("degree_Fahrenheit")
        assert abs(result.magnitude - 32.0) < 0.01

    def test_roundtrip_F_K_F(self, Q):
        original = 72.0
        result = Q(original, "degree_Fahrenheit").to("kelvin").to("degree_Fahrenheit")
        assert abs(result.magnitude - original) < 1e-8

    def test_degF_alias(self, Q):
        result = Q(212, "degF").to("kelvin")
        assert abs(result.magnitude - 373.15) < 0.01


# ============================================================
# Celsius to Fahrenheit
# ============================================================

class TestCelsiusFahrenheit:
    def test_100C_to_F(self, Q):
        result = Q(100, "degree_Celsius").to("degree_Fahrenheit")
        assert abs(result.magnitude - 212.0) < 0.01

    def test_0C_to_F(self, Q):
        result = Q(0, "degree_Celsius").to("degree_Fahrenheit")
        assert abs(result.magnitude - 32.0) < 0.01

    def test_minus40C_to_F(self, Q):
        result = Q(-40, "degree_Celsius").to("degree_Fahrenheit")
        assert abs(result.magnitude - (-40.0)) < 0.01

    def test_roundtrip_C_F_C(self, Q):
        original = 25.0
        result = Q(original, "degree_Celsius").to("degree_Fahrenheit").to("degree_Celsius")
        assert abs(result.magnitude - original) < 1e-8

    def test_37C_to_F(self, Q):
        result = Q(37, "degree_Celsius").to("degree_Fahrenheit")
        assert abs(result.magnitude - 98.6) < 0.1


# ============================================================
# Rankine
# ============================================================

class TestRankine:
    def test_0R_to_K(self, Q):
        result = Q(0, "degree_Rankine").to("kelvin")
        assert abs(result.magnitude) < 0.01

    def test_491R_to_K(self, Q):
        result = Q(491.67, "degree_Rankine").to("kelvin")
        assert abs(result.magnitude - 273.15) < 0.01

    def test_K_to_R(self, Q):
        result = Q(273.15, "kelvin").to("degree_Rankine")
        assert abs(result.magnitude - 491.67) < 0.01

    def test_roundtrip_R_K_R(self, Q):
        original = 500.0
        result = Q(original, "degree_Rankine").to("kelvin").to("degree_Rankine")
        assert abs(result.magnitude - original) < 1e-8


# ============================================================
# Delta (temperature difference) units
# ============================================================

class TestDeltaTemperature:
    def test_delta_celsius_exists(self, ureg):
        canon = ureg.get_canonical_name("delta_degree_Celsius")
        assert canon == "delta_degree_Celsius"

    def test_delta_fahrenheit_exists(self, ureg):
        canon = ureg.get_canonical_name("delta_degree_Fahrenheit")
        assert canon == "delta_degree_Fahrenheit"

    def test_delta_celsius_alias(self, ureg):
        canon = ureg.get_canonical_name("delta_degC")
        assert canon == "delta_degree_Celsius"

    def test_delta_fahrenheit_alias(self, ureg):
        canon = ureg.get_canonical_name("delta_degF")
        assert canon == "delta_degree_Fahrenheit"

    def test_1_delta_celsius_equals_1_kelvin(self, Q):
        q = Q(1, "delta_degree_Celsius")
        k = q.to("kelvin")
        assert abs(k.magnitude - 1.0) < 1e-10

    def test_1_delta_fahrenheit_to_kelvin(self, Q):
        q = Q(1, "delta_degree_Fahrenheit")
        k = q.to("kelvin")
        assert abs(k.magnitude - 5.0 / 9.0) < 1e-10

    def test_10_delta_celsius_to_kelvin(self, Q):
        q = Q(10, "delta_degree_Celsius")
        k = q.to("kelvin")
        assert abs(k.magnitude - 10.0) < 1e-10

    def test_delta_celsius_is_multiplicative(self, ureg):
        udef = ureg._units["delta_degree_Celsius"]
        assert udef.converter.is_multiplicative

    def test_delta_fahrenheit_is_multiplicative(self, ureg):
        udef = ureg._units["delta_degree_Fahrenheit"]
        assert udef.converter.is_multiplicative


# ============================================================
# Edge cases
# ============================================================

class TestTemperatureEdgeCases:
    def test_absolute_zero_C(self, Q):
        result = Q(-273.15, "degree_Celsius").to("kelvin")
        assert abs(result.magnitude) < 0.01

    def test_boiling_water_all_scales(self, Q):
        c = Q(100, "degree_Celsius")
        k = c.to("kelvin")
        f = c.to("degree_Fahrenheit")

        assert abs(k.magnitude - 373.15) < 0.01
        assert abs(f.magnitude - 212.0) < 0.01

    def test_freezing_water_all_scales(self, Q):
        c = Q(0, "degree_Celsius")
        k = c.to("kelvin")
        f = c.to("degree_Fahrenheit")

        assert abs(k.magnitude - 273.15) < 0.01
        assert abs(f.magnitude - 32.0) < 0.01

    def test_negative_fahrenheit(self, Q):
        q = Q(-40, "degree_Fahrenheit")
        c = q.to("degree_Celsius")
        assert abs(c.magnitude - (-40.0)) < 0.01

    def test_large_temperature(self, Q):
        q = Q(1e6, "kelvin")
        c = q.to("degree_Celsius")
        assert abs(c.magnitude - (1e6 - 273.15)) < 0.1
