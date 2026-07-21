"""Shared test configuration.

Hypothesis settings profiles (testing.md §1.1): ``dev`` = 100 examples for the
inner loop; ``ci`` / ``conformance`` = 1,000+ per master doc §12.2 (≥1,000
cases/invariant). Selected via HYPOTHESIS_PROFILE; the conformance gate is never
weakened by shrinking the budget.
"""

import os

from hypothesis import HealthCheck, settings

settings.register_profile("dev", max_examples=100)
settings.register_profile(
    "ci", max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None
)
settings.register_profile(
    "conformance",
    max_examples=1000,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
