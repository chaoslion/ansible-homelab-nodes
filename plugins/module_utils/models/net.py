import re
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    NamedTuple,
)

import pydantic
import pydantic_core
from pydantic.networks import IPvAnyAddress

from . import StrictModel
from .common import CONTAINER_NAME_MAIN

NetworkAddressPattern = re.compile(r"^(\w[\w-]*)(:(\d+))?$")

NetworkAddressContainerPattern = re.compile(
    r"^node-(\w[\w-]*):(\w[\w-]*):(\w[\w-]*)?:(\d+):(\w[\w-]*)$"
)


class NetworkAddressValueContainerPort(NamedTuple):
    project: str
    service: str
    instance: int
    endpoint: str


class NetworkAddressValue(NamedTuple):
    host: str
    port: int | NetworkAddressValueContainerPort
    source: str


def _parse_network_address(value: object):
    if not isinstance(value, str):
        return value
    match = NetworkAddressPattern.match(value)
    if match is None:
        match = NetworkAddressContainerPattern.match(value)
        if match is None:
            raise ValueError(f"invalid network address pattern: {value}")
        else:
            node: str = f"node-{match.group(1)}"
            project: str = match.group(2)
            service: str | None = match.group(3)
            instance: str = match.group(4)
            endpoint: str = match.group(5)
            return {
                "host": node,
                "port": {
                    "project": project,
                    "service": service or CONTAINER_NAME_MAIN,
                    "instance": int(instance),
                    "endpoint": endpoint,
                },
                "source": value,
            }
    else:
        host: str = match.group(1)
        port: str | None = match.group(3)
        return {
            "host": host,
            "port": int(port) if port is not None else 80,
            "source": value,
        }


type NetworkAddress = Annotated[
    NetworkAddressValue, pydantic.BeforeValidator(_parse_network_address)
]

type NetworkAddresses = list[NetworkAddress]
type NetworkAddressesMap = dict[str, NetworkAddress]
type NetworkAddressesMapList = dict[str, list[NetworkAddress]]

NetworkAddressAdapter = pydantic.TypeAdapter(NetworkAddress)


type NetworkUrl = Annotated[
    pydantic_core.Url,
    pydantic.networks.UrlConstraints(
        allowed_schemes=["https", "http"],
        host_required=True,
    ),
    pydantic.PlainSerializer(
        lambda x: {
            # remove trailing slash
            "value": str(x).rstrip("/"),
            "host": x.host,
        },
        return_type=dict[str, Any],
    ),
]


# type IPAddress = pydantic.IPvAnyAddress
type IPAddress = Annotated[
    IPvAnyAddress,
    pydantic.PlainSerializer(
        str,
        return_type=str,
    ),
]


def network_address(host: IPAddress | str, port: int | None = None) -> str:
    if port is not None:
        return (
            f"[{host}]:{port}"
            if not isinstance(host, str) and host.version == 6
            else f"{host}:{port}"
        )
    return f"{host}"


class NetworkAddressResolved(StrictModel):
    host: IPAddress | str
    port: int
    source: str

    @pydantic.computed_field
    @property
    def address(self) -> str:
        return network_address(self.host, self.port)

    @pydantic.computed_field
    @property
    def source_host(self) -> str:
        if ":" in self.source:
            host, _ = self.source.rsplit(":", maxsplit=1)
            return host
        return self.source


class DNSRecordModel(StrictModel):
    name: str
    target: str
    type: Literal["A", "CNAME"] = "A"


type WebsiteAuthNames = Literal[
    "admin",
    "sso",
    "admin/sso",
    "custom",
]


class WebsiteGroupNames(str, Enum):
    APPS = "Apps"
    MEDIA = "Media"
    SMARTHOME = "Smarthome"
    MONITOR = "Monitor"
    NETZWERK = "Netzwerk"


type WebsiteTargetSchemeNames = Literal["http", "https"]

type WebsiteTargetSchemeNamesAddon = Literal[
    "http+nohttp2",
    "https+insecure",
    "https+insecure+nohttp2",
]


class WebsiteHomepageModel(StrictModel):
    auth: WebsiteAuthNames | None = None
    group: WebsiteGroupNames | None = None
    help: str | None = None
    icon: str | None = None
    monitor_path: str | None = None
    path: str | None = None
    title: str | None = None

    @pydantic.computed_field
    @property
    def description(self) -> str | None:
        result: list[str] = []
        if self.help is not None:
            result.append(self.help.strip())
        if self.auth is not None:
            result.append(f"Login: {self.auth}")
        return "\n".join(result).strip() or None


class WebsiteProxyServiceModel(StrictModel):
    scheme: WebsiteTargetSchemeNames | WebsiteTargetSchemeNamesAddon = "http"
    servers: dict[str, list[NetworkAddress]]


class WebsiteProxyModel(StrictModel):
    middlewares: list[str] = pydantic.Field(default_factory=list)
    router: list[str] | None = pydantic.Field(default_factory=list)
    service: WebsiteProxyServiceModel | str


class WebsiteModel(StrictModel):
    id: str
    domains: set[str]
    proxy: WebsiteProxyModel | None
    homepage: WebsiteHomepageModel | None = None


type ADDRESS_ACCESS = Literal[
    "internal",
    "external",
]

type NetworkTargetModeNames = Literal[
    "tcp",
    "udp",
    "tcp+udp",
]


class NetworkTargetModel(StrictModel):
    mode: NetworkTargetModeNames = "tcp"
    port: int
