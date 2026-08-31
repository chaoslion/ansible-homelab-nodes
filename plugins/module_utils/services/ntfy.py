import typing

from ..models.net import NetworkTargetModel, NetworkUrl
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService, ServiceHelper


class ServiceParamsModel(NodeProjectServiceParamsModel):
    admin_token: str
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/binwiederhier/ntfy",
            network={
                "http": NetworkTargetModel(
                    port=80,
                ),
                "smtp": NetworkTargetModel(
                    port=25,
                ),
                "metrics": NetworkTargetModel(
                    port=9095,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "templates": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("templates"),
                    ),
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/ntfy",
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("data"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "attachment": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("attachment"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.extra.update(
            command=[
                "serve",
            ],
        )
        super().customize()
