import re

import pytest

import sns_sqs_communicator

from . import queues


async def test_fail(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that failed processing works as expected."""
    message = queues.Message[queues.FailQueueBodySchema](
        body_schema=queues.FailQueueBodySchema(
            error="Some error",
        ),
        action=queues.messages.MessageAction.fail,
        type="fail",
    )
    await sns_sqs_communicator.testing.push_and_pull_failed_result(
        sns_sqs_worker=sns_sqs_worker,
        message=message,
        expected_message=message.body_schema.error,
        expected_exception=ValueError,
    )


async def test_fail_with_testing_successful_result(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that failed processing works when we expect successful result."""
    message = queues.Message[queues.FailQueueBodySchema](
        body_schema=queues.FailQueueBodySchema(
            error="Some error with success",
        ),
        action=queues.messages.MessageAction.fail,
        type="fail",
    )
    with pytest.raises(ValueError, match=re.escape(message.body_schema.error)):
        await sns_sqs_communicator.testing.push_and_pull_successful_result(
            sns_sqs_worker=sns_sqs_worker,
            message=message,
        )


async def test_not_found_processor(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that cancellation works on not found processor as expected."""
    message = queues.Message[queues.UnknownQueueBodySchema](
        body_schema=queues.UnknownQueueBodySchema(
            message="test_not_found_processor",
        ),
        action=queues.MessageAction.not_found_action,
        type="unknown",
    )
    await sns_sqs_communicator.testing.push_and_pull_failed_result(
        sns_sqs_worker=sns_sqs_worker,
        message=message,
        expected_message=(
            "'No event processors are registered for key unknown'"
        ),
        expected_exception=KeyError,
    )
