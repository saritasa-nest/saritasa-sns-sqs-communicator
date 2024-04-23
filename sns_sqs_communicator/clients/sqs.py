import collections.abc
import dataclasses
import functools
import typing

import anyio
import ujson

import boto3
import mypy_boto3_sqs.literals
import mypy_boto3_sqs.type_defs

from .. import metrics, types

ReturnT = typing.TypeVar("ReturnT")
ParamT = typing.ParamSpec("ParamT")


def get_boto3_sqs_client(
    access_key_getter: types.AccessKeyGetter,
    sqs_endpoint_url_getter: types.AWSEndpointUrlGetter | None = None,
    region: str | None = None,
) -> mypy_boto3_sqs.SQSClient:
    """Prepare boto3 sqs client for usage."""
    endpoint_url = None
    if sqs_endpoint_url_getter:
        endpoint_url = sqs_endpoint_url_getter()
    credentials = access_key_getter()
    return boto3.client(
        service_name="sqs",  # type: ignore
        region_name=region,
        aws_session_token=credentials.token,
        aws_access_key_id=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        endpoint_url=endpoint_url,
    )


@dataclasses.dataclass(frozen=True)
class SQSClient:
    """Client for interacting with SQS."""

    client: mypy_boto3_sqs.SQSClient
    default_queue_url: str = ""
    wait_time_seconds: int = 0

    async def run_sync_as_async(
        self,
        func: collections.abc.Callable[ParamT, ReturnT],
        *args: ParamT.args,
        **kwargs: ParamT.kwargs,
    ) -> ReturnT:
        """Make sync function run in async env."""
        return await anyio.to_thread.run_sync(  # type: ignore
            functools.partial(func, *args, **kwargs),
        )

    @metrics.tracker
    async def send_message(
        self,
        metadata_attributes: types.SQSMessageAttributes,
        body: dict[str, typing.Any],
        queue_url: str = "",
        **additional_attrs,
    ) -> mypy_boto3_sqs.type_defs.SendMessageResultTypeDef:
        """Send message to queue."""
        return await self.run_sync_as_async(
            self.client.send_message,
            QueueUrl=queue_url or self.default_queue_url,
            MessageAttributes=metadata_attributes,
            MessageBody=ujson.dumps(body),
            **additional_attrs,
        )

    @metrics.tracker
    async def receive_messages(
        self,
        queue_url: str = "",
        wait_time_seconds: int | None = None,
    ) -> mypy_boto3_sqs.type_defs.ReceiveMessageResultTypeDef:
        """Receive messages."""
        return await self.run_sync_as_async(
            self.client.receive_message,
            QueueUrl=queue_url or self.default_queue_url,
            MessageAttributeNames=["All"],
            WaitTimeSeconds=wait_time_seconds or self.wait_time_seconds,
        )

    @metrics.tracker
    async def delete_messages(
        self,
        messages_to_delete: collections.abc.Sequence[
            mypy_boto3_sqs.type_defs.MessageTypeDef
        ],
        queue_url: str = "",
    ) -> mypy_boto3_sqs.type_defs.DeleteMessageBatchResultTypeDef:
        """Delete messages from queue."""
        return await self.run_sync_as_async(
            self.client.delete_message_batch,
            QueueUrl=queue_url or self.default_queue_url,
            Entries=[
                {
                    "Id": str(idx),
                    "ReceiptHandle": message["ReceiptHandle"],
                }
                for idx, message in enumerate(messages_to_delete)
                if "ReceiptHandle" in message
            ],
        )

    @metrics.tracker
    async def create_queue(
        self,
        name: str,
        attributes: typing.Mapping[
            mypy_boto3_sqs.literals.QueueAttributeNameType,
            str,
        ]
        | None = None,
    ) -> mypy_boto3_sqs.type_defs.CreateQueueResultTypeDef:
        """Create queue."""
        return await self.run_sync_as_async(
            self.client.create_queue,
            QueueName=name,
            Attributes=attributes or {},
        )

    @metrics.tracker
    async def get_queue_url(
        self,
        name: str,
    ) -> str:
        """Get queue url."""
        return (
            await self.run_sync_as_async(
                self.client.get_queue_url,
                QueueName=name,
            )
        )["QueueUrl"]

    @metrics.tracker
    async def get_queue_arn(
        self,
        queue_url: str,
    ) -> str:
        """Get queue arn."""
        return (
            await self.run_sync_as_async(
                self.client.get_queue_attributes,
                QueueUrl=queue_url,
                AttributeNames=["QueueArn"],
            )
        )["Attributes"]["QueueArn"]

    @metrics.tracker
    async def delete_queue(
        self,
        queue_url: str,
    ) -> mypy_boto3_sqs.type_defs.EmptyResponseMetadataTypeDef:
        """Delete queue."""
        return await self.run_sync_as_async(
            self.client.delete_queue,
            QueueUrl=queue_url,
        )
