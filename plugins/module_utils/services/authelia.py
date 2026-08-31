import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceScriptModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import (
    NodeProjectService,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    domain: str
    basedn: str
    encryption_key: str
    jwt_secret: str
    ldap: NetworkAddress
    postgres: NetworkAddress
    redis: NetworkAddress
    session_secret: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/authelia/authelia",
            network={
                "http": NetworkTargetModel(
                    port=9091,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                bump="restart",
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/config",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._resolve_address("ldap")
        self._resolve_address("redis")
        self._resolve_address("postgres")

        # custom command to bypass entrypoint.sh 'chown of /config'
        self._compose.extra.update(
            command=[
                "authelia",
            ],
        )
        self._compose.common.environment.update(
            X_AUTHELIA_CONFIG=self._spec_model.workspace.mounts["config"].target,
        )

        self._scripts.update(
            {
                "password": NodeProjectServiceScriptModel(
                    command=[
                        "authelia",
                        "crypto",
                        "hash",
                        "generate",
                    ],
                ),
                "client-id": NodeProjectServiceScriptModel(
                    command=[
                        "authelia",
                        "crypto",
                        "rand",
                        "--length=72",
                        "--charset=rfc3986",
                    ],
                ),
                "client-secret": NodeProjectServiceScriptModel(
                    command=[
                        "authelia",
                        "crypto",
                        "hash",
                        "generate",
                        "pbkdf2",
                        "--variant=sha512",
                        "--random",
                        "--random.length=72",
                        "--random.charset=rfc3986",
                    ],
                ),
            }
        )

        super().customize()
