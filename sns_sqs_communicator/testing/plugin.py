import contextlib
import functools
import importlib
import typing

import pytest

import botocore.credentials
import mypy_boto3_sns
import mypy_boto3_sqs.literals

from .. import clients, fifo_attributes_creator, types
from .. import parsers as parsers_module
from .. import queue as queue_module
from .. import topic as topic_module
from . import shortcuts


def pytest_addoption(parser: pytest.Parser) -> None:
    """Set up cmd args and ini config."""
    parser.addini(
        "sns_sqs_access_key",
        "Access key for aws.",
    )
    parser.addini(
        "sns_sqs_secret_key",
        "Secret key for aws.",
    )
    parser.addini(
        "sns_sqs_endpoint_url",
        "Endpoint for aws.",
    )
    parser.addini(
        "sns_sqs_region",
        "Region for aws.",
    )
    parser.addini(
        "sqs_queue_name",
        "SQS queue name.",
        default="sns-sqs-communicator-queue",
    )
    parser.addini(
        "sqs_queue_class",
        "Path to queue class.",
        default="sns_sqs_communicator.queue.SQSQueue",
    )
    parser.addini(
        "sns_topic_name",
        "SNS topic name.",
        default="sns-sqs-communicator-topic",
    )
    parser.addini(
        "sns_topic_class",
        "Path to topic class.",
        default="sns_sqs_communicator.topic.SNSTopic",
    )
    parser.addini(
        "sqs_parser_class",
        "Path to parser class.",
    )
    parser.addini(
        "sns_parser_class",
        "Path to parser class.",
    )


@pytest.fixture(scope="session")
def sns_sqs_access_key_getter(
    request: pytest.FixtureRequest,
) -> types.AccessKeyGetter:
    """Set up cred getter."""
    if (
        access_key := request.config.inicfg.get(
            "sns_sqs_access_key",
            "",
        )
    ) and (
        secret_key := request.config.inicfg.get(
            "sns_sqs_secret_key",
            "",
        )
    ):
        return lambda: botocore.credentials.Credentials(
            access_key=str(access_key),
            secret_key=str(secret_key),
        )
    raise NotImplementedError(  # pragma: no cover
        "Please set up `sns_sqs_access_key_getter` fixture or "
        "set `sns_sqs_access_key` and `sns_sqs_secret_key` in `.ini` file.",
    )


@pytest.fixture(scope="session")
def sns_sqs_endpoint_url_getter(
    request: pytest.FixtureRequest,
) -> types.AWSEndpointUrlGetter | None:
    """Set up url getter."""
    if endpoint_url := request.config.inicfg.get(
        "sns_sqs_endpoint_url",
        "",
    ):
        return lambda: str(endpoint_url)
    return None  # pragma: no cover


@pytest.fixture(scope="session")
def sns_sqs_region(
    request: pytest.FixtureRequest,
) -> str:
    """Get region."""
    return str(request.config.inicfg.get("sns_sqs_region", ""))


@pytest.fixture(scope="session")
def boto3_sqs_client(
    sns_sqs_access_key_getter: types.AccessKeyGetter,
    sns_sqs_endpoint_url_getter: types.AWSEndpointUrlGetter | None,
    sns_sqs_region: str,
) -> mypy_boto3_sqs.SQSClient:
    """Prepare boto3 sqs client."""
    return clients.get_boto3_sqs_client(
        access_key_getter=sns_sqs_access_key_getter,
        sqs_endpoint_url_getter=sns_sqs_endpoint_url_getter,
        region=sns_sqs_region,
    )


@pytest.fixture(scope="session")
def boto3_sns_client(
    sns_sqs_access_key_getter: types.AccessKeyGetter,
    sns_sqs_endpoint_url_getter: types.AWSEndpointUrlGetter | None,
    sns_sqs_region: str,
) -> mypy_boto3_sns.SNSClient:
    """Prepare boto3 sns client."""
    return clients.get_boto3_sns_client(
        access_key_getter=sns_sqs_access_key_getter,
        sns_endpoint_url_getter=sns_sqs_endpoint_url_getter,
        region=sns_sqs_region,
    )


@pytest.fixture(scope="session")
def sqs_client(
    boto3_sqs_client: mypy_boto3_sqs.SQSClient,
) -> clients.SQSClient:
    """Set up sqs client."""
    return clients.SQSClient(client=boto3_sqs_client)


@pytest.fixture(scope="session")
def sns_client(
    boto3_sns_client: mypy_boto3_sns.SNSClient,
) -> clients.SNSClient:
    """Set up sns client."""
    return clients.SNSClient(client=boto3_sns_client)


@pytest.fixture(scope="session")
def factory_fifo_attrs_creator() -> (
    fifo_attributes_creator.FifoAttributesCreatorProtocol | None
):
    """Get fifo_attrs_creator for factory."""
    return None


@pytest.fixture(scope="session")
def factory_attributes() -> typing.Mapping[str, str] | None:
    """Get attributes for factory."""
    return None


@pytest.fixture(scope="session")
def sqs_queue_name(
    request: pytest.FixtureRequest,
) -> str:
    """Get queue name."""
    worker_input = getattr(
        request.config,
        "workerinput",
        {
            "workerid": "",
        },
    )
    return "-".join(
        (
            str(
                request.config.inicfg.get(
                    "sns_sqs_queue_name",
                    "sns-sqs-communicator-queue",
                ),
            ),
            worker_input["workerid"],
        ),
    )


