import typing

import pydantic

from ..models.net import NetworkAddress, NetworkAddressesMap, NetworkTargetModel
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
)
from . import (
    NodeProjectService,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    domain: str
    self: NetworkAddress
    peer: NetworkAddress
    hosts: NetworkAddressesMap = pydantic.Field(default_factory=dict)
    slave: bool = False


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/coredns/coredns",
            network={
                "dns": NetworkTargetModel(
                    port=53,
                    mode="tcp+udp",
                ),
                "metrics": NetworkTargetModel(
                    port=9153,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/coredns",
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._resolve_address("self")
        self._resolve_address("peer")
        self._resolve_addresses_map("hosts")
        self._compose.extra.update(
            command=[
                "-conf",
                "/etc/coredns/Corefile",
            ],
        )
        super().customize()
