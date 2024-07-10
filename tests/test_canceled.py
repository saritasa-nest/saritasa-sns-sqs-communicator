import sns_sqs_communicator

from . import queues


async def test_canceled(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that successful processing works as expected."""
    message = queues.Message[queues.CancelQueueBodySchema](
        body_schema=queues.CancelQueueBodySchema(
            message="Cancel processing, pls",
        ),
        action=queues.messages.MessageAction.do_something,
        type="canceled",
    )
    await sns_sqs_communicator.testing.push_and_pull_canceled_result(
        sns_sqs_worker=sns_sqs_worker,
        message=message,
        expected_message=message.body_schema.message,
    )


async def test_not_found_action(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that cancellation works on not found action as expected."""
    message = queues.Message[queues.CancelQueueBodySchema](
        body_schema=queues.CancelQueueBodySchema(
            message="Cancel processing, pls",
        ),
        action=queues.MessageAction.not_found_action,
        type="canceled",
    )
    await sns_sqs_communicator.testing.push_and_pull_canceled_result(
        sns_sqs_worker=sns_sqs_worker,
        message=message,
        expected_message="No method defined for not_found_action action",
    )


async def test_not_found_schema(
    sns_sqs_worker: sns_sqs_communicator.testing.TestWorker[
        queues.MessageAction
    ],
) -> None:
    """Test that cancellation works on not found schema as expected."""
    message = queues.Message[queues.UnknownQueueBodySchema](
        body_schema=queues.UnknownQueueBodySchema(
            message="test_not_found_schema",
        ),
        action=queues.MessageAction.not_found_action,
        type="unknown_schema",
    )
    await sns_sqs_communicator.testing.push_and_pull_canceled_result(
        sns_sqs_worker=sns_sqs_worker,
        message=message,
        expected_message=(
            "Schema for message type unknown_schema is not registered"
        ),
    )
