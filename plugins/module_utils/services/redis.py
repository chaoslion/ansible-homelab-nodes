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
            upstream="docker.io/redis",
            upstream_tag="8-alpine",
            upstream_tag_force=True,
            network={
                "server": NetworkTargetModel(
                    port=6379,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=999,
                group=1000,
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._enable_healthcheck(
            [
                "CMD-SHELL",
                "redis-cli ping | grep PONG",
            ],
        )
        self._compose.extra.update(
            command=[
                "redis-server",
                "--appendonly",
                "yes",
            ],
        )
        super().customize()
