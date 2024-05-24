import typing

import pytest

import sns_sqs_communicator


@pytest.fixture(scope="session", autouse=True)
def anyio_backend() -> str:
    """Specify async backend."""
    return "asyncio"


@pytest.fixture(scope="session")
def factory_fifo_attrs_creator() -> (
    sns_sqs_communicator.fifo_attributes_creator.FifoAttributesCreatorProtocol
    | None
):
    """Get fifo_attrs_creator for factory."""
    return sns_sqs_communicator.fifo_attributes_creator.FifoAttributesCreator


@pytest.fixture(scope="session")
def factory_dead_letter_fifo_attrs_creator() -> (
    sns_sqs_communicator.fifo_attributes_creator.FifoAttributesCreatorProtocol
    | None
):
    """Get fifo_attrs_creator for factory."""
    return sns_sqs_communicator.fifo_attributes_creator.DeadLetterFifoAttributesCreator  # noqa: E501


@pytest.fixture(scope="session")
def factory_queue_attributes() -> typing.Mapping[str, str] | None:
    """Get attributes for factory."""
    return {
        "FifoQueue": "true",
    }


@pytest.fixture(scope="session")
def factory_topic_attributes() -> typing.Mapping[str, str] | None:
    """Get attributes for factory."""
    return {
        "FifoTopic": "true",
        # Enable content-base deduplication which is required for FIFO
        # topic
        # https://docs.aws.amazon.com/sns/latest/dg/fifo-message-dedup.html
        "ContentBasedDeduplication": "true",
    }