@pytest.fixture(scope="session")
def sqs_queue_class(
    request: pytest.FixtureRequest,
) -> type[queue_module.SQSQueue]:
    """Get queue class for factory."""
    sns_sqs_queue_class = str(
        request.config.inicfg.get("sns_sqs_queue_class", ""),
    )
    if not sns_sqs_queue_class:
        return queue_module.SQSQueue
    *module, klass = sns_sqs_queue_class.split(".")
    return getattr(importlib.import_module(".".join(module)), klass)


@pytest.fixture(scope="session")
def sqs_queue_factory(
    sqs_client: clients.SQSClient,
    sqs_queue_name: str,
    sqs_queue_class: type[queue_module.SQSQueue],
    factory_fifo_attrs_creator: fifo_attributes_creator.FifoAttributesCreatorProtocol  # noqa: E501
    | None,
    factory_attributes: typing.Mapping[
        mypy_boto3_sqs.literals.QueueAttributeNameType,
        str,
    ]
    | None,
) -> functools.partial[
    contextlib._AsyncGeneratorContextManager[queue_module.SQSQueue]
]:
    """Get topic factory."""
    return functools.partial(
        shortcuts.queue_factory,
        name=sqs_queue_name,
        sqs_client=sqs_client,
        fifo_attrs_creator=factory_fifo_attrs_creator,
        attributes=factory_attributes,
        queue_class=sqs_queue_class,
    )


@pytest.fixture(scope="session")
async def setup_sqs_queue(
    sqs_queue_factory: functools.partial[
        contextlib._AsyncGeneratorContextManager[queue_module.SQSQueue]
    ],
) -> typing.AsyncGenerator[
    queue_module.SQSQueue,
    None,
]:
    """Create sqs_queue_module."""
    async with sqs_queue_factory() as queue:
        yield queue


@pytest.fixture
async def sqs_queue(
    setup_sqs_queue: queue_module.SQSQueue,
) -> typing.AsyncGenerator[queue_module.SQSQueue, None]:
    """Return events queue for testing.

    Receive all messages from queue on teardown after each test to avoid
    keeping messages between different tests.

    """
    yield setup_sqs_queue
    await setup_sqs_queue.receive_all()


@pytest.fixture(scope="session")
def sns_topic_name(
    request: pytest.FixtureRequest,
) -> str:
    """Get queue name."""
    worker_input = getattr(
        request.config,
        "workerinput",
        {
            "workerid": "",
        },
    )
    return "-".join(
        (
            str(
                request.config.inicfg.get(
                    "sns_sqs_topic_name",
                    "sns-sqs-communicator-topic",
                ),
            ),
            worker_input["workerid"],
        ),
    )


@pytest.fixture(scope="session")
def sns_topic_class(
    request: pytest.FixtureRequest,
) -> type[topic_module.SNSTopic]:
    """Get topic class for factory."""
    sns_sqs_topic_class = str(
        request.config.inicfg.get("sns_sqs_topic_class", ""),
    )
    if not sns_sqs_topic_class:
        return topic_module.SNSTopic
    *module, klass = sns_sqs_topic_class.split(".")
    return getattr(importlib.import_module(".".join(module)), klass)


@pytest.fixture(scope="session")
def sns_topic_factory(
    sqs_client: clients.SQSClient,
    sns_client: clients.SNSClient,
    sqs_queue_name: str,
    sns_topic_name: str,
    sns_topic_class: type[topic_module.SNSTopic],
    factory_fifo_attrs_creator: fifo_attributes_creator.FifoAttributesCreatorProtocol  # noqa: E501
    | None,
    factory_attributes: typing.Mapping[str, str] | None,
) -> functools.partial[
    contextlib._AsyncGeneratorContextManager[topic_module.SNSTopic]
]:
    """Get topic factory."""
    return functools.partial(
        shortcuts.topic_factory,
        name=sns_topic_name,
        queue_name=sqs_queue_name,
        sqs_client=sqs_client,
        sns_client=sns_client,
        topic_class=sns_topic_class,
        fifo_attrs_creator=factory_fifo_attrs_creator,
        attributes=factory_attributes,
    )


@pytest.fixture(scope="session")
async def sns_topic(
    setup_sqs_queue: queue_module.SQSQueue,
    sns_topic_factory: functools.partial[
        contextlib._AsyncGeneratorContextManager[topic_module.SNSTopic]
    ],
) -> typing.AsyncGenerator[topic_module.SNSTopic, None]:
    """Create sns_topic_module.

    On teardown clear sqs_queue_module.

    """
    async with sns_topic_factory() as topic:
        yield topic
        await setup_sqs_queue.receive_all()


@pytest.fixture(scope="session")
def sqs_parser(
    request: pytest.FixtureRequest,
) -> type[parsers_module.ParserProtocol[typing.Any]]:
    """Get parser for sqs messages."""
    sns_sqs_topic_class = str(
        request.config.inicfg.get("sqs_parser_class", ""),
    )
    if not sns_sqs_topic_class:
        raise NotImplementedError(  # pragma: no cover
            "Please set up `sqs_parser` fixture or "
            "set `sqs_parser_class` in `.ini` file.",
        )
    *module, klass = sns_sqs_topic_class.split(".")
    return getattr(importlib.import_module(".".join(module)), klass)


@pytest.fixture(scope="session")
def sns_parser(
    request: pytest.FixtureRequest,
) -> type[parsers_module.ParserProtocol[typing.Any]]:
    """Get topic class for factory."""
    sns_sqs_topic_class = str(
        request.config.inicfg.get("sns_parser_class", ""),
    )
    if not sns_sqs_topic_class:
        raise NotImplementedError(  # pragma: no cover
            "Please set up `sns_parser` fixture or "
            "set `sns_parser_class` in `.ini` file.",
        )
    *module, klass = sns_sqs_topic_class.split(".")
    return getattr(importlib.import_module(".".join(module)), klass)
