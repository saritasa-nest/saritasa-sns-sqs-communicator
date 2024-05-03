import logging
import typing

import sentry_sdk
import sentry_sdk.tracing

from .. import messages, processing, schemas


class SentryProcessor(
    processing.Processor[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
    typing.Generic[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
):
    """Processor with sentry integration."""

    async def __call__(
        self,
        message: messages.Message[
            schemas.QueueBodySchemaT,
            messages.MessageActionT,
        ],
        logger: logging.Logger,
    ) -> typing.Any:
        """Execute processor."""
        with sentry_sdk.start_transaction(
            op="task",
            name=f"{self.__class__.__name__}.{message.action}",
        ) as transaction:
            transaction.set_tag("type", message.type)
            transaction.set_tag("action", message.action)
            transaction.set_data(
                "body_schema",
                message.body_schema.model_dump(),
            )
            return await super().__call__(message=message, logger=logger)
