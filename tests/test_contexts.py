"""Tests for context-dependent conversions (Task 9)."""

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
# Context loading
# ---------------------------------------------------------------------------

class TestContextLoading:
    def test_spectroscopy_context_exists(self, ureg):
        assert "spectroscopy" in ureg._contexts

    def test_spectroscopy_alias_exists(self, ureg):
        assert "sp" in ureg._contexts

    def test_boltzmann_context_exists(self, ureg):
        assert "boltzmann" in ureg._contexts

    def test_energy_context_exists(self, ureg):
        assert "energy" in ureg._contexts

    def test_spectroscopy_has_defaults(self, ureg):
        ctx = ureg._contexts["spectroscopy"]
        assert "n" in ctx.defaults
        assert ctx.defaults["n"] == 1


# ---------------------------------------------------------------------------
# Spectroscopy context: length <-> frequency
# ---------------------------------------------------------------------------

class TestSpectroscopyContext:
    def test_wavelength_to_frequency(self, ureg, Q):
        with ureg.context("spectroscopy"):
            wavelength = Q(500e-9, "meter")
            freq = wavelength.to("hertz")
            expected = 299792458 / 500e-9
            assert abs(freq.magnitude - expected) / expected < 1e-6

    def test_frequency_to_wavelength(self, ureg, Q):
        with ureg.context("spectroscopy"):
            freq = Q(6e14, "hertz")
            wavelength = freq.to("meter")
            expected = 299792458 / 6e14
            assert abs(wavelength.magnitude - expected) / expected < 1e-6

    def test_without_context_raises(self, ureg, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(500e-9, "meter").to("hertz")

    def test_alias_works(self, ureg, Q):
        with ureg.context("sp"):
            freq = Q(500e-9, "meter").to("hertz")
            assert freq.magnitude > 0

    def test_parameter_override(self, ureg, Q):
        with ureg.context("spectroscopy", n=2):
            freq_n2 = Q(500e-9, "meter").to("hertz")

        with ureg.context("spectroscopy", n=1):
            freq_n1 = Q(500e-9, "meter").to("hertz")

        assert abs(freq_n2.magnitude - freq_n1.magnitude / 2) / freq_n1.magnitude < 1e-6

    def test_frequency_to_energy(self, ureg, Q):
        with ureg.context("spectroscopy"):
            freq = Q(6e14, "hertz")
            energy = freq.to("joule")
            assert energy.magnitude > 0

    def test_energy_to_frequency(self, ureg, Q):
        with ureg.context("spectroscopy"):
            energy = Q(4e-19, "joule")
            freq = energy.to("hertz")
            assert freq.magnitude > 0


# ---------------------------------------------------------------------------
# Boltzmann context: temperature <-> energy
# ---------------------------------------------------------------------------

class TestBoltzmannContext:
    def test_temperature_to_energy(self, ureg, Q):
        with ureg.context("boltzmann"):
            temp = Q(300, "kelvin")
            energy = temp.to("joule")
            assert abs(energy.magnitude - 300 * 1.380649e-23) / (300 * 1.380649e-23) < 1e-6

    def test_energy_to_temperature(self, ureg, Q):
        with ureg.context("boltzmann"):
            energy = Q(4.14e-21, "joule")
            temp = energy.to("kelvin")
            assert temp.magnitude > 0

    def test_without_context_raises(self, ureg, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(300, "kelvin").to("joule")


# ---------------------------------------------------------------------------
# Energy context: mass <-> energy (E=mc²)
# ---------------------------------------------------------------------------

class TestEnergyContext:
    def test_mass_to_energy(self, ureg, Q):
        with ureg.context("energy"):
            mass = Q(1, "kilogram")
            energy = mass.to("joule")
            c = 299792458
            expected = c ** 2
            assert abs(energy.magnitude - expected) / expected < 1e-6

    def test_energy_to_mass(self, ureg, Q):
        with ureg.context("energy"):
            energy = Q(9e16, "joule")
            mass = energy.to("kilogram")
            assert mass.magnitude > 0

    def test_without_context_raises(self, ureg, Q):
        with pytest.raises(IncompatibleDimensionError):
            Q(1, "kilogram").to("joule")


# ---------------------------------------------------------------------------
# Context manager behavior
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_exits_cleanly(self, ureg, Q):
        with ureg.context("spectroscopy"):
            Q(500e-9, "meter").to("hertz")

        with pytest.raises(IncompatibleDimensionError):
            Q(500e-9, "meter").to("hertz")

    def test_nested_contexts(self, ureg, Q):
        with ureg.context("spectroscopy"):
            with ureg.context("boltzmann"):
                temp = Q(300, "kelvin")
                energy = temp.to("joule")
                assert energy.magnitude > 0

                wavelength = Q(500e-9, "meter")
                freq = wavelength.to("hertz")
                assert freq.magnitude > 0

    def test_context_does_not_affect_compatible_conversions(self, ureg, Q):
        with ureg.context("spectroscopy"):
            km = Q(1, "kilometer").to("meter")
            assert abs(km.magnitude - 1000) < 1e-9

    def test_unknown_context_raises(self, ureg):
        with pytest.raises(KeyError):
            with ureg.context("nonexistent"):
                pass

    def test_bidirectional_both_directions(self, ureg, Q):
        with ureg.context("spectroscopy"):
            wavelength = Q(500e-9, "meter")
            freq = wavelength.to("hertz")
            wavelength_back = freq.to("meter")
            assert abs(wavelength_back.magnitude - 500e-9) / 500e-9 < 1e-6

    def test_unidirectional_forward_works(self, ureg, Q):
        with ureg.context("spectroscopy"):
            freq = Q(6e14, "hertz")
            energy = freq.to("joule")
            assert energy.magnitude > 0

    def test_context_with_prefixed_units(self, ureg, Q):
        with ureg.context("spectroscopy"):
            wavelength = Q(500, "nanometer")
            freq = wavelength.to("hertz")
            expected = 299792458 / 500e-9
            assert abs(freq.magnitude - expected) / expected < 1e-3
