import typing

from ..models.net import NetworkAddress, NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    proxy: NetworkAddress | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/homeassistant/home-assistant",
            network={
                "http": NetworkTargetModel(
                    port=8123,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/config",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "media": NodeProjectServiceWorkspaceMountModel(
                        target="/media",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        if self._params.proxy is not None:
            self._resolve_address("proxy")
        self._compose.common.volumes.append(
            {
                "read_only": True,
                "source": "/etc/localtime",
                "target": "/etc/localtime",
                "type": "bind",
            },
        )
        super().customize()
