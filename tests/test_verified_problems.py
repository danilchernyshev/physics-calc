"""Verified-problem regression suite: textbook problems with known answers.

Every test below pins a calculation to a worked result from an academically
trustworthy source — OpenStax (College Physics 2e, Calculus Vol. 1/2/3), the
NIST Guide to the SI / CODATA exact unit definitions, and standard physics
references. The point is not to re-test the engine plumbing (the other test
files already cover error codes and i18n) but to guarantee the *numbers the
calculator produces match an independently published answer*.

Each test's comment carries: the source, the given data, and the expected
answer. No network access — the reference values are inlined.
"""

import math

import pytest

from study_calc.core import cas
from study_calc.core import units
from study_calc.core import vectors as V
from study_calc.core.formula import SolveError
from study_calc.domains import SECTIONS


def _find(section: str, key: str):
    """Locate a formula by key inside a section (same helper as test_formulas)."""
    for formula in SECTIONS[section]:
        if formula.key == key:
            return formula
    raise AssertionError(f"formula {key} not found in section {section}")


# ===========================================================================
# Mechanics  — OpenStax, College Physics 2e
# ===========================================================================

def test_newtons_second_law():
    # OpenStax College Physics 2e §4.3 (Newton's second law). A net force on a
    # 1100 kg car producing 2.0 m/s²: F = m·a = 1100 · 2.0 = 2200 N.
    f = _find("mechanics", "newton_2")
    assert f.solve("F", {"m": 1100, "a": 2.0}) == pytest.approx(2200)
    # Solving back for the other variables must invert cleanly.
    assert f.solve("a", {"F": 2200, "m": 1100}) == pytest.approx(2.0)
    assert f.solve("m", {"F": 2200, "a": 2.0}) == pytest.approx(1100)


def test_kinetic_energy_of_a_pitched_baseball():
    # OpenStax College Physics 2e §7.2 (Kinetic Energy). A 0.145 kg baseball at
    # 40 m/s: KE = ½·m·v² = ½·0.145·40² = 116 J.
    f = _find("mechanics", "kinetic_energy")
    assert f.solve("E", {"m": 0.145, "v": 40}) == pytest.approx(116)
    # And recover the speed from the energy.
    assert f.solve("v", {"E": 116, "m": 0.145}) == pytest.approx(40)


def test_momentum_of_a_pitched_baseball():
    # OpenStax College Physics 2e §8.1 (Linear Momentum). p = m·v =
    # 0.145 kg · 40 m/s = 5.8 kg·m/s.
    f = _find("mechanics", "momentum")
    assert f.solve("p", {"m": 0.145, "v": 40}) == pytest.approx(5.8)


def test_work_done_by_a_constant_force():
    # OpenStax College Physics 2e §7.1 (Work). A 50 N force over 10 m along the
    # motion: W = F·s = 500 J.
    f = _find("mechanics", "work")
    assert f.solve("A", {"F": 50, "s": 10}) == pytest.approx(500)


def test_power_is_work_over_time():
    # OpenStax College Physics 2e §7.7 (Power). 1000 J delivered in 10 s →
    # P = 1000/10 = 100 W.
    f = _find("mechanics", "power")
    assert f.solve("P", {"A": 1000, "t": 10}) == pytest.approx(100)


def test_gravitational_potential_energy():
    # OpenStax College Physics 2e §7.3 (PEg). A 2 kg mass raised 10 m, g = 9.80
    # m/s²: PE = m·g·h = 2·9.80·10 = 196 J.
    f = _find("mechanics", "potential_energy")
    assert f.solve("E", {"m": 2, "g": 9.80, "h": 10}) == pytest.approx(196)


def test_kinematics_final_velocity():
    # OpenStax College Physics 2e §2.4 (Motion Equations, v = v₀ + a·t). From
    # rest at a = 2.0 m/s² for 5.0 s: v = 0 + 2.0·5.0 = 10 m/s.
    f = _find("mechanics", "velocity")
    assert f.solve("v", {"v0": 0, "a": 2.0, "t": 5.0}) == pytest.approx(10.0)
    # Invert for the time it takes to reach that speed.
    assert f.solve("t", {"v": 10.0, "v0": 0, "a": 2.0}) == pytest.approx(5.0)


