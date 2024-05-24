import sns_sqs_communicator

from . import messages


class SQSParser(
    sns_sqs_communicator.parsers.SQSParser[messages.MessageAction],
):
    """Implement SQSParser."""

    message_action_enum = messages.MessageAction


class SNSParser(
    sns_sqs_communicator.parsers.SNSParser[messages.MessageAction],
):
    """Implement SNSParser."""

    message_action_enum = messages.MessageAction
