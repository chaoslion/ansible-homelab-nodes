from typing import Annotated, Final

import pydantic

from . import StrictModel
from .common import CONTAINER_PREFIX
from .config import ConfigModel, ConfigNodeSupervisorGroup
from .net import IPAddress, NetworkTargetModel, network_address


class GroupsModel(StrictModel):
    group: str
    group_images: str
    group_hosts: str
    group_hosts_virt: str
    group_projects: str
    group_supervisors: str
    prefix: str


class GroupVariablesModel(StrictModel):
    cache: str
    roles_path: str
    ca_path: str
    config: ConfigModel
    container_prefix: Annotated[
        Final[str], pydantic.Field(frozen=True, default=CONTAINER_PREFIX, init=False)
    ]
    registry_address: str
    registry_domain: str
    registry_url: str
    registry_url_push: str
    supervisor_inventories: dict[str, str]
    supervisor_groups: dict[ConfigNodeSupervisorGroup, float]


class GroupProjectsVariablesServiceEndpointAddressInternalModel(StrictModel):
    host: str
    port: int

    @pydantic.computed_field
    @property
    def address(self) -> str:
        return network_address(self.host, self.port)


class GroupProjectsVariablesServiceEndpointAddressExternalModel(StrictModel):
    host: IPAddress
    port: int

    @pydantic.computed_field
    @property
    def address(self) -> str:
        return network_address(self.host, self.port)


class GroupProjectsVariablesServiceEndpointModel(StrictModel):
    # can be none if not exposed
    external: GroupProjectsVariablesServiceEndpointAddressExternalModel | None = None
    internal: GroupProjectsVariablesServiceEndpointAddressInternalModel
    target: NetworkTargetModel


type GroupProjectsVariablesProjectServiceEndpoints = dict[
    str, GroupProjectsVariablesServiceEndpointModel
]

type GroupProjectsVariablesProjectServicesEndpoints = dict[
    str, GroupProjectsVariablesProjectServiceEndpoints
]
type GroupProjectsVariablesProjectsServicesEndpoints = dict[
    str, GroupProjectsVariablesProjectServicesEndpoints
]

type GroupProjectVariablesNetworks = dict[
    str, GroupProjectsVariablesProjectsServicesEndpoints
]


class GroupProjectVariablesModel(StrictModel):
    networks: GroupProjectVariablesNetworks = pydantic.Field(default_factory=dict)
    nodes: dict[str, str] = pydantic.Field(default_factory=dict)
