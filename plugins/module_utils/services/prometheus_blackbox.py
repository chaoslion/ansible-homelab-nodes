import typing
from typing import Annotated

import pydantic

from ..models import StrictModel
from ..models.net import NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import NodeProjectService


class ServiceParamsDNSModel(StrictModel):
    domains: list[str] = pydantic.Field(default=[])
    servers: Annotated[
        list[str],
        pydantic.Field(min_length=1),
    ]


class ServiceParamsModel(NodeProjectServiceParamsModel):
    dns: ServiceParamsDNSModel | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="quay.io/prometheus/blackbox-exporter",
            network={
                "http": NetworkTargetModel(
                    port=9115,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/blackbox_exporter",
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

        super().customize()
