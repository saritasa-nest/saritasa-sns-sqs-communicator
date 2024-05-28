import re

import pytest

from . import queues


async def test_duplicate_processor() -> None:
    """Test that it's impossible to create duplicated processor."""
    with pytest.raises(
        KeyError,
        match=re.escape(
            "math_calc is already registered(<class 'tests.test_processing.test_duplicate_processor.<locals>.MathProcessor'>)",  # noqa: E501
        ),
    ):

        class MathProcessor(
            queues.Processor[queues.MathQueueBodySchema],
            for_type="math_calc",
        ):
            """Processor for math calculations."""


async def test_init_other() -> None:
    """Test that we can init processor from other."""
    queues.Processor().init_other(event_processor_class=queues.MathProcessor)
