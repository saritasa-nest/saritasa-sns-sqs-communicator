import typing

import ujson

import mypy_boto3_sqs.type_defs

from .. import messages, metrics, schemas
from . import protocol


class SNSParser(
    protocol.ParserProtocol[messages.MessageActionT],
    typing.Generic[messages.MessageActionT],
):
    """Parser for SQS messages sent by SNS."""

    @classmethod
    @metrics.tracker
    def parse(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
    ) -> messages.Message[
        schemas.QueueBodySchema,
        messages.MessageActionT,
    ]:
        """Deserialize message."""
        if not (body := raw_message.get("Body")):
            raise KeyError("No body has been found in message")

        # SNS wraps actual body into another one, but we need this outer body
        # to parse attributes from it.
        wrapping_sns_body: dict[str, typing.Any] = ujson.loads(body)
        message_type = cls.get_message_attribute_value(
            wrapping_sns_body,
            "type",
        )
        schema_class = schemas.QueueBodySchema.get_schema_by_message_type(
            message_type=message_type,
        )
        return messages.Message(
            body_schema=schema_class(
                **ujson.loads(cls.get_raw_body(raw_message)),
            ),
            action=cls.message_action_enum(  # type: ignore
                cls.get_message_attribute_value(
                    wrapping_sns_body,
                    "action",
                ),
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

        return ujson.loads(body)["Message"]

    @staticmethod
    @metrics.tracker
    def get_message_attribute_value(
        raw_message: dict[str, typing.Any],
        attr_name: str,
    ) -> str:
        """Retrieve message attribute value by name."""
        if not (message_attrs := raw_message.get("MessageAttributes")):
            raise KeyError("No message attributes has been found")

        if not (attr := message_attrs.get(attr_name)):
            raise KeyError(f"No {attr_name} found in message attributes")

        if not (attr_string_value := attr.get("Value")):
            raise ValueError(f"No Value is set for {attr_name}")

        return attr_string_value
