"""Tests for unit systems and grouping features (Task 8)."""

import pytest
from pint import UnitRegistry, Group, System


@pytest.fixture
def ureg():
    return UnitRegistry()


# ---------------------------------------------------------------------------
# Group basics
# ---------------------------------------------------------------------------

class TestGroupDefinition:
    def test_imperial_group_exists(self, ureg):
        grp = ureg.get_group("imperial")
        assert grp is not None

    def test_metric_group_exists(self, ureg):
        grp = ureg.get_group("metric")
        assert grp is not None

    def test_us_group_exists(self, ureg):
        grp = ureg.get_group("US")
        assert grp is not None

    def test_nonexistent_group_returns_none(self, ureg):
        assert ureg.get_group("nonexistent") is None

    def test_group_name(self, ureg):
        grp = ureg.get_group("imperial")
        assert grp.name == "imperial"


class TestGroupMembers:
    def test_imperial_contains_inch(self, ureg):
        grp = ureg.get_group("imperial")
        assert "inch" in grp.members

    def test_imperial_contains_pound(self, ureg):
        grp = ureg.get_group("imperial")
        assert "pound" in grp.members

    def test_imperial_contains_yard(self, ureg):
        grp = ureg.get_group("imperial")
        assert "yard" in grp.members

    def test_metric_contains_meter(self, ureg):
        grp = ureg.get_group("metric")
        assert "meter" in grp.members

    def test_metric_contains_gram(self, ureg):
        grp = ureg.get_group("metric")
        assert "gram" in grp.members

    def test_metric_excludes_inch(self, ureg):
        grp = ureg.get_group("metric")
        assert "inch" not in grp.members

    def test_members_returns_frozenset(self, ureg):
        grp = ureg.get_group("imperial")
        assert isinstance(grp.members, frozenset)

    def test_contains_check(self, ureg):
        grp = ureg.get_group("imperial")
        assert "inch" in grp
        assert "meter" not in grp


class TestGroupUsing:
    def test_us_includes_imperial_units(self, ureg):
        us = ureg.get_group("US")
        assert "inch" in us.members
        assert "foot" in us.members
        assert "yard" in us.members

    def test_us_has_own_units(self, ureg):
        us = ureg.get_group("US")
        assert "gallon" in us.members
        assert "short_ton" in us.members

    def test_us_members_superset_of_own_plus_imperial(self, ureg):
        us = ureg.get_group("US")
        imperial = ureg.get_group("imperial")
        assert imperial.members.issubset(us.members)


# ---------------------------------------------------------------------------
# System basics
# ---------------------------------------------------------------------------

class TestSystemDefinition:
    def test_si_system_exists(self, ureg):
        sys = ureg.get_system("SI")
        assert sys is not None

    def test_cgs_system_exists(self, ureg):
        sys = ureg.get_system("cgs")
        assert sys is not None

    def test_mks_system_exists(self, ureg):
        sys = ureg.get_system("mks")
        assert sys is not None

    def test_imperial_system_exists(self, ureg):
        sys = ureg.get_system("imperial")
        assert sys is not None

    def test_nonexistent_system_returns_none(self, ureg):
        assert ureg.get_system("nonexistent") is None

    def test_system_name(self, ureg):
        sys = ureg.get_system("SI")
        assert sys.name == "SI"


class TestSystemBaseUnits:
    def test_si_base_units(self, ureg):
        si = ureg.get_system("SI")
        assert "meter" in si.base_units
        assert "kilogram" in si.base_units
        assert "second" in si.base_units

    def test_cgs_base_units(self, ureg):
        cgs = ureg.get_system("cgs")
        assert "centimeter" in cgs.base_units
        assert "gram" in cgs.base_units
        assert "second" in cgs.base_units

    def test_mks_base_units(self, ureg):
        mks = ureg.get_system("mks")
        assert "meter" in mks.base_units
        assert "kilogram" in mks.base_units
        assert "second" in mks.base_units


# ---------------------------------------------------------------------------
# sys accessor
# ---------------------------------------------------------------------------

class TestSysAccessor:
    def test_access_si(self, ureg):
        si = ureg.sys.SI
        assert si.name == "SI"

    def test_access_cgs(self, ureg):
        cgs = ureg.sys.cgs
        assert cgs.name == "cgs"

    def test_access_nonexistent_raises(self, ureg):
        with pytest.raises(AttributeError):
            ureg.sys.nonexistent

    def test_dir_lists_systems(self, ureg):
        systems = dir(ureg.sys)
        assert "SI" in systems
        assert "cgs" in systems
        assert "mks" in systems


# ---------------------------------------------------------------------------
# get_compatible_units with group filter
# ---------------------------------------------------------------------------

class TestCompatibleUnitsWithGroup:
    def test_filter_by_imperial_group(self, ureg):
        units = ureg.get_compatible_units("[length]", group="imperial")
        assert "inch" in units
        assert "foot" in units
        assert "yard" in units
        assert "mile" in units

    def test_filter_excludes_non_group_units(self, ureg):
        units = ureg.get_compatible_units("[length]", group="imperial")
        assert "meter" not in units
        assert "kilometer" not in units

    def test_filter_by_metric_group(self, ureg):
        units = ureg.get_compatible_units("[length]", group="metric")
        assert "meter" in units
        assert "inch" not in units

    def test_filter_by_mass(self, ureg):
        units = ureg.get_compatible_units("[mass]", group="imperial")
        assert "pound" in units
        assert "ounce" in units
        assert "gram" not in units

    def test_no_filter_returns_all(self, ureg):
        all_units = ureg.get_compatible_units("[length]")
        filtered = ureg.get_compatible_units("[length]", group="imperial")
        assert len(all_units) > len(filtered)


# ---------------------------------------------------------------------------
# get_base_units with system
# ---------------------------------------------------------------------------

class TestGetBaseUnitsWithSystem:
    def test_cgs_converts_length(self, ureg):
        scale, bu = ureg.get_base_units("meter", system="cgs")
        assert "centimeter" in bu._data
        assert abs(scale - 100.0) < 1e-9

    def test_cgs_converts_mass(self, ureg):
        scale, bu = ureg.get_base_units("kilogram", system="cgs")
        assert "gram" in bu._data
        assert abs(scale - 1000.0) < 1e-9

    def test_cgs_compound_units(self, ureg):
        scale, bu = ureg.get_base_units("newton", system="cgs")
        assert "centimeter" in bu._data
        assert "gram" in bu._data
        assert "second" in bu._data

    def test_imperial_converts_length(self, ureg):
        scale, bu = ureg.get_base_units("meter", system="imperial")
        assert "yard" in bu._data

    def test_default_returns_si_base(self, ureg):
        scale, bu = ureg.get_base_units("kilometer")
        assert "meter" in bu._data
        assert abs(scale - 1000.0) < 1e-9

    def test_si_system_no_change(self, ureg):
        scale, bu = ureg.get_base_units("meter", system="SI")
        assert "meter" in bu._data
        assert abs(scale - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Group repr
# ---------------------------------------------------------------------------

class TestGroupRepr:
    def test_group_repr(self, ureg):
        grp = ureg.get_group("imperial")
        assert "imperial" in repr(grp)

    def test_system_repr(self, ureg):
        sys = ureg.get_system("SI")
        assert "SI" in repr(sys)
