"""Tests for quantity and unit formatting in multiple output styles."""

import pytest
from pint import UnitRegistry, Unit


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
# Default format (D)
# ============================================================

class TestDefaultFormat:
    def test_simple_unit(self, Q):
        assert format(Q(5.0, "meter"), "D") == "5.0 meter"

    def test_compound_ratio(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "D")
        assert "meter" in result
        assert "second ** 2" in result
        assert "/" in result

    def test_product_units(self, Q):
        q = Q(1.0, "kilogram * meter")
        result = format(q, "D")
        assert "kilogram" in result
        assert "meter" in result
        assert "*" in result

    def test_squared_unit(self, Q):
        result = format(Q(10.0, "meter ** 2"), "D")
        assert "meter ** 2" in result

    def test_exponent_one_not_shown(self, Q):
        result = format(Q(5.0, "meter"), "D")
        assert "** 1" not in result
        assert result == "5.0 meter"

    def test_dimensionless(self, Q):
        result = format(Q(42.0), "D")
        assert result == "42.0"


# ============================================================
# Compact format (C)
# ============================================================

class TestCompactFormat:
    def test_simple_unit(self, Q):
        assert format(Q(5.0, "meter"), "C") == "5.0 meter"

    def test_compound_no_spaces(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "C")
        assert "meter/second**2" in result

    def test_product_no_spaces(self, Q):
        q = Q(1.0, "kilogram * meter")
        result = format(q, "C")
        assert "kilogram*meter" in result or "meter*kilogram" in result


# ============================================================
# Pretty format (P)
# ============================================================

class TestPrettyFormat:
    def test_superscript_exponent(self, Q):
        q = Q(10.0, "meter ** 2")
        result = format(q, "P")
        assert "meter²" in result

    def test_cubed_superscript(self, Q):
        q = Q(10.0, "meter ** 3")
        result = format(q, "P")
        assert "meter³" in result

    def test_negative_exponent_superscript(self, Q):
        q = Q(5.0, "second ** -1")
        result = format(q, "P")
        assert "second" in result

    def test_compound_with_dot(self, Q):
        q = Q(1.0, "kilogram * meter ** 2")
        result = format(q, "^P")
        assert "·" in result

    def test_ratio_format(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "P")
        assert "second²" in result


# ============================================================
# LaTeX format (L)
# ============================================================

class TestLatexFormat:
    def test_simple_mathrm(self, Q):
        q = Q(5.0, "meter")
        result = format(q, "L")
        assert "\\mathrm{meter}" in result

    def test_fraction(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "L")
        assert "\\frac{" in result
        assert "\\mathrm{meter}" in result
        assert "\\mathrm{second}" in result

    def test_power_notation(self, Q):
        q = Q(10.0, "meter ** 2")
        result = format(q, "L")
        assert "\\mathrm{meter}^{2}" in result

    def test_cdot_for_product(self, Q):
        q = Q(1.0, "kilogram * meter")
        result = format(q, "^L")
        assert "\\cdot" in result

    def test_backslash_space(self, Q):
        q = Q(5.0, "meter")
        result = format(q, "L")
        assert "\\ " in result

    def test_dimensionless_latex(self, Q):
        result = format(Q(42.0), "L")
        assert result == "42.0"


# ============================================================
# HTML format (H)
# ============================================================

class TestHtmlFormat:
    def test_superscript_tag(self, Q):
        q = Q(10.0, "meter ** 2")
        result = format(q, "H")
        assert "<sup>2</sup>" in result
        assert "meter" in result

    def test_compound_html(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "H")
        assert "second<sup>2</sup>" in result
        assert "/" in result

    def test_simple_no_sup(self, Q):
        q = Q(5.0, "meter")
        result = format(q, "H")
        assert "<sup>" not in result
        assert "meter" in result

    def test_dimensionless_html(self, Q):
        result = format(Q(42.0), "H")
        assert result == "42.0"


# ============================================================
# Abbreviated format (~)
# ============================================================

