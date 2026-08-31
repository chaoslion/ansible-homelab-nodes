import typing

from ..models.net import (
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    apikey: str
    name: str
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/shlinkio/shlink-web-client",
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
        self._compose.common.environment.update(
            SHLINK_SERVER_NAME=self._params.name,
            SHLINK_SERVER_URL=f"{self._params.url}",
            SHLINK_SERVER_API_KEY=self._params.apikey,
        )
        super().customize()
