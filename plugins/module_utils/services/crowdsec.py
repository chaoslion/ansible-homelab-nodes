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
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    collections: list[str]
    keys: dict[str, str]


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/crowdsecurity/crowdsec",
            add_timezone="",
            network={
                "appsec": NetworkTargetModel(
                    port=7422,
                ),
                "lapi": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                bump="reload",
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/crowdsec",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/var/lib/crowdsec/data/",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._compose.common.environment.update(
            {
                # "DISABLE_AGENT": "true",
                "COLLECTIONS": " ".join(self._params.collections),
                **{
                    f"BOUNCER_KEY_{name}": value
                    for name, value in self._params.keys.items()
                },
            }
        )
        super().customize()
