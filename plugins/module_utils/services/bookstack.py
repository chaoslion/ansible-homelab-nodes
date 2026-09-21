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
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    key: str
    openid: NodeProjectServiceParamsOpenIDModel
    redis: NetworkAddress
    mariadb: NetworkAddress
    url: NetworkUrl
    upload_limit: int


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/solidnerd/bookstack",
            network={
                "http": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=33,
                mounts={
                    "php.ini": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/local/etc/php/php.ini",
                        create=False,
                    ),
                    "uploads": NodeProjectServiceWorkspaceMountModel(
                        target="/var/www/bookstack/storage/uploads",
                        mode="0775",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_mariadb = self._resolve_address("mariadb")
        param_redis = self._resolve_address("redis")

        self._compose.common.environment.update(
            APP_AUTO_LANG_PUBLIC="false",
            APP_DISPLAY_TIMEZONE=self._group_variables_model.config.timezone,
            APP_KEY=self._params.key,
            APP_LANG="de",
            APP_URL=url_to_nice(self._params.url),
            AUTH_AUTO_INITIATE="false",
            AUTH_METHOD="oidc",
            CACHE_DRIVER="redis",
            DB_HOST=param_mariadb.address,
            FILE_UPLOAD_SIZE_LIMIT=f"{self._params.upload_limit}",
            OIDC_SCOPES="openid profile email",
            OIDC_EXTERNAL_ID_CLAIM="email",
            OIDC_ADDITIONAL_SCOPES="homelab_bookstack",
            OIDC_CLIENT_ID=self._params.openid.client_id,
            OIDC_CLIENT_SECRET=self._params.openid.client_secret_encoded,
            OIDC_DISPLAY_NAME_CLAIMS="name",
            OIDC_END_SESSION_ENDPOINT="false",
            OIDC_FETCH_AVATAR="false",
            OIDC_GROUPS_CLAIM="homelab_bookstack",
            OIDC_ISSUER=url_to_nice(self._params.openid.url),
            OIDC_ISSUER_DISCOVER="true",
            OIDC_NAME=self._params.openid.name,
            OIDC_USER_TO_GROUPS="true",
            OIDC_REMOVE_FROM_GROUPS="true",
            QUEUE_CONNECTION="redis",
            RECYCLE_BIN_LIFETIME="0",
            REDIS_SERVERS=f"{param_redis.address}:0",
            SESSION_DRIVER="redis",
            STORAGE_TYPE="local_secure",
        )
        self._compose.common.volumes.append(
            {
                "target": "/var/www/bookstack/public/uploads",
                "tmpfs": {
                    "size": "4M",
                },
                "type": "tmpfs",
            },
        )

        self._compose.common.environment.update(
            DB_DATABASE=self._group_variables_model.config.database.name,
            DB_USERNAME=self._group_variables_model.config.database.user,
            DB_PASSWORD=self._group_variables_model.config.database.password,
        )

        super().customize()
