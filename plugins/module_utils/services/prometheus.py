import typing
from typing import Literal

import pydantic

from ..models.net import (
    NetworkAddress,
    NetworkAddresses,
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceScriptModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import (
    NodeProjectService,
    ServiceHelper,
)


class ServiceParamsModel(NodeProjectServiceParamsModel):
    alertmanagers: NetworkAddresses
    alertmanager_peers: NetworkAddresses = pydantic.Field(default_factory=list)
    exporters: dict[
        Literal[
            "blackbox",
            "snmp",
        ],
        NetworkAddress,
    ] = pydantic.Field(default_factory=dict)
    peers: NetworkAddresses = pydantic.Field(default_factory=list)
    retention: str
    url: NetworkUrl | None = None
    targets: dict[str, NetworkAddresses] = pydantic.Field(default_factory=dict)


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="quay.io/prometheus/prometheus",
            add_dockerhost=True,
            network={
                "http": NetworkTargetModel(
                    port=9090,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "config": NodeProjectServiceWorkspaceMountModel(
                        target="/etc/prometheus",
                    ),
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/prometheus",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                        mode="0775",
                    ),
                },
                owner=65534,
                bump="reload",
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        # inject docker nodes node_exporter endpoint
        self._params.targets.update(
            {
                "nodes_node_exporters": [
                    ServiceHelper.parse_address(f"node-{name}:9100")
                    for name in self._group_projects_variables_model.nodes
                ]
            }
        )

        # inject docker nodes homelab-stats endpoint
        self._params.targets.update(
            {
                "nodes_homelab_stats": [
                    ServiceHelper.parse_address(f"node-{name}:9050")
                    for name in self._group_projects_variables_model.nodes
                ]
            }
        )

        _ = self._resolve_addresses("alertmanagers")
        _ = self._resolve_addresses("alertmanager_peers")
        _ = self._resolve_addresses("peers")
        _ = self._resolve_addresses_map("exporters")
        _ = self._resolve_addresses_nested("targets")
        command: list[str] = [
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            f"--storage.tsdb.retention.time={self._params.retention}",
            "--web.console.libraries=/usr/share/prometheus/console_libraries",
            "--web.console.templates=/usr/share/prometheus/consoles",
            "--web.enable-admin-api",
            "--web.enable-remote-write-receiver",
        ]
        if self._params.url is not None:
            command.append(
                f"--web.external-url={self._params.url}",
            )
            self._scripts.update(
                {
                    "tsdb-clean": NodeProjectServiceScriptModel(
                        command=[
                            "curl",
                            "-XPOST",
                            f"{self._params.url}/api/v1/admin/tsdb/clean_tombstones",
                        ],
                        host=True,
                    ),
                }
            )

        self._compose.extra.update(
            command=command,
        )

        super().customize()
