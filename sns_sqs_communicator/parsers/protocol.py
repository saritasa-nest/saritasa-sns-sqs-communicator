import typing

from .. import messages, schemas


class ParserProtocol(
    typing.Protocol[messages.MessageActionT],
):
    """Protocol to implement parsing of sender format.

    This could be needed in case if different senders format messages
    differently. For example, SQS queue message format depends on how we sent
    it: directly from application or from SNS.

    """

    message_action_enum: type[messages.MessageActionT]

    @classmethod
    def parse(
        cls,
        raw_message: typing.Any,
    ) -> messages.Message[
        schemas.QueueBodySchema,
        messages.MessageActionT,
    ]:
        """Parse message."""
        ...

    @classmethod
    def get_raw_body(
        cls,
        raw_message: typing.Any,
    ) -> dict[str, typing.Any]:
        """Retrieve body from raw message."""
        ...
