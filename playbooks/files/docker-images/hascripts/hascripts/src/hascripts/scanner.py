import asyncio
import contextlib
import functools
import importlib.resources
import io
import logging
import os
import pkgutil
import signal
import sys
from argparse import ArgumentParser
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any, NamedTuple, TypeAlias

import aiohttp.web
import argcomplete
from attr import dataclass
import pydantic
import yaml

from hascripts.validate import ConfigModel

AppParamsRaw: TypeAlias = dict[str, Any]


def _params_check_logging_level(value: str) -> str:
    if value not in list(logging.getLevelNamesMapping()):
        raise ValueError("invalid level")
    return value


class ConfigApps(ConfigModel):
    apps: dict[str, AppParamsRaw] = {}
    hidden: bool = False
    log_level: Annotated[
        str | None,
        pydantic.AfterValidator(_params_check_logging_level),
    ] = None
    log_level_global: Annotated[
        str | None,
        pydantic.AfterValidator(_params_check_logging_level),
    ] = None


class ConfigHass(ConfigModel):
    url: str
    token: str


class ConfigSupervisor(ConfigModel):
    path: Path
    # 200 retry for ~ 5.5 hrs
    startretries: int = 200
    startsecs: int = 5

    @pydantic.computed_field
    @property
    def sync(self) -> Path:
        return self.path / "sync"

    @pydantic.computed_field
    @property
    def sync_last(self) -> Path:
        return self.path / "sync-last"


class Config(ConfigModel):
    hass: ConfigHass
    redirect_stderr: bool = True
    supervisor: ConfigSupervisor
    shared: dict[str, Any] = {}
    socket_path: Path = Path(
        os.environ.get(
            "XDG_RUNTIME_DIR",
            "/run",
        ),
    )
    timezone: str = "Europe/Berlin"


class AppSocket(NamedTuple):
    name: str
    root_path: Path

    @staticmethod
    def get_prefix() -> str:
        return "hascripts"

    @property
    def path(self) -> Path:
        return (self.root_path / f"{AppSocket.get_prefix()}-{self.name}").with_suffix(
            ".sock"
        )

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @contextlib.contextmanager
    def create_site(self, runner):
        site = aiohttp.web.UnixSite(
            runner,
            self.path,
        )
        try:
            yield site
        finally:
            self.path.unlink(missing_ok=True)


@dataclass
class AppModuleInfo:
    name: str
    package: str
    config: Path
    config_apps: ConfigApps | None = None

    def parse(self) -> ConfigApps:
        with self.config.open("r") as fapp_config:
            try:
                app_config_raw = yaml.safe_load(fapp_config) or {}
            except yaml.YAMLError as exc:
                raise AppsModuleInvalidException(
                    f"unloadable config: {self.name}"
                ) from exc

        try:
            self.config_apps = ConfigApps(**app_config_raw)
        except pydantic.ValidationError as exc:
            raise AppsModuleValidationException(f"invalid config: {self.name}") from exc

        if self.config_apps.hidden or not self.config_apps.apps:
            raise AppsModuleHiddenException

        return self.config_apps


class AppsModuleInvalidException(RuntimeError):
    pass


class AppsModuleValidationException(AppsModuleInvalidException):
    pass


class AppsModuleHiddenException(AppsModuleInvalidException):
    pass


