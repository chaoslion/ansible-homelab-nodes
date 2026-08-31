import json
import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsOpenIDModel,
    NodeProjectServiceParamsStorageVolume,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    language: str
    media: NodeProjectServiceParamsStorageVolume | None = None
    openid: NodeProjectServiceParamsOpenIDModel | None = None
    postgres: NetworkAddress
    redis: NetworkAddress
    secret: str
    url: NetworkUrl | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/paperless-ngx/paperless-ngx",
            network={
                "http": NetworkTargetModel(
                    port=8000,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/src/paperless/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "media": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/src/paperless/media",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(
                            param="media",
                        ),
                    ),
                    "export": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/src/paperless/export",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=1000,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_redis = self._resolve_address("redis")
        param_postgres = self._resolve_address("postgres")
        self._compose.common.environment.update(
            PAPERLESS_OCR_PAGES="32",
            PAPERLESS_FILENAME_FORMAT="{% raw %}{{ owner_username }}/{{ created }}-{{ original_name }}{% endraw %}",
            PAPERLESS_CONSUMER_DISABLE="true",
            PAPERLESS_ADMIN_USER=self._group_variables_model.config.admin.name,
            PAPERLESS_ADMIN_MAIL=self._group_variables_model.config.admin.mail,
            PAPERLESS_ADMIN_PASSWORD=self._group_variables_model.config.admin.password,
            PAPERLESS_REDIS=f"redis://{param_redis.address}",
            PAPERLESS_DBENGINE="postgresql",
            PAPERLESS_DBNAME="homelab",
            PAPERLESS_DBUSER="homelab",
            PAPERLESS_DBPASS="homelab",
            PAPERLESS_DBHOST=param_postgres.address,
            PAPERLESS_DBPORT=f"{param_postgres.port}",
            PAPERLESS_SECRET_KEY=self._params.secret,
            PAPERLESS_OCR_LANGUAGE=self._params.language,
        )

        if self._params.openid is not None:
            openid_config = {
                "openid_connect": {
                    "SCOPE": [
                        "openid",
                        "profile",
                        "email",
                        "groups",
                    ],
                    "APPS": [
                        {
                            "provider_id": "homelab",
                            "name": self._params.openid.name,
                            "client_id": self._params.openid.client_id,
                            "secret": self._params.openid.client_secret,
                            "settings": {"server_url": f"{self._params.openid.url}"},
                        }
                    ],
                }
            }
            self._compose.common.environment.update(
                PAPERLESS_APPS="allauth.socialaccount.providers.openid_connect",
                PAPERLESS_SOCIALACCOUNT_PROVIDERS=json.dumps(openid_config),
                PAPERLESS_SOCIAL_ACCOUNT_SYNC_GROUPS="true",
                PAPERLESS_SOCIAL_AUTO_SIGNUP="true",
            )

        if self._params.url is not None:
            self._compose.common.environment.update(
                PAPERLESS_URL=f"{self._params.url}",
            )

        self._compose.common.volumes.append(
            {
                "target": "/usr/src/paperless/consume",
                "tmpfs": {
                    "size": "4M",
                },
                "type": "tmpfs",
            },
        )
        super().customize()
