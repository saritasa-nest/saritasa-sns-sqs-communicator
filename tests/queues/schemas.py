import sns_sqs_communicator


class BaseTestSchema(
    sns_sqs_communicator.schemas.QueueBodySchema,
):
    """Base schema for testing."""


class MathQueueBodySchema(
    BaseTestSchema,
    for_type="math_calc",
):
    """Schema for representation test queue messages."""

    a: int
    b: int


class CancelQueueBodySchema(
    BaseTestSchema,
    for_type="canceled",
):
    """Schema for representation test queue messages."""

    message: str


class UnknownQueueBodySchema(
    BaseTestSchema,
    for_type="unknown",
):
    """Schema for representation test queue messages."""

    message: str


class FailQueueBodySchema(
    BaseTestSchema,
    for_type="fail",
):
    """Schema for representation test queue messages."""

    error: str
