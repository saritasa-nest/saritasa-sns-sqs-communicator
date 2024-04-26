import collections.abc
import contextlib
import importlib
import pathlib
import sys
import typing

import typer

from . import local, sqs_poll_worker

app = typer.Typer()


@contextlib.contextmanager
def cwd_in_path() -> collections.abc.Generator[None | str, typing.Any, None]:
    """Context adding the current working directory to sys.path.

    Needed for importing, idea taken from celery.

    """
    try:
        cwd = pathlib.Path.cwd()
    except FileNotFoundError:
        cwd = None
    if not cwd or cwd in sys.path:
        yield None
    else:
        sys.path.insert(0, str(cwd))
        try:
            yield str(cwd)
        finally:
            with contextlib.suppress(ValueError):
                sys.path.remove(str(cwd))


@app.command()
def local_setup(
    manager_path: str = "sns_sqs_communicator.local.LocalSetupManager",
) -> None:
    """Set up sqs and sns locally.."""
    with cwd_in_path():
        *module, manager_class_name = manager_path.split(".")
        manager_class: local.LocalSetupManager = getattr(
            importlib.import_module(".".join(module)),
            manager_class_name,
        )
    manager_class.run()


@app.command()
def worker(
    worker_path: str,
    in_thread: bool = False,
    logging_level: str = "INFO",
) -> None:
    """Run message sqs poll worker."""
    with cwd_in_path():
        *module, worker_class_name = worker_path.split(".")
        worker_class: sqs_poll_worker.SQSPollWorker[typing.Any] = getattr(
            importlib.import_module(".".join(module)),
            worker_class_name,
        )
    worker_class.run_events_worker(
        in_thread=in_thread,
        logging_level=logging_level,
    )


app(prog_name="sns-sqs-communicator")