# ===========================================================================
# Thermodynamics  — OpenStax, College Physics 2e
# ===========================================================================

def test_ideal_gas_molar_volume_at_stp():
    # Standard result (OpenStax College Physics 2e §13.3, Ideal Gas Law): one
    # mole at STP (T = 273.15 K, P = 101325 Pa) occupies 22.414 L = 0.022414 m³.
    f = _find("thermodynamics", "ideal_gas")
    v = f.solve("V", {"P": 101325, "n": 1, "T": 273.15})
    assert v == pytest.approx(0.022414, rel=1e-4)


def test_heat_to_warm_half_a_litre_of_water():
    # OpenStax College Physics 2e §14.2 (Heat). Water c = 4186 J/(kg·K).
    # Q = c·m·ΔT = 4186 · 0.5 kg · 20 K = 41860 J.
    f = _find("thermodynamics", "heat")
    assert f.solve("Q", {"c": 4186, "m": 0.5, "dT": 20}) == pytest.approx(41860)


def test_carnot_efficiency():
    # OpenStax College Physics 2e §15.4 (Carnot engine). η = 1 − Tc/Th. A heat
    # engine between 600 K and 300 K: η = 1 − 300/600 = 0.5 (50%).
    f = _find("thermodynamics", "carnot_efficiency")
    assert f.solve("eta", {"Tc": 300, "Th": 600}) == pytest.approx(0.5)


def test_linear_thermal_expansion_of_a_steel_rod():
    # OpenStax College Physics 2e §13.2 (Thermal Expansion). Steel
    # α = 12×10⁻⁶ /K, a 1 m rod heated 100 K: ΔL = α·L₀·ΔT = 1.2×10⁻³ m = 1.2 mm.
    f = _find("thermodynamics", "linear_expansion")
    assert f.solve("dL", {"alpha": 12e-6, "L0": 1.0, "dT": 100}) == pytest.approx(1.2e-3)


# ===========================================================================
# Electromagnetism  — OpenStax, College Physics 2e
# ===========================================================================

def test_ohms_law():
    # OpenStax College Physics 2e §20.2 (Ohm's Law). U = I·R; 2 A through 5 Ω →
    # 10 V. Inverting gives R = U/I and I = U/R.
    f = _find("electromagnetism", "ohm")
    assert f.solve("U", {"I": 2, "R": 5}) == pytest.approx(10)
    assert f.solve("R", {"U": 10, "I": 2}) == pytest.approx(5)
    assert f.solve("I", {"U": 10, "R": 5}) == pytest.approx(2)


def test_electric_power():
    # OpenStax College Physics 2e §20.4 (Electric Power). P = U·I; a 120 V
    # appliance drawing 2 A dissipates 240 W.
    f = _find("electromagnetism", "electric_power")
    assert f.solve("P", {"U": 120, "I": 2}) == pytest.approx(240)


def test_coulombs_law_two_one_coulomb_charges():
    # OpenStax College Physics 2e §18.3 (Coulomb's Law). Two 1 C charges 1 m
    # apart: F = k·q₁·q₂/r² = 8.988×10⁹ N (k = 8.988×10⁹ N·m²/C²).
    f = _find("electromagnetism", "coulomb")
    assert f.solve("F", {"q1": 1, "q2": 1, "r": 1}) == pytest.approx(8.988e9, rel=1e-3)


def test_capacitor_charge():
    # OpenStax College Physics 2e §19.5 (Capacitors). Q = C·U; a 1 µF capacitor
    # at 12 V holds Q = 1×10⁻⁶ · 12 = 1.2×10⁻⁵ C = 12 µC.
    f = _find("electromagnetism", "capacitor_charge")
    assert f.solve("Q", {"C": 1e-6, "U": 12}) == pytest.approx(1.2e-5)


def test_capacitor_stored_energy():
    # OpenStax College Physics 2e §19.7 (Energy in a Capacitor). W = ½·C·U²;
    # 2 µF at 100 V stores ½·2×10⁻⁶·100² = 0.01 J = 10 mJ.
    f = _find("electromagnetism", "capacitor_energy")
    assert f.solve("W", {"C": 2e-6, "U": 100}) == pytest.approx(0.01)


