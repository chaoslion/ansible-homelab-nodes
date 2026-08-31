import typing

from ..models.net import NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import NodeProjectService, ServiceHelper


class ServiceParamsSynologyModel(NodeProjectServiceParamsModel):
    username: str
    password: str


class ServiceParamsModel(NodeProjectServiceParamsModel):
    synology: ServiceParamsSynologyModel | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="quay.io/prometheus/snmp-exporter",
            network={
                "http": NetworkTargetModel(
                    port=9116,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("config"),
                    ),
                },
                bump="reload",
            ),
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
                f"http://localhost:{self._spec_model.network['http'].port}",
            ],
        )

        self._compose.extra.update(
            command=[
                "--config.file=/etc/snmp_exporter/snmp.yml",
                f"--config.file={self._spec_model.workspace.mounts['config'].target}/*.yml",
            ],
        )

        super().customize()
