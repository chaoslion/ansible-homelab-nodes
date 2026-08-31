import typing

from ..models.net import (
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import (
    NodeProjectService,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    basedn: str
    jwt_secret: str
    key_seed: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/lldap/lldap",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=17170,
                ),
                "ldap": NetworkTargetModel(
                    port=3890,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/data",
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
        self._compose.common.environment.update(
            RUST_LOG="warn",
            LLDAP_DATABASE_URL=f"sqlite://{self._spec_model.workspace.mounts['data'].target}/users.db?mode=rwc",
            LLDAP_JWT_SECRET=self._params.jwt_secret,
            LLDAP_KEY_SEED=self._params.key_seed,
            LLDAP_KEY_FILE="",
            LLDAP_LDAP_BASE_DN=self._params.basedn,
            LLDAP_LDAP_USER_DN=self._group_variables_model.config.admin.name,
            LLDAP_LDAP_USER_EMAIL=self._group_variables_model.config.admin.mail,
            LLDAP_LDAP_USER_PASS=self._group_variables_model.config.admin.password,
        )
        super().customize()
