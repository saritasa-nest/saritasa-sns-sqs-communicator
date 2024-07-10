import typing

import pydantic
import typing_extensions


class QueueBodySchemaNotRegisteredError(Exception):
    """Exception we're unable to find schema for type."""


class QueueBodySchema(pydantic.BaseModel):
    """Base schema for serialization message body for queue message."""

    model_config = pydantic.ConfigDict(
        from_attributes=True,
    )
    for_type: typing.ClassVar[str]
    registry: typing.ClassVar[dict[str, type["QueueBodySchema"]]] = {}

    def __init_subclass__(
        cls,
        for_type: str | None = None,
        **kwargs: typing_extensions.Unpack[pydantic.ConfigDict],
    ) -> None:
        """Register subclass' `for_type` in registry.

        Usage:
            ```python
            class SomeQueueBodySchema(
                BaseQueueBodySchema,
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
        cls.registry[for_type] = cls
        cls.for_type = for_type

    @classmethod
    def get_schema_by_message_type(
        cls,
        message_type: str,
    ) -> type["QueueBodySchema"]:
        """Retrieve schema for given message type from registry."""
        if schema := cls.registry.get(message_type):
            return schema
        raise QueueBodySchemaNotRegisteredError(
            f"Schema for message type {message_type} is not registered",
        )


QueueBodySchemaT = typing.TypeVar("QueueBodySchemaT", bound=QueueBodySchema)
