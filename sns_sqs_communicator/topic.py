import typing

from . import clients, fifo_attributes_creator, metrics, types


class SNSTopic:
    """Implementation of topic through Amazon SNS."""

    def __init__(
        self,
        client: clients.SNSClient,
        topic_arn: str,
        fifo_attrs_creator: (
            fifo_attributes_creator.FifoAttributesCreatorProtocol | None
        ),
    ) -> None:
        self.client = client
        self.topic_arn = topic_arn
        self.fifo_attrs_creator = fifo_attrs_creator

    @metrics.tracker
    async def publish(
        self,
        body: dict[str, typing.Any],
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Publish message to sns topic."""
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

        await self.client.publish(
            topic_arn=self.topic_arn,
            message_attributes=self._prepare_metadata(metadata),
            body=body,
            **additional_attrs,
        )

    @staticmethod
    @metrics.tracker
    def _prepare_metadata(
        metadata: dict[str, str],
    ) -> types.SNSMessageAttributes:
        """Prepare metadata for queue."""
        return {
            key: {
                "DataType": "String",
                "StringValue": value,
            }
            for key, value in metadata.items()
        }
