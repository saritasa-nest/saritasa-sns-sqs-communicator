import collections.abc
import dataclasses
import functools
import typing

import anyio
import ujson

import boto3
import mypy_boto3_sns.type_defs

from .. import types

ReturnT = typing.TypeVar("ReturnT")
ParamT = typing.ParamSpec("ParamT")


def get_boto3_sns_client(
    access_key_getter: types.AccessKeyGetter,
    sns_endpoint_url_getter: types.AWSEndpointUrlGetter | None = None,
    region: str | None = None,
) -> mypy_boto3_sns.SNSClient:
    """Prepare boto3 sns client for usage."""
    endpoint_url = None
    if sns_endpoint_url_getter:
        endpoint_url = sns_endpoint_url_getter()
    credentials = access_key_getter()
    return boto3.client(
        service_name="sns",  # type: ignore
        region_name=region,
        aws_session_token=credentials.token,
        aws_access_key_id=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        endpoint_url=endpoint_url,
    )


@dataclasses.dataclass(frozen=True)
class SNSClient:
    """Client for interacting with SNS."""

    client: mypy_boto3_sns.SNSClient
    default_topic_arn: str = ""

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

    async def publish(
        self,
        message_attributes: types.SNSMessageAttributes,
        body: dict[str, typing.Any],
        topic_arn: str = "",
        **additional_attrs,
    ) -> mypy_boto3_sns.type_defs.PublishResponseTypeDef:
        """Publish message in topic."""
        return await self.run_sync_as_async(
            self.client.publish,
            TopicArn=topic_arn or self.default_topic_arn,
            MessageAttributes=message_attributes,
            Message=ujson.dumps(body),
            **additional_attrs,
        )

    async def create_topic(
        self,
        name: str,
        attributes: typing.Mapping[str, str] | None = None,
    ) -> mypy_boto3_sns.type_defs.CreateTopicResponseTypeDef:
        """Create topic."""
        return await self.run_sync_as_async(
            self.client.create_topic,
            Name=name,
            Attributes=attributes or {},
        )

    async def subscribe(
        self,
        topic_arn: str,
        endpoint: str,
        protocol: str = "sqs",
    ) -> mypy_boto3_sns.type_defs.SubscribeResponseTypeDef:
        """Subscribe topic."""
        return await self.run_sync_as_async(
            self.client.subscribe,
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint,
        )

    async def delete_topic(
        self,
        topic_arn: str,
    ) -> mypy_boto3_sns.type_defs.EmptyResponseMetadataTypeDef:
        """Subscribe topic."""
        return await self.run_sync_as_async(
            self.client.delete_topic,
            TopicArn=topic_arn,
        )
