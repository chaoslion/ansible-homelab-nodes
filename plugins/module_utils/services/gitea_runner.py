import typing

from ..models.net import (
    NetworkAddress,
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
    instance: NetworkAddress
    token: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/gitea/act_runner",
            upstream_tag="latest",
            upstream_tag_force=True,
            workspace=NodeProjectServiceWorkspaceModel(
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
        param_instance = self._resolve_address("instance")
        self._compose.common.volumes.append(
            {
                "source": "/var/run/docker.sock",
                "target": "/var/run/docker.sock",
                "type": "bind",
            },
        )
        self._compose.common.environment.update(
            GITEA_INSTANCE_URL=f"http://{param_instance.address}",
            GITEA_RUNNER_REGISTRATION_TOKEN=self._params.token,
            GITEA_RUNNER_NAME="homelab",
        )
        super().customize()
