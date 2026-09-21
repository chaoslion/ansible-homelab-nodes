import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
    url_to_nice,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsOpenIDModel,
    NodeProjectServiceScriptModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService, ServiceHelper


class ServiceParamsWorkspaceModel(NodeProjectServiceParamsModel):
    cpu: float
    memory: int


class ServiceParamsModel(NodeProjectServiceParamsModel):
    postgres: NetworkAddress
    openid: NodeProjectServiceParamsOpenIDModel | None = None
    url: NetworkUrl
    wildcard_domain: str
    workspaces: ServiceParamsWorkspaceModel


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/coder/coder",
            upstream_tag="v2.31.9",
            upstream_tag_force=True,
            add_dockergroup=True,
            add_dockersocket=True,
            network={
                "http": NetworkTargetModel(
                    port=3000,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=1000,
                mounts={
                    "templates": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("templates"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "workspaces": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("workspaces"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/home/coder",
                        mode="02755",
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
            CODER_ACCESS_URL=f"{self._params.url}",
            CODER_BLOCK_DIRECT="true",
            CODER_DERP_SERVER_STUN_ADDRESSES="disable",
            CODER_HTTP_ADDRESS=f"0.0.0.0:{self._spec_model.network['http'].port}",
            CODER_OAUTH2_GITHUB_DEFAULT_PROVIDER_ENABLE="false",
            CODER_PG_CONNECTION_URL=f"postgresql://homelab:homelab@{param_postgres.address}/homelab?sslmode=disable",
            CODER_TELEMETRY_ENABLE="false",
            CODER_UPDATE_CHECK="false",
            CODER_URL=f"{self._params.url}",
            CODER_WILDCARD_ACCESS_URL=f"*.{self._params.wildcard_domain}",
        )

        if self._params.openid is not None:
            self._compose.common.environment.update(
                CODER_DISABLE_PASSWORD_AUTH="false",
                CODER_OIDC_CLIENT_ID=self._params.openid.client_id,
                CODER_OIDC_CLIENT_SECRET=self._params.openid.client_secret,
                CODER_OIDC_EMAIL_FIELD="email",
                CODER_OIDC_IGNORE_EMAIL_VERIFIED="false",
                CODER_OIDC_ISSUER_URL=url_to_nice(self._params.openid.url),
                CODER_OIDC_SCOPES="openid,profile,email,offline_access",
                CODER_OIDC_SIGN_IN_TEXT=self._params.openid.name,
                CODER_OIDC_USERNAME_FIELD="preferred_username",
            )

        self._scripts.update(
            {
                "login": NodeProjectServiceScriptModel(
                    command=[
                        "coder",
                        "login",
                        f"{self._params.url}",
                    ],
                ),
                "template-init": NodeProjectServiceScriptModel(
                    cwd=self._spec_model.workspace.mounts["templates"].target,
                    command=[
                        "bash",
                        "-c",
                        "for i in */; do pushd $$i && terraform init && popd; done",
                    ],
                ),
                "template-push": NodeProjectServiceScriptModel(
                    cwd=self._spec_model.workspace.mounts["templates"].target,
                    command=[
                        "bash",
                        "-c",
                        "for i in */; do pushd $$i && coder templates push --yes &&  coder templates edit --default-ttl 6h --activity-bump 1h $$(basename $$i) && popd; done",
                    ],
                ),
            }
        )
        super().customize()
