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
    openid: NetworkUrl | None = None
    postgres: NetworkAddress
    ssh_externa_port: int | None = None
    ssh_domain: str
    token: str
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/gitea/gitea",
            network={
                "http": NetworkTargetModel(
                    port=3000,
                ),
                "ssh": NetworkTargetModel(
                    port=22,
                ),
            },
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
        param_postgres = self._resolve_address("postgres")

        self._compose.common.volumes.append(
            {
                "source": "/etc/timezone",
                "target": "/etc/timezone",
                "type": "bind",
                "read_only": True,
            },
        )
        self._compose.common.volumes.append(
            {
                "source": "/etc/localtime",
                "target": "/etc/localtime",
                "type": "bind",
                "read_only": True,
            },
        )

        if self._params.ssh_externa_port is not None:
            self._compose.common.environment.update(
                {
                    "GITEA__server__SSH_PORT": f"{self._params.ssh_externa_port}",
                }
            )

        self._compose.common.environment.update(
            {
                "GITEA_RUNNER_REGISTRATION_TOKEN": self._params.token,
                "GITEA__cron.update_checker__ENABLED": "false",
                "GITEA__cron__ENABLED": "true",
                "GITEA__cron__NOTICE_ON_SUCCESS": "true",
                "GITEA__database__DB_TYPE": "postgres",
                "GITEA__database__HOST": param_postgres.address,
                "GITEA__database__NAME": self._group_variables_model.config.database.name,
                "GITEA__database__PASSWD": self._group_variables_model.config.database.password,
                "GITEA__database__USER": self._group_variables_model.config.database.user,
                "GITEA__log__LEVEL": "info",
                "GITEA__server__ROOT_URL": f"{self._params.url}",
                "GITEA__server__SSH_DOMAIN": self._params.ssh_domain,
                "GITEA__server__SSH_LISTEN_PORT": f"{self._spec_model.network['ssh'].port}",
                "GITEA__service__ALLOW_ONLY_EXTERNAL_REGISTRATION": "true",
                "GITEA__service__DISABLE_REGISTRATION": "false",
                "GITEA__service__REQUIRE_SIGNIN_VIEW": "false",
                "GITEA__service__SHOW_REGISTRATION_BUTTON": "false",
            }
        )

        if self._params.openid is not None:
            self._compose.common.environment.update(
                {
                    "GITEA__oauth2_client__ACCOUNT_LINKING": "auto",
                    "GITEA__oauth2_client__ENABLE_AUTO_REGISTRATION": "true",
                    "GITEA__oauth2_client__OPENID_CONNECT_SCOPES": "openid profile email",
                    "GITEA__oauth2_client__USERNAME": "nickname",
                    "GITEA__openid__ENABLE_OPENID_SIGNIN": "false",
                    "GITEA__openid__ENABLE_OPENID_SIGNUP": "true",
                    "GITEA__openid__WHITELISTED_URIS": f"{self._params.openid}",
                }
            )
        super().customize()
