import typing

from ..models.net import (
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsStorageVolume,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService, ServiceHelper


class ServiceParamsModel(NodeProjectServiceParamsModel):
    apps: NodeProjectServiceParamsStorageVolume


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/python",
            upstream_tag="3.13-slim",
            upstream_tag_force=True,
            network={
                "http": NetworkTargetModel(
                    port=9001,
                ),
                "apps": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "apps": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/local/lib/python3.13/site-packages/hascripts/apps",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(
                            param="apps"
                        ),
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("data"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/supervisor",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.common.environment.update(
            HASCRIPTS_DATA=self._spec_model.workspace.mounts["data"].target,
        )
        self._compose.extra.update(
            entrypoint=[
                "/usr/local/bin/supervisord",
                "-n",
                "-c",
                f"{self._spec_model.workspace.mounts['config'].target}/supervisord.conf",
            ],
        )

        self._compose.common.volumes.extend(
            [
                {
                    "tmpfs": {
                        "size": "16M",
                    },
                    "target": ServiceHelper.container_mount("supervisord-logs"),
                    "type": "tmpfs",
                },
                {
                    "tmpfs": {
                        "size": "8M",
                    },
                    "target": ServiceHelper.container_mount("supervisord-configs"),
                    "type": "tmpfs",
                },
            ],
        )
        super().customize()
