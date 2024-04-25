import collections.abc
import typing

import botocore.credentials
import mypy_boto3_sns.type_defs
import mypy_boto3_sqs.type_defs

SQSMessageAttributes: typing.TypeAlias = collections.abc.Mapping[
    str,
    mypy_boto3_sqs.type_defs.MessageAttributeValueTypeDef,
]
SNSMessageAttributes: typing.TypeAlias = collections.abc.Mapping[
    str,
    mypy_boto3_sns.type_defs.MessageAttributeValueTypeDef,
]
AccessKeyGetter = collections.abc.Callable[
    [],
    botocore.credentials.Credentials,
]
AWSEndpointUrlGetter = collections.abc.Callable[
    [],
    str | None,
]
