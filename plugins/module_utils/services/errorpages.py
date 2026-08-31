import typing

from ..models.net import NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
)
from . import (
    NodeProjectService,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    template: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/tarampampam/error-pages",
            upstream_tag="4.2.4",
            upstream_tag_force=True,
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
            TEMPLATE_NAME=self._params.template,
        )

        super().customize()
