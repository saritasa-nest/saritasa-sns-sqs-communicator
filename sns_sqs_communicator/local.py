import collections.abc
import logging
import pathlib
import tomllib
import typing

import pydantic
import ujson

import botocore.credentials
import mypy_boto3_sns.type_defs
import mypy_boto3_sqs.literals
import mypy_boto3_sqs.type_defs

import sns_sqs_communicator


class LocalSetupConfig(pydantic.BaseModel):
    """Configuration for local setup."""

    endpoint_url: str
    region: str
    access_key: str
    secret_key: str
    queue_attributes: collections.abc.Mapping[
        mypy_boto3_sqs.literals.QueueAttributeNameType,
        str,
    ] = {}
    queue_policy: dict[str, typing.Any] | None = None
    topic_attributes: collections.abc.Mapping[str, str] = {}
    queues_to_create: list[str] = []
    topics_to_create: list[str] = []
    topics_subscriptions: dict[str, collections.abc.Sequence[str]] = {}


class LocalSetupManager:
    """Utils to set up sns/sqs for local dev."""

    _config: LocalSetupConfig | None = None
    sqs_client: mypy_boto3_sqs.SQSClient
    sns_client: mypy_boto3_sns.SNSClient

    created_queues: typing.ClassVar[
        dict[str, mypy_boto3_sqs.type_defs.CreateQueueResultTypeDef]
    ] = {}
    created_topics: typing.ClassVar[
        dict[str, mypy_boto3_sns.type_defs.CreateTopicResponseTypeDef]
    ] = {}

    @classmethod
    def run(cls) -> None:
        """Run set up."""
        config = cls.get_config()
        logger = cls.get_logger()
        cls.sns_client = sns_sqs_communicator.clients.get_boto3_sns_client(
            access_key_getter=lambda: botocore.credentials.Credentials(
                access_key=config.access_key,
                secret_key=config.secret_key,
            ),
            sns_endpoint_url_getter=lambda: config.endpoint_url,
            region=config.region,
        )
        cls.sqs_client = sns_sqs_communicator.clients.get_boto3_sqs_client(
            access_key_getter=lambda: botocore.credentials.Credentials(
                access_key=config.access_key,
                secret_key=config.secret_key,
            ),
            sqs_endpoint_url_getter=lambda: config.endpoint_url,
            region=config.region,
        )
        logger.info("Creating queries")
        for queue_url in config.queues_to_create:
            cls.create_queue(queue_url=queue_url, logger=logger)
        logger.info("Creating topics")
        for topic_arn in config.topics_to_create:
            cls.create_topic(topic_arn=topic_arn, logger=logger)
        logger.info("Subscribing topics to queries")
        for topic_arn, queue_urls in config.topics_subscriptions.items():
            cls.subscribe_topic_to_queues(
                topic_arn=topic_arn,
                queues_urls=queue_urls,
                logger=logger,
            )

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Set up logger."""
        logger = logging.getLogger(__file__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    @classmethod
    def get_config(cls) -> LocalSetupConfig:
        """Get config."""
        if not cls._config:
            with pathlib.Path("pyproject.toml").open("rb") as file:
                cls._config = LocalSetupConfig(
                    **tomllib.load(file)["tool"]["sns-sqs-communicator"][
                        "local-setup"
                    ],
                )
        return cls._config

    @classmethod
    def get_queue_policy_statement(
        cls,
        queue_arn: str,
    ) -> dict[str, typing.Any] | None:
        """Create policy statement for queue."""
        queue_policy = cls.get_config().queue_policy
        if not queue_policy:
            return None
        return dict(Resource=queue_arn, **queue_policy)

    @classmethod
    def get_queue_attributes(
        cls,
    ) -> collections.abc.Mapping[
        mypy_boto3_sqs.literals.QueueAttributeNameType,
        str,
    ]:
        """Create policy statement for queue."""
        return cls.get_config().queue_attributes

    @classmethod
    def generate_queue_policy(
        cls,
        queue_arn: str,
        current_policy: dict[str, typing.Any] | None = None,
    ) -> dict[str, typing.Any]:
        """Generate policy with needed statement for queue."""
        current_policy = current_policy or {}
        statements: list[dict[str, typing.Any]] = current_policy.get(
            "Statement",
            [],
        )
        policy_statement = cls.get_queue_policy_statement(queue_arn)
        if policy_statement and policy_statement not in statements:
            statements.append(policy_statement)
        current_policy["Statement"] = statements
        return current_policy

    @classmethod
    def set_queue_policy(
        cls,
        queue_url: str,
    ) -> None:
        """Set queue policy."""
        events_queue_attrs = cls.sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["QueueArn", "Policy"],
        )
        events_queue_policy = cls.generate_queue_policy(
            queue_arn=events_queue_attrs["Attributes"]["QueueArn"],
            current_policy=ujson.loads(
                events_queue_attrs["Attributes"].get("Policy", "{}"),
            ),
        )
        cls.sqs_client.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={
                "Policy": ujson.dumps(events_queue_policy),
            },
        )

    @classmethod
    def create_queue(
        cls,
        queue_url: str,
        logger: logging.Logger,
    ) -> mypy_boto3_sqs.type_defs.CreateQueueResultTypeDef:
        """Create events queue."""
        logger.info(f"Creating {queue_url}")
        events_queue_response = cls.sqs_client.create_queue(
            QueueName=cls.get_queue_name_from_url(queue_url),
            Attributes=cls.get_queue_attributes(),
        )
        cls.set_queue_policy(
            queue_url=events_queue_response["QueueUrl"],
        )
        cls.created_queues[queue_url] = events_queue_response
        return events_queue_response

    @classmethod
    def get_topic_attributes(
        cls,
    ) -> collections.abc.Mapping[str, str]:
        """Create policy statement for queue."""
        return cls.get_config().topic_attributes

    @classmethod
    def create_topic(
        cls,
        topic_arn: str,
        logger: logging.Logger,
    ) -> mypy_boto3_sns.type_defs.CreateTopicResponseTypeDef:
        """Create topic."""
        logger.info(f"Creating {topic_arn}")
        response = cls.sns_client.create_topic(
            Name=cls.get_topic_name_from_arn(topic_arn=topic_arn),
            Attributes=cls.get_topic_attributes(),
        )
        cls.created_topics[topic_arn] = response
        return response

    @classmethod
    def subscribe_topic_to_queues(
        cls,
        topic_arn: str,
        queues_urls: collections.abc.Iterable[str],
        logger: logging.Logger,
    ) -> None:
        """Subscribe topic to queues."""
        for queue_url in queues_urls:
            logger.info(f"Subscribing {topic_arn} to {queue_url}")
            queue_arn = cls.sqs_client.get_queue_attributes(
                QueueUrl=cls.created_queues[queue_url]["QueueUrl"],
                AttributeNames=["QueueArn"],
            )["Attributes"]["QueueArn"]
            cls.sns_client.subscribe(
                TopicArn=cls.created_topics[topic_arn]["TopicArn"],
                Protocol="sqs",
                Endpoint=queue_arn,
            )

    @classmethod
    def get_queue_name_from_url(cls, queue_url: str) -> str:
        """Get queue name from url."""
        return queue_url.rsplit("/", maxsplit=1)[-1]

    @classmethod
    def get_topic_name_from_arn(cls, topic_arn: str) -> str:
        """Get topic name from arn."""
        return topic_arn.rsplit(":", maxsplit=1)[-1]
