import typing

from ..models.net import NetworkAddress, NetworkTargetModel, NetworkUrl, url_to_nice
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
    secret: str
    openid: NodeProjectServiceParamsOpenIDModel
    postgres: NetworkAddress
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/usekaneo/kaneo",
            network={
                "http": NetworkTargetModel(
                    port=5173,
                ),
            },
        )

    @typing.override
    def customize(
        self,
    ):
        param_postgres = self._resolve_address("postgres")
        self._compose.common.environment.update(
            KANEO_CLIENT_URL=url_to_nice(self._params.url),
            DATABASE_URL=f"postgresql://{self._group_variables_model.config.database.user}:{self._group_variables_model.config.database.password}@{param_postgres.address}/{self._group_variables_model.config.database.name}",
            AUTH_SECRET=self._params.secret,
            CUSTOM_OAUTH_DISCOVERY_URL=self._params.openid.url_well_known,
            CUSTOM_OAUTH_CLIENT_ID=self._params.openid.client_id,
            CUSTOM_OAUTH_CLIENT_SECRET=self._params.openid.client_secret,
            CUSTOM_OAUTH_SCOPES="profile,email,openid,groups",
            CUSTOM_AUTH_PKCE="true",
        )

        self._enable_healthcheck(
            [
                "CMD",
                "wget",
                "-Y",
                "off",
                "--quiet",
                "--spider",
                "http://127.0.0.1:5173/api/health",
            ],
            "30s",
            "60s",
        )

        super().customize()
