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
            upstream="docker.io/postgres",
            upstream_tag="18-alpine",
            upstream_tag_force=True,
            network={
                "server": NetworkTargetModel(
                    port=5432,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/postgresql",
                        mode="01777",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=70,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._enable_healthcheck(
            [
                "CMD-SHELL",
                f"pg_isready -d{self._group_variables_model.config.database.name} -U{self._group_variables_model.config.database.user}",
            ],
            interval="30s",
        )
        self._compose.common.environment.update(
            POSTGRES_DB=self._group_variables_model.config.database.name,
            POSTGRES_USER=self._group_variables_model.config.database.user,
            POSTGRES_PASSWORD=self._group_variables_model.config.database.password,
            POSTGRES_ROOT_PASSWORD=self._group_variables_model.config.database.password,
        )
        super().customize()
