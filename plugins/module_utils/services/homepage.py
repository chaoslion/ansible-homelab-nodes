import typing

from ..models.net import (
    NetworkTargetModel,
    WebsiteGroupNames,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import (
    NodeProjectService,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    domain: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/gethomepage/homepage",
            network={
                "http": NetworkTargetModel(
                    port=3000,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/app/config",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._params_extra.update({"groups": [e.value for e in WebsiteGroupNames]})
        self._compose.common.environment.update(
            LOG_TARGETS="stdout",
            HOMEPAGE_ALLOWED_HOSTS="*",
        )
        super().customize()
