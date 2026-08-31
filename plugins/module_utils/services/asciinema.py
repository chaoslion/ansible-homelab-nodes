import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
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
    postgres: NetworkAddress
    url: NetworkUrl
    secret: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/asciinema/asciinema-server",
            network={
                "http": NetworkTargetModel(
                    port=4000,
                ),
                "http-admin": NetworkTargetModel(
                    port=4002,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/asciinema",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        postgres = self._resolve_address("postgres")
        self._compose.common.environment.update(
            URL_HOST=self._params.url.host,
            URL_SCHEME=self._params.url.scheme,
            SECRET_KEY_BASE=self._params.secret,
            SIGN_UP_DISABLED="true",
            UPLOAD_AUTH_REQUIRED="true",
            DATABASE_URL=f"postgresql://homelab:homelab@{postgres.address}/homelab",
        )
        self._compose.extra.update(
            ulimits={
                "nofile": {
                    "soft": 1024,
                    "hard": 1024,
                }
            }
        )
        super().customize()
