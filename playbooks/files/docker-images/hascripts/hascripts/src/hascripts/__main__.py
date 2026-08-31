# PYTHON_ARGCOMPLETE_OK
import argparse
import asyncio
import functools
import importlib
import logging
from typing import NamedTuple
import zoneinfo

import aiohttp
import aiohttp.web
import apscheduler.events
import apscheduler.schedulers.asyncio
import hass_client
import lmdb

import hascripts.apps
from hascripts.scanner import (
    AppsModuleInvalidException,
    AppSocket,
    AppsScanner,
    Config,
)
from hascripts.cli import (
    setup_logging_and_parse_args,
    setup_signals,
)
from hascripts.runner import AppAPI, AppParams, AppRunner, AppState


class RunnerFactory(NamedTuple):
    database: lmdb.Environment
    logger: logging.Logger
    fullname: str
    config: Config
    params: AppParams
    state: type[AppState]
    runner: type[AppRunner]


def runner_signals_healthcheck(runner: AppRunner, sig: int):
    runner.add_healthcheck(
        lambda: True,
        f"signal received {sig}",
    )


async def runner_main(
    factory: RunnerFactory,
):
    loop = asyncio.get_running_loop()
    async with aiohttp.ClientSession() as hass_session:
        api = AppAPI(
            factory.database,
            factory.logger,
            factory.fullname,
            factory.state,
            apscheduler.schedulers.asyncio.AsyncIOScheduler(),
            hass_client.HomeAssistantClient(
                f"{factory.config.hass.url}/api/websocket",
                factory.config.hass.token,
                hass_session,
            ),
            zoneinfo.ZoneInfo(factory.config.timezone),
        )

        runner = factory.runner(
            api,
            factory.params,
        )

        http_app = aiohttp.web.Application(
            middlewares=runner.setup_http_middlewares(),
        )

        runner.setup_http(http_app)

        http_runner = aiohttp.web.AppRunner(http_app)
        await http_runner.setup()

        app_socket = AppSocket(
            factory.fullname,
            factory.config.socket_path,
        )

        with app_socket.create_site(http_runner) as site:
            await site.start()
            api.scheduler.start()

            with setup_signals(
                loop, functools.partial(runner_signals_healthcheck, runner)
            ):
                pass

            await runner.heartbeat()

            api.scheduler.shutdown()
            await http_runner.cleanup()


def main():
    argsp = argparse.ArgumentParser()
    apps_argsp = argsp.add_subparsers(dest="module", required=True)

    apps_scanner = AppsScanner(hascripts.apps)
    apps_module_packages: dict[str, str] = {}
    for app_module_info in apps_scanner.scan():
        try:
            app_module_info.parse()
        except AppsModuleInvalidException:
            continue
        apps_module_packages.update(
            {
                app_module_info.name: app_module_info.package,
            }
        )

    for apps_module, config_apps in apps_scanner.cache.items():
        app_argsp = apps_argsp.add_parser(apps_module)
        app_argsp.add_argument("name", choices=list(config_apps.apps))

    with setup_logging_and_parse_args(argsp, "hascripts") as (
        args,
        runner_logger,
    ):
        runner_fullname = f"{args.module}-{args.name}"

    app_config = apps_scanner.cache[args.module]
    app_module = importlib.import_module(
        apps_module_packages[args.module],
    )

    app_params_factory: type[AppParams] = getattr(app_module, "Params")
    app_params = app_params_factory.model_validate(
        app_config.apps[args.name],
    )

    with lmdb.open(
        str(apps_scanner.data / f"data-{runner_fullname}"), map_size=10**8
    ) as lmdb_env:
        asyncio.run(
            runner_main(
                RunnerFactory(
                    lmdb_env,
                    runner_logger,
                    runner_fullname,
                    apps_scanner.config,
                    app_params,
                    getattr(app_module, "State"),
                    getattr(app_module, "Runner"),
                ),
            ),
        )


if __name__ == "__main__":
    main()
