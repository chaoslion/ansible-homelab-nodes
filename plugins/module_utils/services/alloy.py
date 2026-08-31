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
from . import NodeProjectService, ServiceHelper


class ServiceParamsModel(NodeProjectServiceParamsModel):
    loki: NetworkAddress


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/grafana/alloy",
            upstream_tag="v1.11.2",
            upstream_tag_force=True,
            network={
                "http": NetworkTargetModel(
                    port=12345,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/alloy/data",
                        mode="0770",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/alloy",
                    ),
                },
                owner=473,
                bump="reload",
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        _ = self._resolve_address("loki")
        self._compose.common.volumes.append(
            {
                "target": ServiceHelper.container_mount("journal"),
                "source": "/var/log/journal",
                "type": "bind",
                "read_only": True,
            },
        )
        self._compose.extra.update(
            command=[
                "run",
                "--disable-reporting=true",
                "--server.http.listen-addr=0.0.0.0:12345",
                "--storage.path=/var/lib/alloy/data",
                "/etc/alloy",
            ],
        )
        super().customize()
