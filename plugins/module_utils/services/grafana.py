import typing

from ..models.net import NetworkTargetModel, NetworkUrl
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    url: NetworkUrl | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/grafana/grafana-oss",
            network={
                "http": NetworkTargetModel(
                    port=3000,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=472,
                group=0,
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/grafana",
                        mode="0777",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        if self._params.url is not None:
            self._compose.common.environment.update(
                GF_SERVER_ROOT_URL=f"{self._params.url}",
            )
        self._compose.common.environment.update(
            GF_AUTH_ANONYMOUS_ENABLED="true",
            GF_AUTH_ANONYMOUS_ORG_NAME="homelab",
            GF_AUTH_ANONYMOUS_ORG_ROLE="Viewer",
            GF_AUTH_ANONYMOUS_HIDE_VERSION="true",
            GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES="false",
            GF_ANALYTICS_CHECK_FOR_UPDATES="false",
            GF_ANALYTICS_ENABLED="false",
            GF_ANALYTICS_REPORTING_ENABLED="false",
            GF_LOG_LEVEL="warn",
            GF_LOG_MODE="console",
            GF_SECURITY_ADMIN_MAIL=self._group_variables_model.config.admin.mail,
            GF_SECURITY_ADMIN_PASSWORD=self._group_variables_model.config.admin.password,
            GF_SECURITY_ADMIN_USER=self._group_variables_model.config.admin.name,
            GF_SECURITY_ALLOW_EMBEDDING="true",
            GF_SECURITY_DISABLE_GRAVATAR="true",
            GF_SNAPSHOTS_EXTERNAL_ENABLED="false",
        )
        super().customize()
