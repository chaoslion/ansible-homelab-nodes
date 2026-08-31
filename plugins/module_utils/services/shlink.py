import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    domain: str
    path: str | None = None
    path_redirect: str | None = None
    postgres: NetworkAddress
    redis: NetworkAddress


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/shlinkio/shlink",
            add_timezone="TIMEZONE",
            network={
                "http": NetworkTargetModel(
                    port=8080,
                ),
            },
        )

    @typing.override
    def customize(
        self,
    ):
        param_redis = self._resolve_address("redis")
        param_postgres = self._resolve_address("postgres")
        env: dict[str, str] = {
            "DB_NAME": self._group_variables_model.config.database.name,
            "DB_USER": self._group_variables_model.config.database.user,
            "DB_PASSWORD": self._group_variables_model.config.database.password,
            "DB_DRIVER": "postgres",
            "DB_HOST": f"{param_postgres.host}",
            "DB_PORT": f"{param_postgres.port}",
            "DEFAULT_DOMAIN": self._params.domain,
            "IS_HTTPS_ENABLED": "true",
            "REDIS_PUB_SUB_ENABLED": "true",
            "REDIS_SERVERS": param_redis.address,
            "TRUSTED_PROXIES": "*",
        }
        if self._params.path is not None:
            env.update(BASE_PATH=self._params.path)
        if self._params.path_redirect is not None:
            env.update(DEFAULT_BASE_URL_REDIRECT=self._params.path_redirect)
        self._compose.common.environment.update(env)

        super().customize()
