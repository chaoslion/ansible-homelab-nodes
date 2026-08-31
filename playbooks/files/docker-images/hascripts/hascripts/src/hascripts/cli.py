import asyncio
import functools
import logging
import signal
import sys
from argparse import ArgumentParser
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import argcomplete


@contextmanager
def setup_signals(loop: asyncio.AbstractEventLoop, callback: Callable[[int], Any]):
    signals = [
        signal.SIGINT,
        signal.SIGTERM,
    ]

    try:
        yield signals
    finally:
        for i in signals:
            loop.add_signal_handler(
                i,
                functools.partial(callback, i),
            )


@contextmanager
def setup_logging_and_parse_args(
    argsp: ArgumentParser,
    logger_name: str,
    level: str | None = None,
):
    logging_levels = logging.getLevelNamesMapping()
    argsp.add_argument(
        "--log-level",
        choices=logging_levels,
        default=level or "INFO",
    )
    argsp.add_argument(
        "--log-level-global",
        choices=logging_levels,
        default="WARN",
    )

    logging_handler_main = logging.StreamHandler(sys.stdout)
    logging_handler_main.addFilter(
        lambda i: i.levelno <= logging.INFO,
    )
    logging_handler_errors = logging.StreamHandler(sys.stderr)
    logging_handler_errors.addFilter(
        lambda i: i.levelno > logging.INFO,
    )

    argcomplete.autocomplete(argsp)
    args = argsp.parse_args()

    logging.basicConfig(
        level=args.log_level_global,
        handlers=[
            logging_handler_main,
            logging_handler_errors,
        ],
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname).3s %(message)s",
    )
    logger = logging.getLogger(logger_name)
    logger.setLevel(args.log_level)

    try:
        yield args, logger
    finally:
        logger.log(logging.INFO, "starting")