class TestAbbreviatedFormat:
    def test_meter_symbol(self, Q):
        q = Q(5.0, "meter")
        result = format(q, "~D")
        assert result == "5.0 m"

    def test_second_symbol(self, Q):
        q = Q(3.0, "second")
        result = format(q, "~D")
        assert result == "3.0 s"

    def test_kilogram_symbol(self, Q):
        q = Q(2.0, "kilogram")
        result = format(q, "~D")
        assert result == "2.0 kg"

    def test_newton_symbol(self, Q):
        q = Q(1.0, "newton")
        result = format(q, "~D")
        assert result == "1.0 N"

    def test_joule_symbol(self, Q):
        q = Q(1.0, "joule")
        result = format(q, "~D")
        assert result == "1.0 J"

    def test_watt_symbol(self, Q):
        q = Q(1.0, "watt")
        result = format(q, "~D")
        assert result == "1.0 W"

    def test_pascal_symbol(self, Q):
        q = Q(1.0, "pascal")
        result = format(q, "~D")
        assert result == "1.0 Pa"

    def test_hertz_symbol(self, Q):
        q = Q(1.0, "hertz")
        result = format(q, "~D")
        assert result == "1.0 Hz"

    def test_volt_symbol(self, Q):
        q = Q(1.0, "volt")
        result = format(q, "~D")
        assert result == "1.0 V"

    def test_prefixed_symbol(self, Q):
        q = Q(1.0, "kilometer")
        result = format(q, "~D")
        assert result == "1.0 km"

    def test_milligram_symbol(self, Q):
        q = Q(1.0, "milligram")
        result = format(q, "~D")
        assert result == "1.0 mg"

    def test_compound_abbreviated(self, Q):
        q = Q(9.81, "meter / second ** 2")
        result = format(q, "~D")
        assert "m" in result
        assert "s" in result

    def test_abbreviated_pretty(self, Q):
        q = Q(10.0, "meter ** 2")
        result = format(q, "~P")
        assert "m²" in result

    def test_abbreviated_latex(self, Q):
        q = Q(5.0, "meter")
        result = format(q, "~L")
        assert "\\mathrm{m}" in result


# ============================================================
# Combined magnitude + unit format
# ============================================================

class TestCombinedFormat:
    def test_float_precision(self, Q):
        q = Q(3.14159, "meter")
        result = format(q, ".2fD")
        assert result == "3.14 meter"

    def test_four_decimals(self, Q):
        q = Q(3.14159, "meter")
        result = format(q, ".4fD")
        assert result == "3.1416 meter"

    def test_scientific_notation(self, Q):
        q = Q(12345.6, "meter")
        result = format(q, "eD")
        assert "e" in result
        assert "meter" in result

    def test_precision_with_abbreviation(self, Q):
        q = Q(3.14159, "meter")
        result = format(q, ".1f~D")
        assert result == "3.1 m"

    def test_precision_with_pretty(self, Q):
        q = Q(3.14159, "meter ** 2")
        result = format(q, ".2fP")
        assert "3.14" in result
        assert "meter²" in result


# ============================================================
# Unit formatting (without magnitude)
# ============================================================

class TestUnitFormatting:
    def test_unit_default(self, U):
        u = U("meter / second")
        result = format(u, "D")
        assert result == "meter / second"

    def test_unit_compact(self, U):
        u = U("meter / second")
        result = format(u, "C")
        assert result == "meter/second"

    def test_unit_pretty(self, U):
        u = U("meter ** 2")
        result = format(u, "P")
        assert "meter²" in result

    def test_unit_latex(self, U):
        u = U("meter")
        result = format(u, "L")
        assert result == "\\mathrm{meter}"

    def test_unit_html(self, U):
        u = U("meter ** 2")
        result = format(u, "H")
        assert "meter<sup>2</sup>" in result

    def test_unit_abbreviated(self, U):
        u = U("meter")
        result = format(u, "~D")
        assert result == "m"

    def test_unit_str_default(self, U):
        u = U("meter")
        assert str(u) == "meter"

    def test_unit_compound_str(self, U):
        u = U("meter / second")
        result = str(u)
        assert "meter" in result
        assert "second" in result


# ============================================================
# Edge cases
# ============================================================

class TestFormattingEdgeCases:
    def test_empty_format(self, Q):
        q = Q(5.0, "meter")
        assert format(q, "") == str(q)

    def test_dimensionless_formats(self, Q):
        q = Q(42.0)
        for spec in ["D", "C", "P", "L", "H"]:
            result = format(q, spec)
            assert "42.0" in result

    def test_zero_magnitude(self, Q):
        q = Q(0.0, "meter")
        result = format(q, "D")
        assert "0.0" in result
        assert "meter" in result

    def test_negative_magnitude(self, Q):
        q = Q(-5.0, "meter")
        result = format(q, "D")
        assert "-5.0" in result
        assert "meter" in result

    def test_unit_dimensionless(self, U):
        u = U("radian")
        result = format(u, "D")
        assert "radian" in result
