import asyncio
import collections.abc
import contextlib
import typing

import mypy_boto3_sqs
import mypy_boto3_sqs.literals

from .. import (
    clients,
    fifo_attributes_creator,
    messages,
    parsers,
    processing,
    queue,
    schemas,
    topic,
)
from . import worker


async def check_messages_in_queue(
    messages: collections.abc.Sequence[
        messages.Message[
            schemas.QueueBodySchemaT,
            messages.MessageActionT,
        ]
    ],
    queue: queue.SQSQueue,
    parser: parsers.ParserProtocol[messages.MessageActionT],
    seconds_wait_for_message: int | float = 0.5,
) -> None:
    """Check expected messages appeared in queue."""
    # Give control to event loop and wait a little to make sure that messages
    # is processed by queue
    await asyncio.sleep(seconds_wait_for_message)
    received_messages = tuple(
        parser.parse(received_message)
        for received_message in await queue.receive_all()
    )
    parsed_messages = tuple(
        received_message.to_dict() for received_message in received_messages
    )
    for message in messages:
        assert message.to_dict() in parsed_messages, (
            message,
            received_messages,
        )


async def push_and_pull_successful_result(
    sns_sqs_worker: worker.TestWorker[messages.MessageActionT],
    message: messages.Message[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
) -> processing.ProcessingResult[typing.Any]:
    """Push and pull successful message."""
    results = await sns_sqs_worker.publish_and_pull(message=message)
    assert len(results) == 1, results
    result = results[0]
    result.raise_on_exception()
    assert result.is_ok
    return result


async def push_and_pull_canceled_result(
    sns_sqs_worker: worker.TestWorker[messages.MessageActionT],
    message: messages.Message[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
    expected_message: str,
) -> processing.ProcessingResult[typing.Any]:
    """Push and pull canceled message."""
    results = await sns_sqs_worker.publish_and_pull(message=message)
    assert len(results) == 1, results
    result = results[0]
    result.raise_on_failure()
    assert result.is_canceled, result
    assert result.message == expected_message, (
        result.message,
        expected_message,
    )
    return result


async def push_and_pull_failed_result(
    sns_sqs_worker: worker.TestWorker[messages.MessageActionT],
    message: messages.Message[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
    expected_message: str,
    expected_exception: type[Exception],
) -> processing.ProcessingResult[typing.Any]:
    """Push and pull failed message."""
    results = await sns_sqs_worker.publish_and_pull(message=message)
    assert len(results) == 1, results
    result = results[0]
    assert result.is_failed, result
    assert isinstance(result.exception, expected_exception), result.exception
    assert result.message == expected_message
    return result


@contextlib.asynccontextmanager
async def queue_factory(
    sqs_client: clients.SQSClient,
    queue_class: type[queue.SQSQueue],
    name: str,
    attributes: typing.Mapping[
        mypy_boto3_sqs.literals.QueueAttributeNameType,
        str,
    ]
    | None = None,
    fifo_attrs_creator: (
        fifo_attributes_creator.FifoAttributesCreatorProtocol | None
    ) = None,
) -> collections.abc.AsyncIterator[queue.SQSQueue]:
    """Create queue and delete it when you done working with it."""
    queue_url = (
        await sqs_client.create_queue(
            name=name,
            attributes=attributes,
        )
    )["QueueUrl"]
    yield queue_class(
        client=sqs_client,
        queue_url=queue_url,
        fifo_attrs_creator=fifo_attrs_creator,
    )
    await sqs_client.delete_queue(queue_url=queue_url)


@contextlib.asynccontextmanager
async def topic_factory(
    sqs_client: clients.SQSClient,
    sns_client: clients.SNSClient,
    topic_class: type[topic.SNSTopic],
    queue_name: str,
    name: str,
    attributes: typing.Mapping[str, str] | None = None,
    fifo_attrs_creator: (
        fifo_attributes_creator.FifoAttributesCreatorProtocol | None
    ) = None,
) -> collections.abc.AsyncIterator[topic.SNSTopic]:
    """Create topic, subtribe it to queue and delete it after using it."""
    queue_url = await sqs_client.get_queue_url(name=queue_name)
    queue_arn = await sqs_client.get_queue_arn(queue_url=queue_url)
    response = await sns_client.create_topic(
        name=name,
        attributes=attributes,
    )
    topic_arn = response["TopicArn"]
    await sns_client.subscribe(
        topic_arn=topic_arn,
        endpoint=queue_arn,
    )
    yield topic_class(
        client=sns_client,
        topic_arn=topic_arn,
        fifo_attrs_creator=fifo_attrs_creator,
    )
    await sns_client.delete_topic(topic_arn=topic_arn)
