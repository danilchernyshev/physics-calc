"""Tests for the chemistry engine: element data, molar mass and balancing."""

import pytest

from study_calc.core import periodic as P


def test_element_lookup_and_dataset_size():
    assert len(P.elements()) == 118
    h = P.element("H")
    assert h.number == 1 and h.name == "Hydrogen"
    assert P.element("Og").number == 118
    with pytest.raises(P.ChemError) as exc:
        P.element("Xx")
    assert exc.value.code == "chem_unknown_element"


def test_composition_handles_counts_and_nested_parentheses():
    assert P.composition("H2O") == {"H": 2, "O": 1}
    assert P.composition("CH3COOH") == {"C": 2, "H": 4, "O": 2}
    assert P.composition("Al2(SO4)3") == {"Al": 2, "S": 3, "O": 12}
    assert P.composition("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}


def test_molar_mass_matches_known_values():
    # Standard atomic weights (IUPAC) summed; rounded to the textbook figures.
    assert P.molar_mass("H2O") == pytest.approx(18.015, abs=1e-3)
    assert P.molar_mass("CO2") == pytest.approx(44.009, abs=1e-3)
    assert P.molar_mass("NaCl") == pytest.approx(58.44, abs=1e-2)
    assert P.molar_mass("C6H12O6") == pytest.approx(180.156, abs=1e-2)
    assert P.molar_mass("Ca(OH)2") == pytest.approx(74.09, abs=1e-2)


@pytest.mark.parametrize("bad,code", [
    ("", "chem_empty"),
    ("Xx2O", "chem_unknown_element"),
    ("(H2O", "chem_parse"),
    ("H2O)", "chem_parse"),
    ("123", "chem_parse"),
])
def test_molar_mass_error_codes(bad, code):
    with pytest.raises(P.ChemError) as exc:
        P.molar_mass(bad)
    assert exc.value.code == code


def test_balance_simple_and_combustion():
    assert P.balance("H2 + O2 -> H2O") == "2H2 + O2 -> 2H2O"
    assert P.balance("CH4 + O2 -> CO2 + H2O") == "CH4 + 2O2 -> CO2 + 2H2O"
    assert P.balance("C3H8 + O2 -> CO2 + H2O") == "C3H8 + 5O2 -> 3CO2 + 4H2O"
    assert P.balance("Fe + O2 -> Fe2O3") == "4Fe + 3O2 -> 2Fe2O3"


def test_balance_accepts_alternate_arrows():
    assert P.balance("H2 + O2 = H2O") == "2H2 + O2 -> 2H2O"
    assert P.balance("H2 + O2 → H2O") == "2H2 + O2 -> 2H2O"


def test_balance_redox_with_many_species():
    assert (P.balance("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2")
            == "2KMnO4 + 16HCl -> 2KCl + 2MnCl2 + 8H2O + 5Cl2")


@pytest.mark.parametrize("bad,code", [
    ("H2 + O2", "chem_no_arrow"),
    ("H2 -> H2 + O2", "chem_unbalanceable"),
    ("Xx -> Yy", "chem_unknown_element"),
])
def test_balance_error_codes(bad, code):
    with pytest.raises(P.ChemError) as exc:
        P.balance(bad)
    assert exc.value.code == code