def test_resistance_of_a_copper_wire():
    # OpenStax College Physics 2e §20.3 (Resistance and Resistivity). Copper
    # ρ = 1.68×10⁻⁸ Ω·m; a 10 m wire of 1 mm² (1×10⁻⁶ m²) cross-section:
    # R = ρ·L/S = 1.68×10⁻⁸·10/1×10⁻⁶ = 0.168 Ω.
    f = _find("electromagnetism", "resistance_series")
    assert f.solve("R", {"rho": 1.68e-8, "L": 10, "S": 1e-6}) == pytest.approx(0.168)


# ===========================================================================
# Waves & optics  — OpenStax, College Physics 2e
# ===========================================================================

def test_wave_speed_of_a_sound_wave():
    # OpenStax College Physics 2e §16.9 (Waves). v = λ·f. A 0.5 m wavelength at
    # 680 Hz gives 340 m/s — the speed of sound in air at ~15 °C.
    f = _find("waves", "wave_speed")
    assert f.solve("v", {"lam": 0.5, "f": 680}) == pytest.approx(340)


def test_period_is_inverse_of_frequency():
    # OpenStax College Physics 2e §16.2. T = 1/f; 50 Hz → 0.02 s.
    f = _find("waves", "period_frequency")
    assert f.solve("T", {"f": 50}) == pytest.approx(0.02)


def test_photon_energy_of_green_light():
    # OpenStax College Physics 2e §29.1 (Photon energy E = h·f). Green light
    # at 500 nm has f = c/λ = 5.996×10¹⁴ Hz, so E = h·f ≈ 3.97×10⁻¹⁹ J
    # (≈ 2.48 eV).
    f = _find("waves", "photon_energy")
    frequency = 299792458.0 / 500e-9
    assert f.solve("E", {"f": frequency}) == pytest.approx(3.97e-19, rel=1e-3)


def test_wavelength_of_an_fm_radio_wave():
    # OpenStax College Physics 2e §24.3. λ = c/f; a 100 MHz (1×10⁸ Hz) FM
    # carrier has λ = c/f ≈ 3.0 m.
    f = _find("waves", "wavelength_light")
    assert f.solve("lam", {"f": 1e8}) == pytest.approx(2.998, rel=1e-3)


def test_snells_law_air_into_water():
    # OpenStax College Physics 2e §25.3 (Law of Refraction). Light entering
    # water (n = 1.333) from air (n = 1) at 30° refracts to ≈22.03°
    # (sin θ₂ = sin 30° / 1.333).
    f = _find("waves", "snell")
    theta2 = f.solve("theta2", {"n1": 1.0, "theta1": 30.0, "n2": 1.333})
    assert theta2 == pytest.approx(22.03, abs=0.05)


def test_snell_total_internal_reflection_beyond_critical_angle():
    # OpenStax College Physics 2e §25.4. Going water→air at 60° exceeds the
    # critical angle (~48.6°), so there is no refracted ray.
    f = _find("waves", "snell")
    with pytest.raises(SolveError) as info:
        f.solve("theta2", {"n1": 1.333, "theta1": 60.0, "n2": 1.0})
    assert info.value.code == "total_internal_reflection"


# ===========================================================================
# Unit converter  — NIST SP 811 / SI exact definitions
# ===========================================================================

def test_length_conversions_nist_exact():
    # NIST SP 811 App. B: 1 mile = 1.609344 km, 1 in = 2.54 cm, 1 ft = 0.3048 m
    # (all exact by definition).
    assert units.convert(1, "mile", "kilometer", "length") == pytest.approx(1.609344)
    assert units.convert(1, "inch", "centimeter", "length") == pytest.approx(2.54)
    assert units.convert(1, "foot", "meter", "length") == pytest.approx(0.3048)


def test_mass_conversions_nist_exact():
    # NIST SP 811: 1 lb = 0.45359237 kg (exact); 1 oz = lb/16 = 28.349523125 g.
    assert units.convert(1, "pound", "kilogram", "mass") == pytest.approx(0.45359237)
    assert units.convert(1, "ounce", "gram", "mass") == pytest.approx(28.349523125)


