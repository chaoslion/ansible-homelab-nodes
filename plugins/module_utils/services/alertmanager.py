import typing

import pydantic
from typing_extensions import Literal

from ..models.net import (
    NetworkAddresses,
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService

type Severities = typing.Literal["critical", "warning", "info"]


class ServicePushoverCredentialsModel(NodeProjectServiceParamsModel):
    type: Literal["pushover"]
    user: str
    severities: dict[Severities, str]


class ServiceNtfyCredentialsModel(NodeProjectServiceParamsModel):
    type: Literal["ntfy"]
    token: str
    topic_prefix: str
    url: NetworkUrl


class ServiceParamsModel(NodeProjectServiceParamsModel):
    notifiers: list[
        typing.Annotated[
            ServicePushoverCredentialsModel | ServiceNtfyCredentialsModel,
            pydantic.Field(discriminator="type"),
        ]
    ]
    peers: NetworkAddresses = pydantic.Field(default_factory=list)
    url: NetworkUrl | None = None


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/prom/alertmanager",
            network={
                "cluster": NetworkTargetModel(
                    port=9094,
                    mode="tcp+udp",
                ),
                "http": NetworkTargetModel(
                    port=9093,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/alertmanager",
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/alertmanager",
                        mode="0775",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=65534,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        peers = self._resolve_addresses("peers")
        command: list[str] = []
        command.extend(
            [
                "--config.file=/etc/alertmanager/alertmanager.yml",
                "--storage.path=/alertmanager",
            ]
        )

        if self._params.peers:
            command.append(
                "--cluster.label=homelab",
            )
            command.append(
                f"--cluster.advertise-address={self._spec_model.network['cluster'].port}",
            )
            for peer in peers:
                command.append(
                    f"--cluster.peer={peer.address}",
                )

        else:
            command.append(
                "--cluster.listen-address=",
            )

        if self._params.url is not None:
            command.append(
                f"--web.external-url={self._params.url}",
            )
        self._compose.extra.update(command=command)
        super().customize()
