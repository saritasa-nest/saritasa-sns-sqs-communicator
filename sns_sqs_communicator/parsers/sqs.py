import typing

import ujson

import mypy_boto3_sqs.type_defs

from .. import messages, metrics, schemas
from . import protocol


class SQSParser(
    protocol.ParserProtocol[messages.MessageActionT],
    typing.Generic[messages.MessageActionT],
):
    """Parser for SQS messages sent by service directly."""

    @classmethod
    @metrics.tracker
    def parse(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
    ) -> messages.Message[
        schemas.QueueBodySchema,
        messages.MessageActionT,
    ]:
        """Parse message."""
        parsed_body: dict[str, typing.Any] = cls.get_raw_body(raw_message)
        message_type = cls.get_message_attribute_value(raw_message, "type")
        schema_class = schemas.QueueBodySchema.get_schema_by_message_type(
            message_type=message_type,
        )
        return messages.Message(
            body_schema=schema_class(**parsed_body),
            action=cls.message_action_enum(  # type: ignore
                cls.get_message_attribute_value(raw_message, "action"),
            ),
            type=message_type,
        )

    @classmethod
    @metrics.tracker
    def get_raw_body(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
    ) -> typing.Any:
        """Retrieve body from raw message."""
        if not (body := raw_message.get("Body")):
            raise KeyError("No body has been found in message")

        return ujson.loads(body)

    @staticmethod
    @metrics.tracker
    def get_message_attribute_value(
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
        attr_name: str,
    ) -> str:
        """Retrieve message attribute value by name."""
        if not (message_attrs := raw_message.get("MessageAttributes")):
            raise KeyError("No message attributes has been found")

        if not (attr := message_attrs.get(attr_name)):
            raise KeyError(f"No {attr_name} found in message attributes")

        if not (attr_string_value := attr.get("StringValue")):
            raise ValueError(f"No StringValue is set for {attr_name}")

        return attr_string_value
