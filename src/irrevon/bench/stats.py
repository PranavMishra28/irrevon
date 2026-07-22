"""Statistical primitives for the §5 analysis plan — stdlib-only, no scipy.

Everything here is deliberately dependency-free so the confirmatory analysis
is runnable on a clean machine from the wheel alone, and every procedure is
pinned by known-answer tests against published values (tests/bench/test_stats).

Implemented per the preregistration:

- Paired Student-t point estimates and CIs (§5.2) — t distribution via the
  regularized incomplete beta function (continued-fraction evaluation, the
  standard Lentz/Numerical-Recipes formulation; see also DLMF §8.17).
- TOST equivalence, paired form (§5.3; Schuirmann 1987, Lakens 2017).
- One-sided paired superiority tests (§5.4).
- Wilson score intervals (§5.2 descriptive companions; Brown, Cai & DasGupta 2001).
- Exact paired sign-flip permutation test (§5.2; floor p = 1/2^S).
- Holm–Bonferroni and Benjamini–Hochberg multiplicity procedures (§5.7).
- Log relative risk with the Haldane–Anscombe 0.5 correction (§5.5).

No default margins or thresholds: every equivalence margin and alpha is a
required argument — margins are §0.1 HUMAN freeze parameters, and this module
must be unable to choose them silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product

__all__ = [
    "PairedT",
    "TostResult",
    "benjamini_hochberg",
    "benjamini_hochberg_adjusted",
    "holm_adjusted",
    "holm_bonferroni",
    "log_relative_risk",
    "one_sided_p",
    "paired_t",
    "sign_flip_permutation_p",
    "student_t_cdf",
    "student_t_quantile",
    "tost_paired",
    "wilson_interval",
]

_EPS = 3e-14
_FPMIN = 1e-300


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return h
    raise ArithmeticError("betacf failed to converge")


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: int) -> float:
    """P(T ≤ t) for Student's t with ``df`` degrees of freedom."""
    if df < 1:
        raise ValueError("df must be ≥ 1")
    if t == 0.0:
        return 0.5
    x = df / (df + t * t)
    tail = 0.5 * _betainc(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def student_t_quantile(p: float, df: int) -> float:
    """Inverse CDF by bisection (robust; precision ~1e-12 is ample here)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    if p == 0.5:
        return 0.0
    lo, hi = -1e6, 1e6
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if student_t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class PairedT:
    n: int
    mean_diff: float
    sd_diff: float
    se: float
    t_stat: float
    df: int
    p_two_sided: float
    ci_low: float
    ci_high: float
    ci_level: float


def paired_t(diffs: list[float], *, ci_level: float = 0.95) -> PairedT:
    """Paired Student-t on per-seed differences (the §5.1 unit of inference)."""
    n = len(diffs)
    if n < 2:
        raise ValueError("paired t needs at least 2 pairs")
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)
    df = n - 1
    if se == 0.0:
        t_stat = math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
        p = 0.0 if mean != 0 else 1.0
        return PairedT(n, mean, sd, se, t_stat, df, p, mean, mean, ci_level)
    t_stat = mean / se
    p = 2.0 * (1.0 - student_t_cdf(abs(t_stat), df))
    t_crit = student_t_quantile(0.5 + ci_level / 2.0, df)
    return PairedT(
        n, mean, sd, se, t_stat, df, p,
        mean - t_crit * se, mean + t_crit * se, ci_level,
    )


@dataclass(frozen=True)
class TostResult:
    margin: float
    alpha: float
    p_lower: float  # H0₁: Δ ≤ −δ
    p_upper: float  # H0₂: Δ ≥ +δ
    equivalent: bool
    ci_low: float  # the (1 − 2α) CI the TOST verdict is equivalent to
    ci_high: float


def tost_paired(diffs: list[float], *, margin: float, alpha: float) -> TostResult:
    """Schuirmann's two one-sided tests, paired form (Lakens 2017): both
    one-sided tests at ``alpha``; equivalently the (1 − 2α) CI inside
    (−margin, +margin). No adjustment between the two components
    (intersection–union, Berger & Hsu 1996)."""
    if margin <= 0:
        raise ValueError("TOST margin must be positive (a §0.1 human parameter)")
    base = paired_t(diffs, ci_level=1.0 - 2.0 * alpha)
    if base.se == 0.0:
        inside = -margin < base.mean_diff < margin
        p = 0.0 if inside else 1.0
        return TostResult(margin, alpha, p, p, inside, base.ci_low, base.ci_high)
    t_lower = (base.mean_diff + margin) / base.se  # reject Δ ≤ −δ when large
    t_upper = (base.mean_diff - margin) / base.se  # reject Δ ≥ +δ when small
    p_lower = 1.0 - student_t_cdf(t_lower, base.df)
    p_upper = student_t_cdf(t_upper, base.df)
    return TostResult(
        margin, alpha, p_lower, p_upper,
        p_lower < alpha and p_upper < alpha,
        base.ci_low, base.ci_high,
    )


def one_sided_p(diffs: list[float]) -> float:
    """One-sided paired t p-value for H1: Δ < 0 (R reduces the rate; diffs are
    R − comparator)."""
    base = paired_t(diffs)
    if base.se == 0.0:
        return 0.0 if base.mean_diff < 0 else 1.0
    return student_t_cdf(base.t_stat, base.df)


def wilson_interval(successes: int, n: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval (Brown, Cai & DasGupta 2001). Default z is the
    two-sided 95% normal quantile."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be within [0, n]")
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p_hat + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def sign_flip_permutation_p(diffs: list[float], *, alternative: str = "two-sided") -> float:
    """Exact paired sign-flip permutation p-value over all 2^S assignments
    (§5.2; the floor is 1/2^S — at S = 5 it cannot reject at α = 0.025, which
    the preregistration notes honestly). Exchangeability of the sign under H0
    is the assumption; it is stated wherever this is reported."""
    n = len(diffs)
    if n == 0:
        raise ValueError("empty diffs")
    if n > 20:
        raise ValueError("exact enumeration limited to S ≤ 20")
    observed = sum(diffs) / n
    count = 0
    total = 0
    for signs in product((1.0, -1.0), repeat=n):
        stat = sum(s * d for s, d in zip(signs, diffs, strict=True)) / n
        total += 1
        if alternative == "two-sided":
            if abs(stat) >= abs(observed) - 1e-15:
                count += 1
        elif alternative == "less":
            if stat <= observed + 1e-15:
                count += 1
        elif alternative == "greater":
            if stat >= observed - 1e-15:
                count += 1
        else:
            raise ValueError(f"unknown alternative {alternative!r}")
    return count / total


def holm_bonferroni(p_values: dict[str, float], *, alpha: float) -> dict[str, bool]:
    """Holm's step-down procedure: reject smallest p while
    p_(i) ≤ α / (m − i); stop at the first failure."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    rejected: dict[str, bool] = {}
    still_rejecting = True
    for i, (name, p) in enumerate(ordered):
        threshold = alpha / (m - i)
        if still_rejecting and p <= threshold:
            rejected[name] = True
        else:
            still_rejecting = False
            rejected[name] = False
    return rejected


def benjamini_hochberg(p_values: dict[str, float], *, q: float) -> dict[str, bool]:
    """BH step-up FDR control: find the largest k with p_(k) ≤ (k/m)·q and
    reject all hypotheses with p ≤ p_(k)."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    k_star = 0
    for k, (_, p) in enumerate(ordered, start=1):
        if p <= (k / m) * q:
            k_star = k
    return {
        name: (i + 1) <= k_star for i, (name, _) in enumerate(ordered)
    }


def log_relative_risk(
    events_a: int, n_a: int, events_b: int, n_b: int
) -> tuple[float, float]:
    """Log relative risk (A vs B) with its SE, applying the Haldane–Anscombe
    0.5 correction when any cell of the 2×2 table is zero (§5.5).

    Convention per Weber et al. 2020 (Res. Synth. Methods 11, eqs. 3–4;
    Haldane 1955, Anscombe 1956): add ½ to the event counts AND to the group
    sizes — log RR = log[ (a+½)/(n₁+½) ÷ (c+½)/(n₀+½) ]."""
    if min(n_a, n_b) <= 0:
        raise ValueError("group sizes must be positive")
    a, b = float(events_a), float(events_b)
    na, nb = float(n_a), float(n_b)
    if a == 0 or b == 0 or a == na or b == nb:
        a += 0.5
        b += 0.5
        na += 0.5
        nb += 0.5
    log_rr = math.log((a / na) / (b / nb))
    se = math.sqrt(1.0 / a - 1.0 / na + 1.0 / b - 1.0 / nb)
    return log_rr, se


def holm_adjusted(p_values: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values: p̃_(k) = max_{j≤k} min((m−j+1)·p_(j), 1)
    (the running max enforces monotonicity; R `p.adjust(method="holm")`)."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for j, (name, p) in enumerate(ordered, start=1):
        running = max(running, min((m - j + 1) * p, 1.0))
        adjusted[name] = running
    return adjusted


def benjamini_hochberg_adjusted(p_values: dict[str, float]) -> dict[str, float]:
    """BH adjusted p-values: p̃_(k) = min_{j≥k} min((m/j)·p_(j), 1) (running min
    from the largest rank down; R `p.adjust(method="BH")`)."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for j in range(m, 0, -1):
        name, p = ordered[j - 1]
        running = min(running, min((m / j) * p, 1.0))
        adjusted[name] = running
    return adjusted
