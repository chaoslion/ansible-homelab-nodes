import typing

from ..models.net import NetworkAddress, NetworkTargetModel, NetworkUrl
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
    key: str
    openid: NodeProjectServiceParamsOpenIDModel
    postgres: NetworkAddress
    url: NetworkUrl
    upload_limit: int


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/plankanban/planka",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=1337,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=1000,
                mounts={
                    "terms": NodeProjectServiceWorkspaceMountModel(
                        target="/app/terms/custom",
                    ),
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
            BASE_URL=f"{self._params.url}",
            DATABASE_URL=f"postgresql://{self._group_variables_model.config.database.user}:{self._group_variables_model.config.database.password}@{param_postgres.address}/{self._group_variables_model.config.database.name}",
            SECRET_KEY=self._params.key,
            MAX_UPLOAD_FILE_SIZE=f"{self._params.upload_limit}",
            TRUST_PROXY="true",
            DEFAULT_LANGUAGE="de-DE",
            DEFAULT_ADMIN_EMAIL=self._group_variables_model.config.admin.mail,
            DEFAULT_ADMIN_PASSWORD=self._group_variables_model.config.admin.password,
            DEFAULT_ADMIN_NAME=self._group_variables_model.config.admin.name,
            DEFAULT_ADMIN_USERNAME=self._group_variables_model.config.admin.name.lower(),
            OIDC_ISSUER=f"{self._params.openid.url}",
            OIDC_CLIENT_ID=self._params.openid.client_id,
            OIDC_CLIENT_SECRET=self._params.openid.client_secret,
            OIDC_USE_OAUTH_CALLBACK="false",
            OIDC_SCOPES="openid email profile homelab_planka",
            OIDC_RESPONSE_MODE="fragment",
            OIDC_USE_DEFAULT_RESPONSE_MODE="false",
            OIDC_ADMIN_ROLES="planka-admin",
            OIDC_PROJECT_OWNER_ROLES="planka-project-owner",
            OIDC_BOARD_USER_ROLES="planka-board-user",
            OIDC_CLAIMS_SOURCE="userinfo",
            OIDC_ROLES_ATTRIBUTE="planka_groups",
            OIDC_IGNORE_ROLES="false",
        )

        super().customize()
