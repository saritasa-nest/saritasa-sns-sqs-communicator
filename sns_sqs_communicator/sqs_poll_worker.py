import asyncio
import logging
import threading
import traceback
import typing

import mypy_boto3_sqs.type_defs

from . import (
    clients,
    fifo_attributes_creator,
    messages,
    metrics,
    parsers,
    processing,
    queue,
)


class SQSPollWorker(
    typing.Protocol[messages.MessageActionT],
):
    """Worker that polls and processes new messages from remote queue."""

    queue_url: str
    dead_letter_queue_url: str
    fifo_attrs_creator: (
        type[fifo_attributes_creator.FifoAttributesCreatorProtocol] | None
    ) = None
    dead_letter_fifo_attrs_creator: (
        type[fifo_attributes_creator.FifoAttributesCreatorProtocol] | None
    ) = None
    logger_name: str = "sns_sqs_worker"
    logging_level: str = "INFO"
    queue_class: type[queue.SQSQueue]
    parser_class: type[parsers.ParserProtocol[messages.MessageActionT]]

    @classmethod
    def setup_sqs_client(cls) -> clients.SQSClient:
        """Set up sqs client."""
        ...

    @classmethod
    def get_fifo_attrs_creator(
        cls,
    ) -> fifo_attributes_creator.FifoAttributesCreatorProtocol | None:
        """Get fifo_attrs_creator class."""
        return cls.fifo_attrs_creator

    @classmethod
    def get_dead_letter_fifo_attrs_creator(
        cls,
    ) -> fifo_attributes_creator.FifoAttributesCreatorProtocol | None:
        """Get dead_letter_fifo_attrs_creator class."""
        return cls.dead_letter_fifo_attrs_creator

    @classmethod
    @metrics.tracker
    def setup_queue(
        cls,
        sqs_client: clients.SQSClient,
    ) -> queue.SQSQueue:
        """Set up queue."""
        return cls.queue_class(
            client=sqs_client,
            queue_url=cls.queue_url,
            fifo_attrs_creator=cls.get_fifo_attrs_creator(),
        )

    @classmethod
    @metrics.tracker
    def setup_dead_letter_queue(
        cls,
        sqs_client: clients.SQSClient,
    ) -> queue.SQSQueue:
        """Set up queue for dead letters."""
        return cls.queue_class(
            client=sqs_client,
            queue_url=cls.dead_letter_queue_url,
            fifo_attrs_creator=cls.get_dead_letter_fifo_attrs_creator(),
        )

    @classmethod
    @metrics.tracker
    def setup_parser(cls) -> parsers.ParserProtocol[messages.MessageActionT]:
        """Set up queue."""
        return cls.parser_class()  # type: ignore

    @classmethod
    @metrics.tracker
    def run_events_worker(
        cls,
        in_thread: bool = False,
        logging_level: str = "INFO",
    ) -> None:
        """Run events worker (in current or separate thread)."""
        cls.logging_level = logging_level
        if in_thread:
            worker_thread = threading.Thread(
                target=asyncio.run,
                args=(cls.run(),),
                daemon=True,
            )
            worker_thread.start()
        else:
            asyncio.run(cls.run())

    @classmethod
    @metrics.tracker
    def setup_logger(cls) -> logging.Logger:
        """Set up logger."""
        logger = logging.getLogger(cls.logger_name)
        handler = cls.setup_logger_handler()
        handler.setFormatter(cls.setup_logger_formatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, cls.logging_level))
        return logger

    @classmethod
    def setup_logger_handler(cls) -> logging.Handler:
        """Set up handler for logger."""
        handler = logging.StreamHandler()
        return handler

    @classmethod
    def setup_logger_formatter(cls) -> logging.Formatter:
        """Set up handler for logger."""
        return logging.Formatter()

    @classmethod
    async def run(cls) -> None:
        """Start infinite loop that handles event messages."""
        logger = cls.setup_logger()
        logger.info(f"{cls.__name__} started")
        while True:
            sqs_client = cls.setup_sqs_client()
            logger.info("Polling messages from queue")
            await cls.pull_messages(
                queue=cls.setup_queue(
                    sqs_client=sqs_client,
                ),
                dead_letter_queue=cls.setup_dead_letter_queue(
                    sqs_client=sqs_client,
                ),
                parser=cls.setup_parser(),
                logger=logger,
            )

    @classmethod
    @metrics.tracker
    async def pull_messages(
        cls,
        queue: queue.SQSQueue,
        dead_letter_queue: queue.SQSQueue,
        parser: parsers.ParserProtocol[messages.MessageActionT],
        logger: logging.Logger,
    ) -> None:
        """Pull for messages and process them."""
        async for raw_message in queue.receive():
            try:
                await cls.process_message(
                    raw_message=raw_message,
                    parser=parser,
                    logger=logger,
                )
            except Exception as error:
                await cls.handle_processing_error(
                    raw_message=raw_message,
                    error=error,
                    parser=parser,
                    dead_letter_queue=dead_letter_queue,
                    logger=logger,
                )

    @classmethod
    @metrics.tracker
    async def process_message(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
        parser: parsers.ParserProtocol[messages.MessageActionT],
        logger: logging.Logger,
    ) -> None:
        """Handle incoming message from queue."""
        message = parser.parse(raw_message)
        processor = await cls.get_processor(
            raw_message=raw_message,
            parser=parser,
        )
        await processor(
            message=message,
            logger=logger,
        )

    @classmethod
    @metrics.tracker
    async def get_processor(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
        parser: parsers.ParserProtocol[messages.MessageActionT],
    ) -> processing.Processor[typing.Any, typing.Any]:
        """Get matching processor for message."""
        message = parser.parse(raw_message)
        return processing.Processor.get(message.type)

    @classmethod
    @metrics.tracker
    async def handle_processing_error(
        cls,
        raw_message: mypy_boto3_sqs.type_defs.MessageTypeDef,
        error: Exception,
        parser: parsers.ParserProtocol[messages.MessageActionT],
        dead_letter_queue: queue.SQSQueue,
        logger: logging.Logger,
    ) -> None:
        """Handle error during message processing."""
        logger.error(
            f"Error during message processing: {error}\n"
            f"{traceback.format_exc()}",
        )
        failed_message = messages.DeadLetterMessage(
            message_id=raw_message.get("MessageId", ""),
            receipt_handle=raw_message.get("ReceiptHandle", ""),
            raw_message=parser.get_raw_body(
                raw_message=raw_message,
            ),
            error_details=traceback.format_exc(),
        )
        await dead_letter_queue.put(
            body=failed_message.to_dict(),
            metadata=failed_message.to_dict(),
        )