def test_energy_conversions():
    # Thermochemical calorie = 4.184 J (exact); 1 kWh = 3.6×10⁶ J; 1 eV =
    # 1.602176634×10⁻¹⁹ J (CODATA 2018, exact since the 2019 SI redefinition).
    assert units.convert(1, "calorie", "joule", "energy") == pytest.approx(4.184)
    assert units.convert(1, "kwh", "joule", "energy") == pytest.approx(3.6e6)
    assert units.convert(1, "ev", "joule", "energy") == pytest.approx(1.602176634e-19)


def test_pressure_conversions():
    # 1 atm = 101325 Pa (exact, defined); 1 mmHg = 133.322387415 Pa.
    assert units.convert(1, "atm", "pascal", "pressure") == pytest.approx(101325)
    assert units.convert(1, "mmhg", "pascal", "pressure") == pytest.approx(133.322387415)


def test_speed_conversions():
    # 36 km/h = 10 m/s; 1 knot = 1 nautical mile/h = 1852/3600 ≈ 0.514444 m/s.
    assert units.convert(36, "km_per_hour", "meter_per_second", "speed") == pytest.approx(10)
    assert units.convert(1, "knot", "meter_per_second", "speed") == pytest.approx(0.5144444, rel=1e-6)


def test_temperature_conversions():
    # Defining points: 100 °C = 212 °F; normal body temp 37 °C = 310.15 K;
    # absolute zero 0 K = −273.15 °C.
    assert units.convert(100, "celsius", "fahrenheit", "temperature") == pytest.approx(212)
    assert units.convert(37, "celsius", "kelvin", "temperature") == pytest.approx(310.15)
    assert units.convert(0, "kelvin", "celsius", "temperature") == pytest.approx(-273.15)


def test_angle_conversions():
    # A straight angle is π rad = 180°; a right angle is 100 gradians = 90°.
    assert units.convert(180, "degree", "radian", "angle") == pytest.approx(math.pi)
    assert units.convert(100, "gradian", "degree", "angle") == pytest.approx(90)


def test_time_conversions_si_exact():
    # SI defined multiples of the second (NIST SP 811): 1 min = 60 s,
    # 1 h = 3600 s, 1 day = 86400 s (all exact).
    assert units.convert(1, "hour", "second", "time") == pytest.approx(3600)
    assert units.convert(1, "day", "second", "time") == pytest.approx(86400)


def test_force_conversions_exact():
    # 1 kgf = 9.80665 N (3rd CGPM 1901: standard gravity g₀ = 9.80665 m/s²,
    # exact). 1 dyne = 10⁻⁵ N (CGS, exact). 1 kN = 1000 N.
    assert units.convert(1, "kgf", "newton", "force") == pytest.approx(9.80665)
    assert units.convert(1, "dyne", "newton", "force") == pytest.approx(1e-5)
    assert units.convert(1, "kilonewton", "newton", "force") == pytest.approx(1000)


# ===========================================================================
# Vectors  — OpenStax, Calculus Vol. 3 (Vectors in Space)
# ===========================================================================

def test_dot_product():
    # OpenStax Calculus Vol. 3 §2.3 (Dot Product). (1,2,3)·(4,5,6) =
    # 4 + 10 + 18 = 32.
    assert V.run("dot", "1,2,3", "4,5,6").output_text == "u·v = 32"


def test_cross_product_3d():
    # OpenStax Calculus Vol. 3 §2.4 (Cross Product).
    # (2,3,4)×(5,6,7) = (3·7−4·6, 4·5−2·7, 2·6−3·5) = (−3, 6, −3).
    assert V.run("cross", "2,3,4", "5,6,7").output_text == "u×v = (-3, 6, -3)"


def test_cross_product_2d_is_the_scalar_z_component():
    # In 2-D the cross product is the scalar (1·4 − 2·3) = −2.
    assert V.run("cross", "1,2", "3,4").output_text == "u×v = -2"


def test_angle_between_vectors():
    # OpenStax Calculus Vol. 3 §2.3. The angle between (1,0) and (1,1) is 45°;
    # between the perpendicular (1,0,0) and (0,1,0) it is 90°.
    assert V.run("angle", "1,0", "1,1").output_text == "θ = 45°"
    assert V.run("angle", "1,0,0", "0,1,0").output_text == "θ = 90°"


def test_vector_projection():
    # OpenStax Calculus Vol. 3 §2.3 (Projections). The projection of (3,4) onto
    # the x-axis (1,0) is (3,0).
    assert V.run("projection", "3,4", "1,0").output_text == "proj_v(u) = (3, 0)"


