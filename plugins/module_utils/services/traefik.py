import typing

import pydantic

from ..models.net import (
    NetworkAddress,
    NetworkAddressesMap,
    NetworkTargetModel,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService, ServiceHelper


class ParamsACMEDNSModel(NodeProjectServiceParamsModel):
    name: str
    env: dict[str, str]


class ServiceParamsDomainModel(NodeProjectServiceParamsModel):
    main: str
    sans: list[str] = pydantic.Field(default=[])


class ServiceParamsCrowdsecModel(NodeProjectServiceParamsModel):
    appsec: NetworkAddress
    lapi: NetworkAddress
    key: str


class ServiceParamsModel(NodeProjectServiceParamsModel):
    acmedns: ParamsACMEDNSModel
    authelia: NetworkAddress | None = None
    crowdsec: ServiceParamsCrowdsecModel | None = None
    domain: ServiceParamsDomainModel
    errorpages: NetworkAddress
    targets: NetworkAddressesMap = pydantic.Field(default={})


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/traefik",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=80,
                ),
                "https": NetworkTargetModel(
                    port=443,
                ),
                "dashboard": NetworkTargetModel(
                    port=8080,
                ),
                "metrics": NetworkTargetModel(
                    port=8090,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/traefik",
                    ),
                    "acme": NodeProjectServiceWorkspaceMountModel(
                        target=ServiceHelper.container_mount("acme"),
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        self._resolve_addresses_map("targets")
        if self._params.crowdsec is not None:
            self._resolve_address("crowdsec_appsec", self._params.crowdsec.appsec)
            self._resolve_address("crowdsec_lapi", self._params.crowdsec.lapi)
        if self._params.authelia is not None:
            self._resolve_address("authelia")
        self._resolve_address("errorpages")
        self._compose.common.environment.update(self._params.acmedns.env)

        super().customize()
