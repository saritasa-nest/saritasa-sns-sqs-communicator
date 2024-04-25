import hashlib
import typing

import ujson

from . import metrics


class FifoAttributesCreatorProtocol(typing.Protocol):
    """Protocol to create special attributes for AWS FIFO topics and queues."""

    @classmethod
    def get_message_deduplication_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message deduplication id."""
        ...

    @classmethod
    def get_message_group_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message group id."""
        ...


class FifoAttributesCreator(FifoAttributesCreatorProtocol):
    """Class to create special attributes for AWS FIFO topics and queues.

    It is needed to create attributes for aws fifo queues and topics since they
    require MessageDeduplicationId and MessageGroupId attrs to work correctly.

    """

    @classmethod
    @metrics.tracker
    def get_message_deduplication_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message deduplication id."""
        action = metadata["action"]
        # Make sha256 hash of body like AWS do under the hood but also add
        # action to the beginning to avoid treating messages as duplicates if
        # they have same body but different actions.
        body_sha256_hash = hashlib.sha256(ujson.dumps(body).encode())
        return f"{action}:{body_sha256_hash.hexdigest()}"

    @classmethod
    @metrics.tracker
    def get_message_group_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message group id."""
        return metadata["type"]


class DeadLetterFifoAttributesCreator(FifoAttributesCreatorProtocol):
    """Class to create special attributes for AWS FIFO topics and queues.

    It is needed to create attributes for aws fifo queues and topics since they
    require MessageDeduplicationId and MessageGroupId attrs to work correctly.

    """

    @classmethod
    @metrics.tracker
    def get_message_deduplication_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message deduplication id."""
        message_id = metadata["message_id"]
        # Make sha256 hash of body like AWS do under the hood but also add
        # action to the beginning to avoid treating messages as duplicates if
        # they have same body but different actions.
        body_sha256_hash = hashlib.sha256(ujson.dumps(body).encode())
        return f"{message_id}:{body_sha256_hash.hexdigest()}"

    @classmethod
    @metrics.tracker
    def get_message_group_id(
        cls,
        body: dict[str, typing.Any],
        metadata: dict[str, str],
    ) -> str:
        """Construct message group id."""
        return metadata["message_id"]
