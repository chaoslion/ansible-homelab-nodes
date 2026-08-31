import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsOpenIDModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    postgres: NetworkAddress
    openid: NodeProjectServiceParamsOpenIDModel
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/mealie-recipes/mealie",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=9000,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=911,
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/app/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_postgres = self._resolve_address("postgres")
        self._compose.common.environment.update(
            POSTGRES_DB=self._group_variables_model.config.database.name,
            POSTGRES_USER=self._group_variables_model.config.database.user,
            POSTGRES_PASSWORD=self._group_variables_model.config.database.password,
            BASE_URL=f"{self._params.url}",
            # ALLOW_PASSWORD_LOGIN="false",
            DB_ENGINE="postgres",
            POSTGRES_SERVER=f"{param_postgres.host}",
            POSTGRES_PORT=f"{param_postgres.port}",
            OIDC_AUTH_ENABLED="true",
            OIDC_CLIENT_ID=self._params.openid.client_id,
            OIDC_CLIENT_SECRET=self._params.openid.client_secret,
            OIDC_CONFIGURATION_URL=self._params.openid.url_well_known,
            OIDC_PROVIDER_NAME=self._params.openid.name,
        )
        super().customize()
