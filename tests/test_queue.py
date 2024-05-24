import sns_sqs_communicator

from . import queues


async def test_queue_client(
    sqs_queue: sns_sqs_communicator.queue.SQSQueue,
    sqs_parser: queues.SQSParser,
) -> None:
    """Test that queue client works as expected."""
    message = queues.Message[queues.MathQueueBodySchema](
        body_schema=queues.MathQueueBodySchema(
            a=1,
            b=2,
        ),
        action=queues.messages.MessageAction.fail,
        type="math_calc",
    )
    await sqs_queue.put(
        body=message.serialize_body(),
        metadata=message.metadata,
    )
    await sns_sqs_communicator.testing.check_messages_in_queue(
        messages=(message,),
        queue=sqs_queue,
        parser=sqs_parser,
    )
