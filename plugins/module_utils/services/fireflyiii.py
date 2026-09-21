import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
    url_to_nice,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsStorageVolume,
    NodeProjectServiceScriptModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsAuthModel(NodeProjectServiceParamsModel):
    logout_url: NetworkUrl


class ServiceParamsModel(NodeProjectServiceParamsModel):
    auth: ServiceParamsAuthModel | None = None
    key: str
    postgres: NetworkAddress
    proxy: NetworkAddress | None = None
    redis: NetworkAddress
    upload: NodeProjectServiceParamsStorageVolume | None = None
    url: NetworkUrl | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/fireflyiii/core",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=33,
                mounts={
                    "upload": NodeProjectServiceWorkspaceMountModel(
                        mode="0775",
                        target="/var/www/html/storage/upload",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(
                            param="upload",
                        ),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_postgres = self._resolve_address("postgres")
        param_redis = self._resolve_address("redis")

        if self._params.proxy is not None:
            param_proxy = self._resolve_address("proxy")
            self._compose.common.environment.update(
                TRUSTED_PROXIES=f"{param_proxy.host}",
            )

        if self._params.url is not None:
            self._compose.common.environment.update(
                APP_URL=url_to_nice(self._params.url),
            )

        if self._params.auth is not None:
            self._compose.common.environment.update(
                AUTHENTICATION_GUARD="remote_user_guard",
                AUTHENTICATION_GUARD_HEADER="HTTP_REMOTE_USER",
                AUTHENTICATION_GUARD_EMAIL="HTTP_REMOTE_EMAIL",
                CUSTOM_LOGOUT_URL=url_to_nice(self._params.auth.logout_url),
            )

        self._compose.common.environment.update(
            ALLOW_WEBHOOKS="true",
            APP_KEY=self._params.key,
            APP_LOG_LEVEL="notice",
            CACHE_DRIVER="redis",
            DB_CONNECTION="pgsql",
            DB_DATABASE="homelab",
            DB_HOST=f"{param_postgres.host}",
            DB_PASSWORD="homelab",
            DB_PORT=f"{param_postgres.port}",
            DB_USERNAME="homelab",
            DEFAULT_LANGUAGE="de_DE",
            LOG_CHANNEL="stdout",
            REDIS_HOST=f"{param_redis.host}",
            REDIS_PORT=f"{param_redis.port}",
            REDIS_SCHEME="tcp",
            SESSION_DRIVER="redis",
            SITE_OWNER=self._group_variables_model.config.admin.mail,
            # MAIL_MAILER="smtp",
            # MAIL_HOST="{{ vars_group_homelab_nodes__config.mail.address }}",
            # MAIL_PORT="{{ vars_group_homelab_nodes__config.mail.port }}",
            # MAIL_FROM="{{ vars_group_homelab_nodes__config.mail.sender }}",
            # MAIL_USERNAME="{{ vars_group_homelab_nodes__config.mail.user }}",
            # MAIL_PASSWORD="{{ vars_group_homelab_nodes__config.mail.password }}",
            # MAIL_ENCRYPTION="tls",
        )

        self._scripts.update(
            cron=NodeProjectServiceScriptModel(
                command=[
                    "/usr/local/bin/php",
                    "/var/www/html/artisan",
                    "firefly-iii:cron",
                ],
                daily=True,
            ),
        )

        super().customize()
