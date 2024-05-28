import enum

import sns_sqs_communicator


class MessageAction(enum.StrEnum):
    """List of all possible message actions."""

    plus = "plus"
    minus = "minus"
    do_something = "do_something"
    not_found_action = "not_found_action"
    fail = "fail"


Message = sns_sqs_communicator.messages.Message[
    sns_sqs_communicator.schemas.QueueBodySchemaT,
    MessageAction,
]
