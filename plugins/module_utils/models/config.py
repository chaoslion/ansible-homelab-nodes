from typing import Annotated, Any, Literal

import pydantic

from . import StrictModel
from .common import UserModel
from .net import IPAddress, WebsiteGroupNames, WebsiteModel

type ConfigNodeSupervisorGroup = Literal[
    "low",
    "mid",
    "high",
    "max",
]


class ConfigSupervisorModel(StrictModel):
    host: IPAddress
    gateway: IPAddress
    # default qemu config
    config: dict[str, object] = pydantic.Field(default_factory=dict)


class ConfigSupervisorImageModel(StrictModel):
    url: str
    url_sha: str
    path: str


class ConfigSupervisorsModel(StrictModel):
    hosts: dict[str, ConfigSupervisorModel]
    image: ConfigSupervisorImageModel
    offset: int | None = None


class ConfigRegistryLocalInsecureModel(StrictModel):
    address: str
    port: int
    images: dict[str, str] = pydantic.Field(default_factory=dict)


class ConfigMailModel(StrictModel):
    password: str
    port: int
    sender: str
    server: str
    user: str

    @pydantic.computed_field
    @property
    def header_from(self) -> str:
        return f"Homelab <{self.sender}>"


class ConfigDatabaseModel(StrictModel):
    name: str
    user: str
    password: str


class ConfigWebsitesModel(StrictModel):
    default_homepage_group: WebsiteGroupNames
    sites: list[WebsiteModel]


class ConfigModel(StrictModel):
    admin: UserModel
    content: str
    domain: str
    ip_range: list[str] = pydantic.Field(default_factory=list)
    database: ConfigDatabaseModel
    hosts: dict[str, IPAddress] = pydantic.Field(default_factory=dict)
    mail: ConfigMailModel
    registry: ConfigRegistryLocalInsecureModel
    supervisors: ConfigSupervisorsModel | None = None
    timezone: str
    websites: ConfigWebsitesModel | None = None


class ConfigNodeSupervisorModel(StrictModel):
    backup: bool = True
    index: int
    name: str
    disk: int = 32
    startup: int | None = None
    # define limits, else use supervisor defaults
    group: ConfigNodeSupervisorGroup = "low"
    cores: int | None = None
    # IN MB
    memory: int | None = None


class ConfigNodeProjectServiceExposeModel(StrictModel):
    # map port internal to external
    port: int | None = None
    bind: IPAddress | None = None
    container_expose: bool = True
    website: WebsiteModel | None = None


class ConfigNodeProjectServiceLimitsModel(StrictModel):
    cpus: float | None = 0.5
    # in MB
    memory: Annotated[
        int | None,
        pydantic.PlainSerializer(
            lambda value: f"{value}m",
            return_type=str,
        ),
    ] = 512


class ConfigNodeProjectServiceModel(StrictModel):
    # dns: list[str | None] = None
    params: dict[str, object] = pydantic.Field(default_factory=dict)
    clone: int | None = None
    service: str | None = None
    tag: str | None = None
    limits: ConfigNodeProjectServiceLimitsModel = ConfigNodeProjectServiceLimitsModel()
    # expose can be port or ip:port (string)
    expose: dict[str, ConfigNodeProjectServiceExposeModel] | None = None


class ConfigNodeProjectServicesModel(StrictModel):
    name: str | None = None
    service: ConfigNodeProjectServiceModel
    dependencies: dict[str, ConfigNodeProjectServiceModel] = pydantic.Field(
        default_factory=dict
    )


class ConfigNodeModel(StrictModel):
    config: Annotated[
        dict[str, object],
        pydantic.Field(exclude=True),
    ] = pydantic.Field(default_factory=dict)
    packages: list[str] = pydantic.Field(default_factory=list)
    bootstrap: str | None = None
    projects: Annotated[
        dict[str, ConfigNodeProjectServicesModel],
        pydantic.Field(exclude=True),
    ] = pydantic.Field(default_factory=dict)
    supervisor: ConfigNodeSupervisorModel | None = None
