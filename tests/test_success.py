import random

import pytest

import sns_sqs_communicator

from . import queues


@pytest.mark.parametrize(
    "action",
    [
        queues.MessageAction.plus,
        queues.MessageAction.minus,
    ],
)
async def test_success(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
    action: queues.MessageAction,
) -> None:
    """Test that successful processing works as expected."""
    message = queues.Message[queues.MathQueueBodySchema](
        body_schema=queues.MathQueueBodySchema(
            a=random.randint(1, 100),
            b=random.randint(1, 100),
        ),
        action=action,
        type="math_calc",
    )
    result = (
        await sns_sqs_communicator.testing.push_and_pull_successful_result(
            sns_sqs_worker=sns_sqs_worker,
            message=message,
        )
    )
    match action:
        case queues.MessageAction.plus:
            assert (
                result.result == message.body_schema.a + message.body_schema.b
            )
        case queues.MessageAction.minus:
            assert (
                result.result == message.body_schema.a - message.body_schema.b
            )
