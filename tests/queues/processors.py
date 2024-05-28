import typing

import sns_sqs_communicator

from . import messages, schemas


class Processor(
    sns_sqs_communicator.sentry.SentryProcessor[
        sns_sqs_communicator.schemas.QueueBodySchemaT,
        messages.MessageAction,
    ],
    typing.Generic[sns_sqs_communicator.schemas.QueueBodySchemaT],
):
    """Base processor for tests."""


class MathProcessor(
    Processor[schemas.MathQueueBodySchema],
    for_type="math_calc",
):
    """Processor for math calculations."""

    async def plus(
        self,
        message: messages.Message[schemas.MathQueueBodySchema],
        **kwargs,
    ) -> int:
        """Perform action."""
        return message.body_schema.a + message.body_schema.b

    async def minus(
        self,
        message: messages.Message[schemas.MathQueueBodySchema],
        **kwargs,
    ) -> int:
        """Perform action."""
        return message.body_schema.a - message.body_schema.b


class CanceledProcessor(
    Processor[schemas.CancelQueueBodySchema],
    for_type="canceled",
):
    """Processor which always cancels."""

    async def do_something(
        self,
        message: messages.Message[schemas.CancelQueueBodySchema],
        **kwargs,
    ) -> None:
        """Cancel processing."""
        raise sns_sqs_communicator.processing.CancelProcessingError(
            reason=message.body_schema.message,
        )


class FailProcessor(
    Processor[schemas.FailQueueBodySchema],
    for_type="fail",
):
    """Processor which always fails."""

    async def fail(
        self,
        message: messages.Message[schemas.FailQueueBodySchema],
        **kwargs,
    ) -> None:
        """Cancel processing."""
        raise ValueError(message.body_schema.error)
