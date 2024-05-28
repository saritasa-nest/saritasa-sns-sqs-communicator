import collections.abc
import logging
import typing

from .. import messages, parsers, processing, queue, sqs_poll_worker, topic


class TestWorker(typing.Generic[messages.MessageActionT]):
    """Worker for testing code related to sns-sqs-communicator."""

    def __init__(
        self,
        sqs_poll_worker_class: type[
            sqs_poll_worker.SQSPollWorker[messages.MessageActionT]
        ],
        sqs_queue: queue.SQSQueue,
        dead_letter_sqs_queue: queue.SQSQueue,
        sns_topic: topic.SNSTopic,
        parser: type[parsers.ParserProtocol[messages.MessageActionT]],
        logger: logging.Logger,
    ) -> None:
        self.sqs_poll_worker_class = sqs_poll_worker_class
        self.queue = sqs_queue
        self.dead_letter_queue = dead_letter_sqs_queue
        self.sns_topic = sns_topic
        self.parser = parser
        self.logger = logger

    async def publish_and_pull(
        self,
        message: messages.Message[typing.Any, messages.MessageActionT],
    ) -> collections.abc.Sequence[processing.ProcessingResult[typing.Any]]:
        """Publish message to sns and pull result."""
        await self.sns_topic.publish(
            body=message.serialize_body(),
            metadata=message.metadata,
        )
        return await self.pull()

    async def pull(
        self,
    ) -> collections.abc.Sequence[processing.ProcessingResult[typing.Any]]:
        """Pull and process messages."""
        return await self.sqs_poll_worker_class.pull_messages(
            queue=self.queue,
            dead_letter_queue=self.dead_letter_queue,
            parser=self.parser,
            logger=self.logger,
        )
