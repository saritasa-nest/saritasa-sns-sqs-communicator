import collections
import collections.abc
import contextlib
import logging
import typing

from .. import messages, metrics, schemas

ProcessorT = typing.TypeVar(
    "ProcessorT",
    bound="Processor[typing.Any, typing.Any]",
)


class CancelProcessingError(Exception):
    """Exception when raise showing what we should cancel processing."""

    def __init__(self, reason: str) -> None:
        super().__init__()
        self.reason = reason


class Processor(
    typing.Generic[
        schemas.QueueBodySchemaT,
        messages.MessageActionT,
    ],
):
    """Process messages that came from queue."""

    for_type: str
    registry: typing.ClassVar[
        dict[
            str,
            "Processor[typing.Any, typing.Any]",
        ]
    ] = {}

    def init_other(
        self,
        event_processor_class: type[ProcessorT],
    ) -> ProcessorT:
        """Init other processor from current."""
        return event_processor_class()

    def __init_subclass__(
        cls,
        for_type: str | None = None,
        **kwargs,
    ) -> None:
        """Register subclass' `for_type` in registry.

        Usage:
            ```python
            class ModelProcessor(
                Processor,
                for_type="some_type",
            ):
                ...
            ```

        """
        super().__init_subclass__(**kwargs)
        if not for_type:
            return
        if for_type in cls.registry:
            raise KeyError(f"{for_type} is already registered({cls})")
        cls.registry[for_type] = cls()
        cls.for_type = for_type

    @classmethod
    def get(
        cls,
        message_type: str,
    ) -> "Processor[typing.Any, typing.Any]":
        """Retrieve event processor from registry."""
        registry_key = message_type
        if event_processor := cls.registry.get(message_type):
            return event_processor
        raise KeyError(
            f"No event processors are registered for key {registry_key}",
        )

    @metrics.tracker
    async def __call__(
        self,
        message: messages.Message[
            schemas.QueueBodySchemaT,
            messages.MessageActionT,
        ],
        logger: logging.Logger,
    ) -> typing.Any:
        """Execute processor."""
        logger.info(
            f"Starting to process <{message.action}: "
            f"{self.for_type}> with processor {self.__class__}.",
        )
        logger.debug(
            "Body:\n" f"{message.serialize_body()}\n",
        )
        try:
            action = getattr(self, message.action, None)
            if not action:
                raise CancelProcessingError(
                    f"No method defined for {message.action} action",
                )
            async with self.prepare_context(message) as context:
                result = await action(
                    message=message,
                    logger=logger,
                    **context,
                )
        except CancelProcessingError as skip_exception:
            logger.info(f"Cancelled, reason: {skip_exception.reason}")
            return
        logger.info(
            f"Finished to process <{message.action}: "
            f"{self.for_type}> with processor {self.__class__}.",
        )
        logger.debug(
            "Body:\n" f"{message.serialize_body()}\n",
        )
        return result

    @contextlib.asynccontextmanager
    @metrics.tracker
    async def prepare_context(
        self,
        message: messages.Message[
            schemas.QueueBodySchemaT,
            messages.MessageActionT,
        ],
    ) -> collections.abc.AsyncIterator[dict[str, typing.Any]]:
        """Prepare context for event processor."""
        yield {}
