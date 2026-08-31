import typing

from ..models.net import (
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    pass


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/nginx",
            upstream_tag="stable-alpine-slim",
            network={
                "http": NetworkTargetModel(
                    port=80,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/nginx/conf.d",
                    ),
                    "workspace": NodeProjectServiceWorkspaceMountModel(
                        target="/usr/share/nginx/html",
                    ),
                },
                owner=101,
            ),
        )
