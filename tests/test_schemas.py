import re

import pytest

from . import queues


async def test_duplicate_schema() -> None:
    """Test that it's impossible to create duplicated schema."""
    with pytest.raises(
        KeyError,
        match=re.escape(
            "math_calc is already registered(<class 'tests.test_schemas.test_duplicate_schema.<locals>.MathQueueBodySchema'>)",  # noqa: E501
        ),
    ):

        class MathQueueBodySchema(
            queues.BaseTestSchema,
            for_type="math_calc",
        ):
            """Processor for math calculations."""
