import typing

from ..models.net import (
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    pass


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/tphakala/birdnet-go",
            network={
                "http": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/config",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=1000,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.common.volumes.append(
            {
                "tmpfs": {
                    "size": "50M",
                    # "mode": "0755",
                },
                "target": "/config/hls",
                "type": "tmpfs",
            },
        )
        super().customize()
