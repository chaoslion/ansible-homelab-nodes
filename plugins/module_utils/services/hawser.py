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
    server: NetworkAddress
    token: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/finsys/hawser",
            upstream_tag="0.2.35",
            upstream_tag_force=True,
            add_dockersocket=True,
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "stacks": NodeProjectServiceWorkspaceMountModel(
                        target="/data/stacks",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_server = self._resolve_address("server")
        self._compose.common.environment.update(
            DOCKHAND_SERVER_URL=f"ws://{param_server.address}/api/hawser/connect",
            TOKEN=self._params.token,
            SKIP_DF_COLLECTION="1",
        )
        super().customize()
