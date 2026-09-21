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
                owner=20211,
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
        self._compose.common.environment.update(
            PORT="20211",
        )
        self._compose.extra.update(
            read_only=True,
            tmpfs=[
                "/tmp:uid=20211,gid=20211,mode=1700,rw,noexec,nosuid,nodev,async,noatime,nodiratime",
            ],
            cap_drop=["ALL"],
            cap_add=[
                "NET_ADMIN",
                "NET_RAW",
                "NET_BIND_SERVICE",
                "CHOWN",
                "SETUID",
                "SETGID",
            ],
        )
        self._compose.common.volumes.append(
            {
                "source": "/etc/localtime",
                "target": "/etc/localtime",
                "type": "bind",
                "read_only": True,
            },
        )
        super().customize()
