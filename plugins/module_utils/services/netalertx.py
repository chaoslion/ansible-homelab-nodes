import typing

from ..models.net import NetworkTargetModel
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
            upstream="ghcr.io/jokob-sk/netalertx",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=20211,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=102,
                group=82,
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/app/config",
                    ),
                    "db": NodeProjectServiceWorkspaceMountModel(
                        target="/app/db",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                        mode="0750",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.common.environment.update(
            PORT="20211",
        )
        self._compose.common.volumes.append(
            {
                "target": "/app/api",
                "tmpfs": {
                    "size": "16M",
                },
                "type": "tmpfs",
            },
        )
        super().customize()