def test_unit_vector():
    # The unit vector of (3,4) (length 5) is (0.6, 0.8).
    assert V.run("unit", "3,4").output_text == "(0.6, 0.8)"


def test_magnitude_pythagorean_quadruple():
    # |(3,4,12)| = √(9+16+144) = √169 = 13 (a Pythagorean quadruple).
    assert V.run("magnitude", "3,4,12").output_text == "|u| = 13"


# ===========================================================================
# Symbolic math (CAS)  — OpenStax, Calculus Vol. 1/2 (standard results)
# ===========================================================================

def test_derivatives():
    # OpenStax Calculus Vol. 1 §3.3/§3.5. d/dx(x³) = 3x²; d/dx(sin x) = cos x.
    assert cas.run("derivative", "x^3", "x").output_text == "3*x**2"
    assert cas.run("derivative", "sin(x)", "x").output_text == "cos(x)"


def test_indefinite_integrals():
    # OpenStax Calculus Vol. 2 §1.1/§1.5. ∫x² dx = x³/3; ∫(1/x) dx = ln|x|.
    assert cas.run("integral", "x^2", "x").output_text == "x**3/3"
    assert cas.run("integral", "1/x", "x").output_text == "log(x)"


def test_solve_quadratic_with_integer_roots():
    # x² − 5x + 6 = (x−2)(x−3) = 0 → x = 2, 3.
    assert cas.run("solve", "x^2 - 5x + 6", "x").output_text == "x = 2, x = 3"


def test_factor_difference_and_common_factor():
    # x³ − x = x(x−1)(x+1).
    assert cas.run("factor", "x^3 - x").output_text == "x*(x - 1)*(x + 1)"


def test_pythagorean_trig_identity():
    # OpenStax Algebra & Trig §9.1. sin²x + cos²x simplifies to 1, and the
    # identity is confirmed True.
    assert cas.run("trig_simplify", "sin(x)^2 + cos(x)^2").output_text == "1"
    assert cas.run("identity", "sin(x)^2 + cos(x)^2 = 1").output_text == "True"


def test_fundamental_trig_limit():
    # OpenStax Calculus Vol. 1 §2.3. lim(x→0) sin(x)/x = 1.
    assert cas.run("limit", "sin(x)/x", "x", at="0").output_text == "1"


def test_limit_defining_eulers_number():
    # OpenStax Calculus Vol. 2 §6.1. lim(x→∞) (1 + 1/x)^x = e ≈ 2.71828.
    out = cas.run("limit", "(1+1/x)^x", "x", at="oo").output_text
    assert out.startswith("E") and float(out.split("≈")[1]) == pytest.approx(math.e, rel=1e-5)


def test_expand_binomials():
    # OpenStax Algebra & Trig §1.4 (binomial expansion). (x+1)³ and (a+b)².
    assert cas.run("expand", "(x+1)^3").output_text == "x**3 + 3*x**2 + 3*x + 1"
    assert cas.run("expand", "(a+b)^2").output_text == "a**2 + 2*a*b + b**2"


def test_simplify_rational_expression():
    # (x²−1)/(x−1) = (x−1)(x+1)/(x−1) = x+1.
    assert cas.run("simplify", "(x^2-1)/(x-1)").output_text == "x + 1"


def test_maclaurin_series():
    # OpenStax Calculus Vol. 2 §6.3 (Table 6.1). Maclaurin series (about 0),
    # truncated by the engine: eˣ = 1 + x + x²/2 + x³/6 + x⁴/24 + …;
    # sin x = x − x³/6 + x⁵/120 − …
    assert cas.run("series", "exp(x)", "x", at="0").output_text == (
        "x**5/120 + x**4/24 + x**3/6 + x**2/2 + x + 1"
    )
    assert cas.run("series", "sin(x)", "x", at="0").output_text == "x**5/120 - x**3/6 + x"


def test_evaluate_numeric_expressions():
    # Standard constants to the engine's 15 significant figures.
    assert cas.run("evaluate", "2^10").output_text == "1024.00000000000"
    assert cas.run("evaluate", "sqrt(2)").output_text == "1.41421356237310"
