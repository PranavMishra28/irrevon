"""Known-answer tests for the §5 statistics — every procedure pinned against
published values from independent sources (never against this implementation's
own output).

Reference provenance (research pass, 2026-07-22; two-source cross-checks
unless flagged):

- t quantiles: NIST/SEMATECH e-Handbook §1.3.6.7.2 + the 7-d.p. planetquantum
  Student-t table (df ∈ {4, 5, 9, 19} at both sources; df=10 cross-checked
  against NIST to 3 d.p. only — flagged inline).
- Paired t: R's built-in `sleep` dataset (Student 1908 / Cushny–Peebles),
  `t.test(paired=TRUE)` published output.
- TOST: TOSTER `t_TOST(sleep, eqb=0.5)` published output (Lakens;
  aaroncaldwell.us/TOSTERpkg IntroTOSTt) — single primary source, internally
  consistent with the dual-sourced t machinery.
- Wilson: Newcombe 1998 (Stat. Med. 17:857–872) Table I method 3.
- Holm/BH: r-statistics.co worked example verified there against R `p.adjust`
  (identical() == TRUE).
- Haldane–Anscombe: Weber et al. 2020 (Res. Synth. Methods 11, eqs. 3–4).
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from irrevon.bench.stats import (
    benjamini_hochberg,
    benjamini_hochberg_adjusted,
    holm_adjusted,
    holm_bonferroni,
    log_relative_risk,
    paired_t,
    sign_flip_permutation_p,
    student_t_cdf,
    student_t_quantile,
    tost_paired,
    wilson_interval,
)

# R sleep data: paired differences group1 − group2 (10 subjects).
SLEEP_DIFFS = [-1.2, -2.4, -1.3, -1.3, 0.0, -1.0, -1.8, -0.8, -4.6, -1.4]


# ── Student-t distribution ─────────────────────────────────────────────────────

T_QUANTILES = [
    # (df, one_sided_p, expected) — NIST + planetquantum (6 s.f.)
    (4, 0.95, 2.131847),
    (4, 0.975, 2.776445),
    (5, 0.95, 2.015048),
    (5, 0.975, 2.570582),
    (9, 0.95, 1.833113),
    (9, 0.975, 2.262157),
    # df=10: NIST 3-d.p. cross-check only (2.228 / 1.812); 6-s.f. values rest
    # on one full-precision source — flagged in the research record.
    (10, 0.95, 1.812461),
    (10, 0.975, 2.228139),
    (19, 0.95, 1.729133),
    (19, 0.975, 2.093024),
]


@pytest.mark.parametrize(("df", "p", "expected"), T_QUANTILES)
def test_t_quantiles_match_published_tables(df: int, p: float, expected: float) -> None:
    assert student_t_quantile(p, df) == pytest.approx(expected, abs=5e-6)
    # Symmetry: the lower-tail quantile is the negation.
    assert student_t_quantile(1.0 - p, df) == pytest.approx(-expected, abs=5e-6)


@pytest.mark.parametrize(("df", "p", "expected"), T_QUANTILES)
def test_t_cdf_inverts_the_quantiles(df: int, p: float, expected: float) -> None:
    assert student_t_cdf(expected, df) == pytest.approx(p, abs=1e-6)


@given(t=st.floats(min_value=-50, max_value=50), df=st.integers(min_value=1, max_value=200))
def test_t_cdf_monotone_and_bounded(t: float, df: int) -> None:
    value = student_t_cdf(t, df)
    assert 0.0 <= value <= 1.0
    assert student_t_cdf(t + 0.5, df) >= value
    # Symmetry property: F(−t) = 1 − F(t).
    assert student_t_cdf(-t, df) == pytest.approx(1.0 - value, abs=1e-12)


# ── Paired t (R sleep known answer) ────────────────────────────────────────────


def test_paired_t_sleep_known_answer() -> None:
    result = paired_t(SLEEP_DIFFS, ci_level=0.95)
    assert result.n == 10
    assert result.df == 9
    assert result.mean_diff == pytest.approx(-1.58, abs=1e-12)
    assert result.t_stat == pytest.approx(-4.062128, abs=1e-5)
    assert result.p_two_sided == pytest.approx(0.002833, abs=1e-5)
    assert result.ci_low == pytest.approx(-2.4598858, abs=1e-6)
    assert result.ci_high == pytest.approx(-0.7001142, abs=1e-6)


def test_paired_t_rejects_degenerate_input() -> None:
    with pytest.raises(ValueError):
        paired_t([1.0])


# ── TOST (TOSTER sleep, eqb = 0.5, known answer) ───────────────────────────────


def test_tost_sleep_known_answer() -> None:
    result = tost_paired(SLEEP_DIFFS, margin=0.5, alpha=0.05)
    base = paired_t(SLEEP_DIFFS, ci_level=0.90)
    # Published TOSTER output: lower t = −2.777, upper t = −5.348, df = 9;
    # equivalence p = 0.9892 (NOT equivalent); 90% CI (−2.2930053, −0.8669947).
    t_lower = (base.mean_diff + 0.5) / base.se
    t_upper = (base.mean_diff - 0.5) / base.se
    assert t_lower == pytest.approx(-2.777, abs=5e-4)
    assert t_upper == pytest.approx(-5.348, abs=5e-4)
    assert result.equivalent is False
    assert max(result.p_lower, result.p_upper) == pytest.approx(0.9892, abs=5e-4)
    assert result.ci_low == pytest.approx(-2.2930053, abs=1e-6)
    assert result.ci_high == pytest.approx(-0.8669947, abs=1e-6)


def test_tost_declares_equivalence_when_ci_inside_margins() -> None:
    diffs = [0.001, -0.002, 0.0015, -0.001, 0.0005, -0.0005, 0.001, -0.001]
    result = tost_paired(diffs, margin=0.01, alpha=0.05)
    assert result.equivalent is True
    assert -0.01 < result.ci_low and result.ci_high < 0.01


def test_tost_margin_is_a_required_positive_parameter() -> None:
    """§0.1 discipline: no default margin exists anywhere; zero/negative
    margins are rejected, never coerced."""
    with pytest.raises(ValueError, match="human parameter"):
        tost_paired(SLEEP_DIFFS, margin=0.0, alpha=0.05)


# ── Wilson intervals (Newcombe 1998 Table I, method 3) ─────────────────────────

WILSON_CASES = [
    (81, 263, 0.2553, 0.3662),
    (15, 148, 0.0624, 0.1605),
    (0, 20, 0.0000, 0.1611),
    (1, 29, 0.0061, 0.1718),
]


@pytest.mark.parametrize(("x", "n", "low", "high"), WILSON_CASES)
def test_wilson_newcombe_known_answers(x: int, n: int, low: float, high: float) -> None:
    got_low, got_high = wilson_interval(x, n)
    assert got_low == pytest.approx(low, abs=5e-5)
    assert got_high == pytest.approx(high, abs=5e-5)


@given(n=st.integers(min_value=1, max_value=500), x=st.integers(min_value=0, max_value=500))
def test_wilson_bounds_are_sane(n: int, x: int) -> None:
    x = min(x, n)
    low, high = wilson_interval(x, n)
    eps = 1e-12  # float rounding at the exact boundary cases (x=0, x=n)
    assert 0.0 <= low <= x / n + eps
    assert x / n - eps <= high <= 1.0


# ── Exact sign-flip permutation ────────────────────────────────────────────────


def test_sign_flip_worked_example() -> None:
    # d = [1.2, 2.3, 0.7, 3.1]: all positive; only all-+ and all-− of the 16
    # assignments tie-or-exceed |mean| → two-sided p = 2/16 = 0.125.
    assert sign_flip_permutation_p([1.2, 2.3, 0.7, 3.1]) == pytest.approx(0.125)


def test_sign_flip_floor_is_two_to_minus_s() -> None:
    """The preregistration's honesty note (§5.2): at S = 5 the two-sided floor
    is 1/2⁴ = 2/2⁵ — it CANNOT reject at α = 0.025; at S = 10, floor 1/1024
    (one-sided all-agree)."""
    p5 = sign_flip_permutation_p([1.0, 2.0, 3.0, 4.0, 5.0])
    assert p5 == pytest.approx(2 / 32)
    assert p5 > 0.025
    p10 = sign_flip_permutation_p([float(i) for i in range(1, 11)], alternative="greater")
    assert p10 == pytest.approx(1 / 1024)


@given(diffs=st.lists(st.floats(min_value=-5, max_value=5), min_size=2, max_size=8))
def test_sign_flip_p_is_a_probability(diffs: list[float]) -> None:
    p = sign_flip_permutation_p(diffs)
    assert 1.0 / 2 ** len(diffs) <= p <= 1.0


# ── Holm and Benjamini–Hochberg (R p.adjust known answers) ─────────────────────

RAW_P = {"a": 0.001, "b": 0.01, "c": 0.04, "d": 0.20, "e": 0.50}


def test_holm_adjusted_known_answer() -> None:
    adjusted = holm_adjusted(RAW_P)
    assert adjusted["a"] == pytest.approx(0.005)
    assert adjusted["b"] == pytest.approx(0.04)
    assert adjusted["c"] == pytest.approx(0.12)
    assert adjusted["d"] == pytest.approx(0.40)
    assert adjusted["e"] == pytest.approx(0.50)


def test_bh_adjusted_known_answer() -> None:
    adjusted = benjamini_hochberg_adjusted(RAW_P)
    assert adjusted["a"] == pytest.approx(0.005)
    assert adjusted["b"] == pytest.approx(0.025)
    assert adjusted["c"] == pytest.approx(0.04 * 5 / 3)
    assert adjusted["d"] == pytest.approx(0.25)
    assert adjusted["e"] == pytest.approx(0.50)


def test_rejection_sets_match_adjusted_p() -> None:
    holm = holm_bonferroni(RAW_P, alpha=0.05)
    assert holm == {"a": True, "b": True, "c": False, "d": False, "e": False}
    bh = benjamini_hochberg(RAW_P, q=0.05)
    assert bh == {"a": True, "b": True, "c": False, "d": False, "e": False}


@given(
    ps=st.dictionaries(
        st.text(min_size=1, max_size=3),
        st.floats(min_value=1e-9, max_value=1.0),
        min_size=1,
        max_size=8,
    )
)
def test_holm_never_rejects_more_than_bh(ps: dict[str, float]) -> None:
    """FWER control is strictly more conservative than FDR control at the
    same level — a structural property, not a tuning choice."""
    holm = holm_bonferroni(ps, alpha=0.05)
    bh = benjamini_hochberg(ps, q=0.05)
    assert sum(holm.values()) <= sum(bh.values())


# ── Haldane–Anscombe log relative risk ────────────────────────────────────────


def test_log_rr_uncorrected_case() -> None:
    log_rr, se = log_relative_risk(10, 100, 20, 100)
    assert log_rr == pytest.approx(math.log(0.5))
    assert se == pytest.approx(math.sqrt(1 / 10 - 1 / 100 + 1 / 20 - 1 / 100))


def test_log_rr_haldane_anscombe_zero_cell() -> None:
    # Weber et al. 2020 convention: ½ added to events AND group sizes.
    log_rr, se = log_relative_risk(0, 50, 5, 50)
    expected = math.log((0.5 / 50.5) / (5.5 / 50.5))
    assert log_rr == pytest.approx(expected)
    assert math.isfinite(se)
