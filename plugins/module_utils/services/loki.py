import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import (
    NodeProjectService,
    ServiceHelper,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    alertmanager: NetworkAddress
    prometheus: NetworkAddress
    retention: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/grafana/loki",
            network={
                "http": NetworkTargetModel(
                    port=3100,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/loki",
                    ),
                    "rules": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("rules"),
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/loki",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=10001,
                bump="restart",
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        _ = self._resolve_address("alertmanager")
        _ = self._resolve_address("prometheus")
        super().customize()
