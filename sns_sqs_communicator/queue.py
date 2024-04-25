import collections.abc
import typing

import mypy_boto3_sqs.type_defs

from . import clients, fifo_attributes_creator, metrics, types


class SQSQueue:
    """Implementation of queue through Amazon SQS."""

    def __init__(
        self,
        client: clients.SQSClient,
        queue_url: str,
        fifo_attrs_creator: (
            fifo_attributes_creator.FifoAttributesCreatorProtocol | None
        ) = None,
        wait_time_seconds: int = 0,
    ) -> None:
        self.client = client
        self.queue_url = queue_url
        self.fifo_attrs_creator = fifo_attrs_creator
        self.wait_time_seconds = wait_time_seconds

    @metrics.tracker
    async def put(
        self,
        body: dict[str, typing.Any],
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Put sync message to queue."""
        metadata = metadata or {}
        additional_attrs = {}
        if self.fifo_attrs_creator:
            additional_attrs["MessageGroupId"] = (
                self.fifo_attrs_creator.get_message_group_id(
                    body,
                    metadata,
                )
            )
            additional_attrs["MessageDeduplicationId"] = (
                self.fifo_attrs_creator.get_message_deduplication_id(
                    body,
                    metadata,
                )
            )
        await self.client.send_message(
            queue_url=self.queue_url,
            metadata_attributes=self._prepare_metadata(metadata),
            body=body,
            **additional_attrs,
        )

    @metrics.tracker
    async def receive(
        self,
    ) -> collections.abc.AsyncIterator[
        mypy_boto3_sqs.type_defs.MessageTypeDef,
    ]:
        """Receive message from queue.

        It could be a single message or a batch depending on queue type, so
        this method returns list in general to handle both cases.

        """
        response = await self.client.receive_messages(
            queue_url=self.queue_url,
            wait_time_seconds=self.wait_time_seconds,
        )

        if raw_messages := response.get("Messages"):
            for raw_message in raw_messages:
                yield raw_message
            await self.delete_messages(raw_messages)

    @metrics.tracker
    async def receive_all(
        self,
    ) -> list[mypy_boto3_sqs.type_defs.MessageTypeDef]:
        """Receive all messages awaiting in queue."""
        collected_messages: list[mypy_boto3_sqs.type_defs.MessageTypeDef] = []
        response = await self.client.receive_messages(
            queue_url=self.queue_url,
            wait_time_seconds=self.wait_time_seconds,
        )

        while raw_messages := response.get("Messages"):
            for raw_message in raw_messages:
                collected_messages.append(raw_message)

            await self.delete_messages(raw_messages)
            response = await self.client.receive_messages(
                queue_url=self.queue_url,
                wait_time_seconds=self.wait_time_seconds,
            )
        return collected_messages

    @metrics.tracker
    async def delete_messages(
        self,
        messages_to_delete: collections.abc.Sequence[
            mypy_boto3_sqs.type_defs.MessageTypeDef
        ],
    ) -> mypy_boto3_sqs.type_defs.DeleteMessageBatchResultTypeDef:
        """Delete given messages from sqs."""
        return await self.client.delete_messages(
            queue_url=self.queue_url,
            messages_to_delete=messages_to_delete,
        )

    @staticmethod
    def _prepare_metadata(
        metadata: dict[str, str],
    ) -> types.SQSMessageAttributes:
        """Prepare metadata for queue."""
        return {
            key: {
                "DataType": "String",
                "StringValue": value,
            }
            for key, value in metadata.items()
        }