class AppsScanner:
    DATA_ENV_KEY = "HASCRIPTS_DATA"

    def __init__(self, module: ModuleType):
        self._apps_modules = module
        self._cache: dict[str, ConfigApps] = {}
        self._data = (
            Path(os.environ[self.DATA_ENV_KEY])
            if self.DATA_ENV_KEY in os.environ is not None
            else Path.cwd()
        )
        config_yaml = importlib.resources.files(module.__package__) / "config.yaml"
        config_content = yaml.safe_load(config_yaml.read_bytes()) or {}
        self._apps_config = Config(**config_content)

    @property
    def data(self) -> Path:
        return self._data

    @property
    def config(self) -> Config:
        return self._apps_config

    @property
    def cache(self) -> dict[str, ConfigApps]:
        return self._cache

    def scan(self) -> Generator[AppModuleInfo]:
        self._cache.clear()
        package_files = importlib.resources.files(self._apps_modules.__package__)
        for _, pkg_module, pkg_is_package in pkgutil.iter_modules(
            self._apps_modules.__path__
        ):
            if not pkg_is_package:
                continue
            app_module_package_name = f"hascripts.apps.{pkg_module}"
            app_module_config_path = package_files / pkg_module / "config.yaml"
            if not app_module_config_path.is_file():
                continue

            app_module_info = AppModuleInfo(
                pkg_module,
                app_module_package_name,
                Path(str(app_module_config_path)),
            )
            yield app_module_info

            if app_module_info.config_apps is not None:
                self._cache.update(
                    {
                        pkg_module: app_module_info.config_apps,
                    }
                )

    # def parse(
    #     self,
    #     info: AppModuleInfo,
    # ) -> ConfigApps:
    #     with info.config.open("r") as fapp_config:
    #         try:
    #             app_config_raw = yaml.safe_load(fapp_config) or {}
    #         except yaml.YAMLError as exc:
    #             raise AppsModuleInvalidException(
    #                 f"unloadable config: {info.name}"
    #             ) from exc
    #
    #     try:
    #         self._cache_configs.update(
    #             {
    #                 info.name: ConfigApps(**app_config_raw),
    #             },
    #         )
    #     except pydantic.ValidationError as exc:
    #         raise AppsModuleValidationException(f"invalid config: {info.name}") from exc
    #
    #     if (
    #         self._cache_configs[info.name].hidden
    #         or not self._cache_configs[info.name].apps
    #     ):
    #         raise AppsModuleHiddenException
    #
    #     return self._cache_configs[info.name]

    def supervisor_purge(
        self,
        clean: bool = False,
    ):
        for i in self._apps_config.supervisor.path.glob("*.conf"):
            i.unlink()
        if clean:
            self._apps_config.supervisor.sync.unlink(missing_ok=True)
            self._apps_config.supervisor.sync_last.unlink(missing_ok=True)

    def supervisor_write(
        self,
        app: str,
        config_app: ConfigApps,
    ) -> list[str]:
        result: list[str] = []
        config_path = (self._apps_config.supervisor.path / app).with_suffix(".conf")
        with io.open(config_path, "w") as fconfig:
            for app_name in config_app.apps:
                app_fullname = f"{app}-{app_name}"
                fconfig.write(f"[program:app-{app_fullname}]\n")
                runner_args = ["-mhascripts"]
                if config_app.log_level is not None:
                    runner_args.extend(
                        [
                            "--log-level",
                            config_app.log_level,
                        ]
                    )
                if config_app.log_level_global is not None:
                    runner_args.extend(
                        [
                            "--log-level-global",
                            config_app.log_level_global,
                        ]
                    )
                runner_args.extend(
                    [
                        app,
                        app_name,
                    ]
                )
                fconfig.write(
                    f"command=/usr/local/bin/python {' '.join(runner_args)}\n",
                )
                fconfig.write(
                    f"environment={self.DATA_ENV_KEY}={self._data},PYTHONDONTWRITEBYTECODE=1\n",
                )

                fconfig.write(
                    f"startretries={self._apps_config.supervisor.startretries}\n"
                )
                fconfig.write(f"startsecs={self._apps_config.supervisor.startsecs}\n")
                fconfig.write("stdout_logfile_maxbytes=1MB\n")
                fconfig.write("stdout_logfile_backups=0\n")
                if self._apps_config.redirect_stderr:
                    fconfig.write("redirect_stderr=true\n")
                else:
                    fconfig.write("stderr_logfile_maxbytes=1MB\n")
                    fconfig.write("stderr_logfile_backups=0\n")

                result.append(app_fullname)
        return result


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
