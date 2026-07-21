"""Advisory-isolation fixtures: reuse the template-DB harness."""

from tests.integration.conftest import (  # noqa: F401
    DBHandles,
    fresh_db,
    fresh_db_unaudited,
    template_db,
)
