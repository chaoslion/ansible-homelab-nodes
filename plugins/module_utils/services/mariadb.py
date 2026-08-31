import typing

from ..models.net import NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    pass


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/mariadb",
            upstream_tag="12",
            upstream_tag_force=True,
            network={
                "server": NetworkTargetModel(
                    port=3306,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                owner=999,
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/mysql",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._enable_healthcheck(
            [
                "CMD",
                "healthcheck.sh",
                "--connect",
                "--innodb_initialized",
            ],
        )

        self._compose.common.environment.update(
            MARIADB_DATABASE=self._group_variables_model.config.database.name,
            MARIADB_USER=self._group_variables_model.config.database.user,
            MARIADB_PASSWORD=self._group_variables_model.config.database.password,
            MARIADB_ROOT_PASSWORD=self._group_variables_model.config.database.password,
        )

        super().customize()
