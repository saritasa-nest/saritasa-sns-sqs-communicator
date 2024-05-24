import enum
import typing

import pydantic

from . import schemas

MessageActionT = typing.TypeVar(
    "MessageActionT",
    bound=enum.StrEnum,
)


class Message(
    pydantic.BaseModel,
    typing.Generic[schemas.QueueBodySchemaT, MessageActionT],
):
    """Queue message."""

    body_schema: schemas.QueueBodySchemaT
    action: MessageActionT
    type: str

    @property
    def metadata(self) -> dict[str, str]:
        """Get message metadata."""
        return {
            "action": self.action.value,
            "type": self.type,
        }

    def serialize_body(self) -> dict[str, typing.Any]:
        """Serialize message body."""
        return self.body_schema.model_dump(mode="json", by_alias=True)

    def to_dict(self) -> dict[str, typing.Any]:
        """Serialize message to dict."""
        return {
            "metadata": self.metadata,
            **self.serialize_body(),
        }


class DeadLetterMessage(pydantic.BaseModel):
    """Message for dead letter queue."""

    message_id: str
    receipt_handle: str
    raw_message: typing.Any
    error_details: str

    def to_dict(self) -> dict[str, typing.Any]:
        """Serialize message to dict."""
        return {
            "message_id": self.message_id,
            "receipt_handle": self.receipt_handle,
            "raw_message": self.raw_message,
            "exception_details": self.error_details,
        }
