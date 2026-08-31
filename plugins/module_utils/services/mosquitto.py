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
    persistence: bool = True


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/eclipse-mosquitto",
            upstream_tag="2.0.18-openssl",
            upstream_tag_force=True,
            network={
                "server": NetworkTargetModel(
                    port=1883,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/mosquitto/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/mosquitto/config",
                    ),
                },
                owner=1883,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.common.volumes.append(
            {
                "tmpfs": {
                    "size": "4M",
                },
                "target": "/mosquitto/log",
                "type": "tmpfs",
            },
        )
        # service.compose.compose.update(
        #     healthcheck={
        #         "test": "mosquitto_sub -t '$$SYS/broker/uptime' -C 1 -i healthcheck -W 3",
        #         "interval": "10s",
        #         "timeout": "5s",
        #         "retries": 2,
        #     },
        # )
        #
        super().customize()
