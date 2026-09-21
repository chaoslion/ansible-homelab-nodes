import urllib.parse
from typing import Annotated, Literal

import pydantic

from . import StrictModel
from .config import (
    ConfigNodeModel,
)
from .net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
    WebsiteTargetSchemeNames,
    url_to_nice,
)


class NodeVariablesModel(StrictModel):
    config: ConfigNodeModel
    hostname: str
    name: str
    workspace: str


type NodeProjectServiceWorkspaceBump = Literal[
    "restart",
    "reload",
]


class NodeProjectServiceImageModel(StrictModel):
    name: str
    source: str
    tag: str

    @pydantic.computed_field
    @property
    def repo(self) -> str:
        return f"{self.name}:{self.tag}"

    @pydantic.computed_field
    @property
    def id(self) -> str:
        return f"{self.name.replace('-', '_')}__{self.tag.replace('-', '_').replace('.', '_')}"


class NodeProjectServiceComposeCommonModel(StrictModel):
    # container_name: str
    environment: dict[str, str] = pydantic.Field(default_factory=dict)
    image: str
    ports: list[str] = pydantic.Field(default_factory=list)
    restart: str
    volumes: list[dict[str, object]] = pydantic.Field(default_factory=list)


class NodeProjectServiceComposeModel(StrictModel):
    common: NodeProjectServiceComposeCommonModel
    extra: dict[str, object] = pydantic.Field(default_factory=dict)

    @pydantic.model_serializer()
    def ser_model(self) -> dict[str, object]:
        return self.common.model_dump(exclude_defaults=True) | self.extra


class NodeProjectServiceWorkspaceMountVolumeModel(StrictModel):
    param: str | None = None


class NodeProjectServiceWorkspaceMountModel(StrictModel):
    create: bool = True
    target: str
    mode: str | None = None
    volume: NodeProjectServiceWorkspaceMountVolumeModel | None = None


class NodeProjectServiceWorkspaceModel(StrictModel):
    bump: NodeProjectServiceWorkspaceBump | None = None
    group: int | None = None
    mounts: dict[str, NodeProjectServiceWorkspaceMountModel] = pydantic.Field(
        default_factory=dict
    )
    owner: int = 0


class NodeProjectServiceSpecModel(StrictModel):
    add_timezone: str | None = None
    add_dockerhost: bool = False
    add_dockersocket: bool = False
    add_dockergroup: bool = False
    network: dict[str, NetworkTargetModel] = pydantic.Field(default_factory=dict)
    upstream: str
    upstream_tag: str = "latest"
    upstream_tag_force: bool = False
    workspace: NodeProjectServiceWorkspaceModel = NodeProjectServiceWorkspaceModel()


class NodeProjectWorkspaceModel(StrictModel):
    source: str
    target: str


class NodeProjectWorkspaceOwnerModel(StrictModel):
    owner: int
    group: int
    bump: NodeProjectServiceWorkspaceBump | None = None


class NodeProjectWorkspacePathModel(StrictModel):
    group: int
    mode: str
    owner: int
    path: str


class NodeProjectServiceParamsModel(StrictModel):
    pass


type NodeProjectServiceParams = dict[str, object]


class NodeProjectServiceScriptModel(StrictModel):
    command: list[str]
    cwd: str | None = None
    daily: bool = False
    host: bool = False


class NodeProjectVariablesModel(StrictModel):
    compose_services: dict[str, object] = pydantic.Field(default_factory=dict)
    compose_volumes: dict[str, object] = pydantic.Field(default_factory=dict)
    containers: dict[str, object] = pydantic.Field(default_factory=dict)
    id: str
    urn: str
    node_name: str
    params: NodeProjectServiceParams = pydantic.Field(default_factory=dict)
    project_name: str
    scripts: dict[str, NodeProjectServiceScriptModel] = pydantic.Field(
        default_factory=dict
    )
    specs: dict[str, object] = pydantic.Field(default_factory=dict)
    workspace: str
    workspace_root: str
    workspaces: dict[str, dict[str, NodeProjectWorkspaceModel]] = pydantic.Field(
        default_factory=dict
    )
    workspaces_owners: dict[str, NodeProjectWorkspaceOwnerModel] = pydantic.Field(
        default_factory=dict
    )
    workspaces_paths: list[NodeProjectWorkspacePathModel] = pydantic.Field(
        default_factory=list
    )


class NodeProjectServiceParamsUrlAddressModel(NodeProjectServiceParamsModel):
    target: NetworkAddress
    scheme: WebsiteTargetSchemeNames = "http"


class NodeProjectServiceParamsOpenIDModel(NodeProjectServiceParamsModel):
    client_id: str
    client_secret: str
    url: NetworkUrl

    @pydantic.computed_field
    @property
    def client_secret_encoded(self) -> str:
        return urllib.parse.quote_plus(self.client_secret)

    @pydantic.computed_field
    @property
    def name(self) -> str:
        return "Homelab SSO"

    @pydantic.computed_field
    @property
    def url_well_known(self) -> str:
        url = url_to_nice(self.url)
        return f"{url}/.well-known/openid-configuration"


class NodeProjectServiceParamsStorageVolumeS3Model(NodeProjectServiceParamsModel):
    type: Literal["s3"]
    bucket: str
    key: str
    region: str
    secret: str
    url: NetworkUrl


class NodeProjectServiceParamsStorageVolumeFSModel(NodeProjectServiceParamsModel):
    type: Literal["fs"]
    path: str
    exclusive: bool = False


class NodeProjectServiceParamsStorageVolumeNFSModel(NodeProjectServiceParamsModel):
    type: Literal["nfs"]
    path: str
    host: str
    exclusive: bool = False
    version: str | None = None
    timeout: int = 10


NodeProjectServiceParamsStorageVolume = Annotated[
    NodeProjectServiceParamsStorageVolumeFSModel
    | NodeProjectServiceParamsStorageVolumeNFSModel
    | NodeProjectServiceParamsStorageVolumeS3Model,
    pydantic.Field(discriminator="type"),
]

NodeProjectServiceParamsStorageVolumeAdapter = pydantic.TypeAdapter(
    NodeProjectServiceParamsStorageVolume
)
