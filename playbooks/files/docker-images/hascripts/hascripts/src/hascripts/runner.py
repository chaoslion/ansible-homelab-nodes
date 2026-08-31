import asyncio
import datetime
import logging
import zoneinfo
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, NamedTuple, TypeAlias

import aiohttp.web
import apscheduler.events
import apscheduler.schedulers.asyncio
import hass_client
import lmdb
import pydantic
from attr import dataclass

from hascripts.scanner import AppParamsRaw
from hascripts.validate import ConfigModel

AppHealthCheckCall: TypeAlias = Callable[[], bool]
AppPersistentStateRaw: TypeAlias = dict[str, Any]
AppStateRaw: TypeAlias = dict[str, Any]
AppStateContext: TypeAlias = dict[str, Any]
HttpStateConfig: TypeAlias = dict[str, Any]


class AppHealthCheck(NamedTuple):
    check: AppHealthCheckCall
    reason: str


class AppParams(ConfigModel):
    pass


class AppState(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        extra="forbid",
        serialize_by_alias=True,
    )


@dataclass(frozen=True)
class AppAPI[T: AppState]:
    database: lmdb.Environment
    logger: logging.Logger
    name: str
    state_factory: type[T]
    scheduler: apscheduler.schedulers.asyncio.AsyncIOScheduler
    hass: hass_client.HomeAssistantClient
    timezone: zoneinfo.ZoneInfo

    DATABASE_STATE_KEY: bytes = b"STATE"

    @property
    def now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=self.timezone)

    @property
    def today_min(self) -> datetime.datetime:
        return datetime.datetime.combine(
            self.now,
            datetime.time.min,
            tzinfo=self.timezone,
        )

    @property
    def today_max(self) -> datetime.datetime:
        return datetime.datetime.combine(
            self.now,
            datetime.time.max,
            tzinfo=self.timezone,
        )

    def state_init(self, initial: AppStateRaw, context: AppStateContext) -> T:
        return self.state_factory.model_validate(
            initial,
            context=context,
        )

    def state_store(self, state: T):
        blob: bytes = state.model_dump_json().encode()
        with self.database.begin(write=True) as txn:
            txn.put(self.DATABASE_STATE_KEY, blob)

    def state_restore(self, context: AppStateContext) -> T | None:
        with self.database.begin() as txn:
            blob: bytes | None = txn.get(self.DATABASE_STATE_KEY)
        return (
            None
            if blob is None
            else self.state_factory.model_validate_json(
                blob.decode(),
                context=context,
            )
        )


class IAppRunner(ABC):
    @abstractmethod
    def log(self, *args): ...

    @abstractmethod
    def log_debug(self, *args): ...

    @abstractmethod
    def log_error(self, *args): ...

    @abstractmethod
    def log_critical(self, *args, exc): ...


class AppRunner[T: AppParams, K: AppState](IAppRunner):
    HEALTHCHECK_INTERVAL: int = 1

    def __init__(
        self,
        api: AppAPI[K],
        params: T,
    ):
        self.api = api
        self.state: K = api.state_init(self.state_initial(), {})
        self.state_lock = asyncio.Lock()
        self.params: T = params
        self._uptime = 0
        self._healthchecks: list[AppHealthCheck] = []
        # self.api.scheduler.add_listener(
        #     self._api_scheduler_listener,
        #     apscheduler.events.EVENT_JOB_ERROR | apscheduler.events.EVENT_JOB_EXECUTED,
        # )
        self.log_debug("init params", self.params)
        self.log_debug("init state", self.state)

    # def _api_scheduler_listener(self, event: apscheduler.events.JobExecutionEvent):
    #     if event.exception is not None:
    #         self.log_critical(
    #             "scheduler exception",
    #             event.job_id,
    #             exc=event.exception,
    #         )
    #     else:
    #         self.log_debug("scheduler event", event.job_id, event.code)

    def state_initial(self) -> AppParamsRaw:
        return {}

    async def state_store(self):
        async with self.state_lock:
            await asyncio.to_thread(
                self.api.state_store,
                self.state,
            )

    async def state_restore(self, context: AppStateContext | None = None):
        if context is None:
            context = {}
        async with self.state_lock:
            result: K | None = await asyncio.to_thread(
                self.api.state_restore,
                context,
            )
            if result is not None:
                self.state = result

    def add_healthcheck(self, check: AppHealthCheckCall, reason: str):
        if reason in map(lambda i: i.reason, self._healthchecks):
            self.log("ignore duplicated healthcheck reason", reason)
            return
        self._healthchecks.append(
            AppHealthCheck(check, reason),
        )

    def log(self, *args):
        self.api.logger.log(logging.INFO, ", ".join(map(str, list(args))))

    def log_debug(self, *args):
        self.api.logger.log(logging.DEBUG, ", ".join(map(str, list(args))))

    def log_error(self, *args):
        self.api.logger.log(logging.ERROR, ", ".join(map(str, list(args))))

    def log_critical(self, *args, exc: BaseException):
        self.api.logger.log(
            logging.CRITICAL,
            ", ".join(map(str, list(args))),
            exc_info=exc,
        )

    async def heartbeat(self):
        await self.setup()
        while True:
            self.log_debug("heartbeat", self._uptime)
            if self._healthchecks:
                unhealthy = list(filter(lambda i: i.check(), self._healthchecks))
                for i in unhealthy:
                    self.log_error("unhealthy abort", i.reason)
                if unhealthy:
                    break

            self._uptime += self.HEALTHCHECK_INTERVAL
            await asyncio.sleep(self.HEALTHCHECK_INTERVAL)

    def setup_http_middlewares(self):
        return []

    def http_handler_state_config(self) -> HttpStateConfig:
        return {}

    async def http_handler_state(self, request):
        async with self.state_lock:
            return aiohttp.web.Response(
                text=self.state.model_dump_json(**self.http_handler_state_config()),
                content_type="application/json",
            )

    async def http_handler_health(self, request):
        return aiohttp.web.json_response({"uptime": self._uptime})

    def setup_http(self, http: aiohttp.web.Application):
        http.add_routes(
            [
                aiohttp.web.get(
                    "/",
                    self.http_handler_state,
                ),
                aiohttp.web.get(
                    "/health",
                    self.http_handler_health,
                ),
            ],
        )

    async def setup(self):
        raise NotImplementedError


class AppRunnerHass[T: AppParams, K: AppState](AppRunner[T, K]):
    async def heartbeat(self):
        async with self.api.hass:
            self.add_healthcheck(
                lambda: not self.api.hass.connected,
                "homeassistant disconnected",
            )
            self.log("homeassistant connected", self.api.hass.version)
            await super().heartbeat()
