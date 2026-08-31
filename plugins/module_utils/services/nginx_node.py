import typing

from attr import s

from ..models.net import (
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
)
from . import (
    NodeProjectService,
    ServiceHelper,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    command: list[str]
    healthcheck: str


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/node",
            network={
                "http": NetworkTargetModel(
                    port=4321,
                ),
            },
        )

    @typing.override
    def customize(
        self,
    ):

        self._enable_healthcheck(
            [
                "CMD",
                "wget",
                "-q",
                "-O-",
                f"http://localhost:{self._spec_model.network['http'].port}/{self._params.healthcheck}",
            ],
        )

        workspace = ServiceHelper.container_mount("workspace")
        self._compose.common.volumes.append(
            {
                "target": workspace,
                "source": self._node_project_variables_model.workspaces["main"][
                    "workspace"
                ].source,
                "type": "bind",
                "read_only": True,
            },
        )
        self._compose.extra.update(
            working_dir=workspace,
            command=self._params.command,
        )
        super().customize()
