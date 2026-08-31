# PYTHON_ARGCOMPLETE_OK
import argparse
import asyncio
import logging
import sys

import aiohttp

from hascripts.cli import (
    setup_logging_and_parse_args,
    setup_signals,
)


async def main_async_task(
    address: str,
    logger: logging.Logger,
) -> bool:
    ratelimit: int = 60
    timeout: int = 10
    delay = ratelimit // timeout
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.post(
                    address,
                    data={},
                ) as resp:
                    logger.log(logging.INFO, f"request result: {resp.status}")
                    for line in (await resp.text()).splitlines():
                        logger.log(logging.INFO, line)
            except aiohttp.ClientConnectorError as exc:
                logger.log(
                    logging.CRITICAL,
                    "request error",
                    exc_info=exc,
                )
                return False

            for i in range(delay):
                logger.log(logging.INFO, f"next check in {ratelimit - i * timeout} s")
                try:
                    await asyncio.sleep(timeout)
                except asyncio.CancelledError as exc:
                    logger.log(
                        logging.CRITICAL,
                        "aborting",
                        exc_info=exc,
                    )
                    return True


async def main_async(
    address: str,
    logger: logging.Logger,
) -> bool:
    loop = asyncio.get_running_loop()
    task = asyncio.create_task(
        main_async_task(
            address,
            logger,
        )
    )
    with setup_signals(loop, lambda sig: task.cancel(f"abort via signal: {sig}")):
        pass

    return await task


def main():
    argsp = argparse.ArgumentParser()
    argsp.add_argument(
        "--address",
        default="http://localhost:8080",
    )
    with setup_logging_and_parse_args(argsp, "hascripts-sync") as (args, logger):
        pass
    result = asyncio.run(main_async(args.address, logger))
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
