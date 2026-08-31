import typing

from ..models.net import (
    NetworkAddress,
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
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    mqtt: NetworkAddress
    shm_mb: str
    storage: NodeProjectServiceParamsStorageVolume


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/blakeblackshear/frigate",
            network={
                "restream": NetworkTargetModel(
                    port=8554,
                ),
                "rtc": NetworkTargetModel(
                    port=8555,
                    mode="tcp+udp",
                ),
                "https": NetworkTargetModel(
                    port=8971,
                ),
                "http": NetworkTargetModel(
                    port=5000,
                ),
                "http-go2rtc": NetworkTargetModel(
                    port=1984,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "media": NodeProjectServiceWorkspaceMountModel(
                        target="/media/frigate",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(
                            param="storage",
                        ),
                    ),
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/config",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._resolve_address("mqtt")
        self._compose.common.volumes.extend(
            [
                {
                    "read_only": True,
                    "source": "/etc/localtime",
                    "target": "/etc/localtime",
                    "type": "bind",
                },
                # {
                #     "source": self._params["storage"],
                #     "target": "/media/frigate",
                #     "type": "bind",
                # },
                {
                    "target": "/tmp/cache",
                    "tmpfs": {
                        "size": "1GB",
                    },
                    "type": "tmpfs",
                },
            ],
        )

        self._compose.extra.update(
            mem_swappiness=0,
            memswap_limit=f"{self._config_node_project_service_model.limits.memory}m",
            devices=["/dev/dri/renderD128"],
            privileged=True,
            shm_size=f"{self._params.shm_mb}mb",
            stop_grace_period="30s",
        )
        super().customize()
