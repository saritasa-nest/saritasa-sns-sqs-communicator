import collections
import collections.abc
import contextlib
import enum
import logging
import typing

import pydantic

import mypy_boto3_sqs.type_defs

from .. import messages, metrics, parsers, schemas

ProcessorT = typing.TypeVar(
    "ProcessorT",
    bound="Processor[typing.Any, typing.Any]",
)


class CancelProcessingError(Exception):
    """Exception when raise showing what we should cancel processing."""

    def __init__(self, reason: str) -> None:
        super().__init__()
        self.reason = reason


class ProcessingResultStatus(enum.StrEnum):
    """Define status for result of processing."""

    success = "success"
    failed = "failed"
    canceled = "cancelled"


ProcessingResultReturnT = typing.TypeVar(
    "ProcessingResultReturnT",
    bound=typing.Any,
)


class ProcessingResult(
    pydantic.BaseModel,
    typing.Generic[ProcessingResultReturnT],
):
    """Representation of processing result."""

    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )

    status: ProcessingResultStatus
    result: ProcessingResultReturnT
    message: str
    exception: Exception | None = None

    @property
    def is_ok(self) -> bool:
        """Check if ok."""
        return self.status == ProcessingResultStatus.success

    @property
    def is_canceled(self) -> bool:
        """Check if canceled."""
        return self.status == ProcessingResultStatus.canceled

    @property
    def is_failed(self) -> bool:
        """Check if canceled."""
        return self.status == ProcessingResultStatus.failed

    def raise_on_failure(self) -> None:
        """Raise error on fail."""
        if self.is_ok or self.is_canceled:
            return
        self.raise_on_exception()

    def raise_on_canceled(self) -> None:
        """Raise error on fail."""
        if self.is_ok or self.is_failed:
            return
        self.raise_on_exception()

    def raise_on_exception(self) -> None:
        """Raise error if present."""
        if not self.exception:
            return
        raise self.exception


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
    @metrics.tracker
    async def process(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
        parser: type[parsers.ParserProtocol[messages.MessageActionT]],
        logger: logging.Logger,
    ) -> ProcessingResult[typing.Any]:
        """Process raw message."""
        try:
            message = parser.parse(raw_message)
        except schemas.QueueBodySchemaNotRegisteredError as not_found_error:
            logger.info(f"Cancelled, reason: {not_found_error!s}")
            return ProcessingResult[typing.Any](
                status=ProcessingResultStatus.canceled,
                message=str(not_found_error),
                result=None,
                exception=not_found_error,
            )
        processor = cls.get(message_type=message.type)
        return await processor(
            message=message,
            logger=logger,
        )

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
    ) -> ProcessingResult[typing.Any]:
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
        except CancelProcessingError as cancel_exception:
            logger.info(f"Cancelled, reason: {cancel_exception.reason}")
            return ProcessingResult[typing.Any](
                status=ProcessingResultStatus.canceled,
                message=cancel_exception.reason,
                result=None,
                exception=cancel_exception,
            )
        logger.info(
            f"Finished to process <{message.action}: "
            f"{self.for_type}> with processor {self.__class__}.",
        )
        logger.debug(
            "Body:\n" f"{message.serialize_body()}\n",
        )
        return ProcessingResult[typing.Any](
            status=ProcessingResultStatus.success,
            message="",
            result=result,
            exception=None,
        )

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
