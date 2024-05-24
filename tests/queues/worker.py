import logging

import sns_sqs_communicator

from . import messages, parsers


class SQSPollWorker(
    sns_sqs_communicator.sqs_poll_worker.SQSPollWorker[messages.MessageAction],
):
    """Worker that polls and processes new messages from remote queue."""

    queue_url = ""
    dead_letter_queue_url = ""
    fifo_attrs_creator = (
        sns_sqs_communicator.fifo_attributes_creator.FifoAttributesCreator
    )
    dead_letter_fifo_attrs_creator = sns_sqs_communicator.fifo_attributes_creator.DeadLetterFifoAttributesCreator  # noqa: E501
    queue_class = sns_sqs_communicator.queue.SQSQueue
    parser_class = parsers.SNSParser

    @classmethod
    def setup_sqs_client(cls) -> sns_sqs_communicator.clients.SQSClient:
        """Set up sqs client."""
        raise NotImplementedError("Shouldn't be called")

    @classmethod
    def setup_logger_handler(cls) -> logging.Handler:
        """Set up rich handler."""
        raise NotImplementedError("Shouldn't be called")
