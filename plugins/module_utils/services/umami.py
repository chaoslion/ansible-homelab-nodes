import typing

from ..models.net import NetworkAddress, NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    postgres: NetworkAddress
    redis: NetworkAddress
    secret: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/umami-software/umami",
            network={
                "http": NetworkTargetModel(
                    port=3000,
                ),
            },
        )

    @typing.override
    def customize(
        self,
    ):
        param_postgres = self._resolve_address("postgres")
        param_redis = self._resolve_address("redis")
        self._compose.common.environment.update(
            DATABASE_URL=f"postgresql://{self._group_variables_model.config.database.user}:{self._group_variables_model.config.database.password}@{param_postgres.address}/{self._group_variables_model.config.database.name}",
            REDIS_URL=f"redis://{param_redis.address}",
            APP_SECRET=self._params.secret,
            DISABLE_UPDATES="1",
            DISABLE_TELEMETRY="1",
            TRACKER_SCRIPT_NAME="go.js",
            COLLECT_API_ENDPOINT="/go",
        )
        self._compose.common.volumes.append(
            {
                "read_only": True,
                "source": "/etc/localtime",
                "target": "/etc/localtime",
                "type": "bind",
            },
        )

        super().customize()
