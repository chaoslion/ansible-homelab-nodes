from typing import cast

from ..models.config import (
    ConfigModel,
    ConfigNodeProjectServiceExposeModel,
    ConfigNodeProjectServiceModel,
)
from ..models.group import (
    GroupProjectsVariablesProjectServiceEndpoints,
    GroupProjectsVariablesServiceEndpointAddressExternalModel,
    GroupProjectsVariablesServiceEndpointAddressInternalModel,
    GroupProjectsVariablesServiceEndpointModel,
    GroupProjectVariablesModel,
    GroupProjectVariablesNetworks,
    GroupVariablesModel,
)
from ..models.net import (
    IPAddress,
    NetworkAddress,
    NetworkAddressAdapter,
    NetworkAddresses,
    NetworkAddressesMap,
    NetworkAddressesMapList,
    NetworkAddressResolved,
    NetworkAddressValueContainerPort,
)
from ..models.node import (
    NodeProjectServiceComposeCommonModel,
    NodeProjectServiceComposeModel,
    NodeProjectServiceImageModel,
    NodeProjectServiceParamsModel,
    NodeProjectServiceParamsStorageVolume,
    NodeProjectServiceParamsStorageVolumeAdapter,
    NodeProjectServiceParamsStorageVolumeFSModel,
    NodeProjectServiceParamsStorageVolumeNFSModel,
    NodeProjectServiceParamsStorageVolumeS3Model,
    NodeProjectServiceScriptModel,
    NodeProjectServiceSpecModel,
    NodeProjectVariablesModel,
    NodeProjectWorkspaceModel,
    NodeProjectWorkspaceOwnerModel,
    NodeProjectWorkspacePathModel,
)


class ServiceHelper:
    @staticmethod
    def in_seconds(minutes: int = 0, hours: int = 0) -> int:
        return minutes * 60 + hours * 60

    @staticmethod
    def in_bytes(megabytes: int = 0, gigabytes: int = 0) -> int:
        return megabytes * 1024**2 + gigabytes * 1024**3

    @staticmethod
    def container_mount(dir: str) -> str:
        return f"/mnt/homelab-{dir}"

    @staticmethod
    def parse_address(
        value: str,
    ) -> NetworkAddress:
        return NetworkAddressAdapter.validate_python(value)

    @staticmethod
    def resolve_addresses(
        address: NetworkAddress,
        config: ConfigModel,
        networks: GroupProjectVariablesNetworks,
    ) -> (
        NetworkAddressResolved
        | tuple[str, NetworkAddressResolved, NetworkAddressResolved | None]
    ):
        try:
            host = config.hosts[address.host]
        except KeyError:
            raise ValueError(f"unknown host: {address}")

        if isinstance(address.port, int):
            return NetworkAddressResolved(
                host=host,
                port=address.port,
                source=address.source,
            )

        container_address: NetworkAddressValueContainerPort = address.port
        host_node_name = address.host.replace("node-", "")

        try:
            networks_host = networks[host_node_name]
        except KeyError:
            raise ValueError(f"unknown node host: {address}")

        try:
            networks_host_project = networks_host[container_address.project]
        except KeyError:
            raise ValueError(f"unknown project: {address}")

        try:
            networks_host_project_service = networks_host_project[
                container_address.service
            ]
        except KeyError:
            raise ValueError(f"unknown service: {address}")

        try:
            networks_host_project_service_endpoint = networks_host_project_service[
                container_address.endpoint
            ]
        except KeyError:
            raise ValueError(f"unknown service endpoint: {address}")

        internal = NetworkAddressResolved(
            host=networks_host_project_service_endpoint.internal.host,
            port=int(networks_host_project_service_endpoint.internal.port),
            source=address.source,
        )
        external: NetworkAddressResolved | None = None
        if networks_host_project_service_endpoint.external is not None:
            external = NetworkAddressResolved(
                host=networks_host_project_service_endpoint.external.host,
                port=int(networks_host_project_service_endpoint.external.port),
                source=address.source,
            )

        return (host_node_name, internal, external)

    @staticmethod
    def resolve_address(
        address: NetworkAddress,
        config: ConfigModel,
        networks: GroupProjectVariablesNetworks,
        node_name: str,
    ) -> NetworkAddressResolved:
        addresses = ServiceHelper.resolve_addresses(address, config, networks)
        if not isinstance(addresses, tuple):
            return addresses
        address_node_name, address_internal, address_external = addresses
        if node_name == address_node_name:
            return address_internal
        if address_external is None:
            raise ValueError(f"Could not resolve external address: {address}")
        return address_external


class NodeProjectService[T: NodeProjectServiceParamsModel]:
    def __init__(
        self,
        group_variables_model: GroupVariablesModel,
        group_projects_variables_model: GroupProjectVariablesModel,
        node_project_variables_model: NodeProjectVariablesModel,
        config_node_project_service_model: ConfigNodeProjectServiceModel,
        params: T,
        service_name: str,
        service_instance_name: str,
        service_container_name: str,
        node_address: IPAddress,
        dependencies: list[str],
    ):
        self._group_variables_model = group_variables_model
        self._group_projects_variables_model = group_projects_variables_model
        self._node_project_variables_model = node_project_variables_model
        self._config_node_project_service_model = config_node_project_service_model
        self._params = params
        self._params_extra: dict[str, object] = {}
        self._service_name = service_name
        self._service_instance_name = service_instance_name
        self._service_container_name = service_container_name
        self._node_address = node_address
        self._dependencies = dependencies

        self._scripts: dict[str, NodeProjectServiceScriptModel] = {}
        self._spec_model = self.spec()
        self._image_tag = self._spec_model.upstream_tag
        if config_node_project_service_model.tag is not None:
            if self._spec_model.upstream_tag_force:
                raise ValueError(
                    f"{service_instance_name}: tag is fixed to {self._spec_model.upstream_tag}",
                )
            self._image_tag = config_node_project_service_model.tag

        self._compose = NodeProjectServiceComposeModel(
            common=NodeProjectServiceComposeCommonModel(
                container_name=self._service_container_name,
                image=f"{group_variables_model.registry_url}/{self._service_name}:{self._image_tag}",
                restart="no",
                environment={}
                | (
                    {
                        self._spec_model.add_timezone
                        or "TZ": self._group_variables_model.config.timezone
                    }
                    if self._spec_model is not None
                    else {}
                ),
                volumes=[]
                + (
                    [
                        {
                            "source": "/var/run/docker.sock",
                            "target": "/var/run/docker.sock",
                            "type": "bind",
                        }
                    ]
                    if self._spec_model.add_dockersocket
                    else []
                ),
            ),
            extra={
                "extra_hosts": []
                + (
                    ["host.docker.internal:host-gateway"]
                    if self._spec_model.add_dockerhost
                    else []
                ),
                "group_add": []
                + (
                    ["${HOMELAB_DOCKER_GROUP:?HOMELAB_DOCKER_GROUP is missing}"]
                    if self._spec_model.add_dockergroup
                    else []
                ),
                "logging": {
                    "options": {
                        "tag": "homelab",
                    },
                },
            },
        )

        # if config_node_project_service_model.dns is not None:
        #     self._compose.extra.update(
        #         dns=config_node_project_service_model.dns,
        #     )

        # limits
        self._compose.extra.update(
            {
                "deploy": {
                    "resources": {
                        "limits": config_node_project_service_model.limits.model_dump(),
                    },
                },
            },
        )
        #
        # update project variables model
        self._create_workspace()

    @property
    def image(self) -> NodeProjectServiceImageModel:
        return NodeProjectServiceImageModel(
            name=self._service_name,
            tag=self._image_tag,
            source=f"{self._spec_model.upstream}:{self._image_tag}",
        )

    def _resolve_address(
        self,
        param: str,
        param_value: NetworkAddress | None = None,
    ) -> NetworkAddressResolved:
        address: NetworkAddress = param_value or cast(
            NetworkAddress, getattr(self._params, param)
        )
        resolved = ServiceHelper.resolve_address(
            address,
            self._group_variables_model.config,
            self._group_projects_variables_model.networks,
            self._node_project_variables_model.node_name,
        )
        self._params_extra.update({f"{param}_resolved": resolved.model_dump()})
        return resolved

    def _resolve_addresses(
        self,
        param: str,
    ) -> list[NetworkAddressResolved]:
        results: list[NetworkAddressResolved] = []
        for address in cast(NetworkAddresses, getattr(self._params, param)):
            resolved = ServiceHelper.resolve_address(
                address,
                self._group_variables_model.config,
                self._group_projects_variables_model.networks,
                self._node_project_variables_model.node_name,
            )
            results.append(resolved)
        self._params_extra.update(
            {f"{param}_resolved": [result.model_dump() for result in results]}
        )
        return results

    def _resolve_addresses_nested(
        self,
        param: str,
    ) -> dict[str, list[NetworkAddressResolved]]:
        results: dict[str, list[NetworkAddressResolved]] = {}

        for name, addresses in cast(
            NetworkAddressesMapList, getattr(self._params, param)
        ).items():
            result: list[NetworkAddressResolved] = []
            for address in addresses:
                resolved = ServiceHelper.resolve_address(
                    address,
                    self._group_variables_model.config,
                    self._group_projects_variables_model.networks,
                    self._node_project_variables_model.node_name,
                )
                result.append(resolved)
            results.update({name: result})
            self._params_extra.update(
                {f"{param}_{name}_resolved": [i.model_dump() for i in result]}
            )
        return results

    def _resolve_addresses_map(
        self,
        param: str,
    ) -> dict[str, NetworkAddressResolved]:
        results: dict[str, NetworkAddressResolved] = {}
        for name, address in cast(
            NetworkAddressesMap, getattr(self._params, param)
        ).items():
            resolved = ServiceHelper.resolve_address(
                address,
                self._group_variables_model.config,
                self._group_projects_variables_model.networks,
                self._node_project_variables_model.node_name,
            )
            results.update({name: resolved})
        self._params_extra.update(
            {
                f"{param}_resolved": {
                    name: result.model_dump() for name, result in results.items()
                }
            }
        )
        return results

    def _enable_healthcheck(
        self,
        test: list[str],
        interval: str | None = None,
        start_period: str | None = None,
    ):
        result = {
            "interval": interval or "10s",
            "start_period": start_period or "10s",
            "timeout": "5s",
            "retries": 5,
        }
        result.update(
            test=test,
        )
        self._compose.extra.update(
            healthcheck=result,
        )

    def _append_workspace_paths(self, workspace_source: str, mode: str):
        self._node_project_variables_model.workspaces_paths.append(
            NodeProjectWorkspacePathModel(
                mode=mode,
                path=workspace_source,
                owner=self._node_project_variables_model.workspaces_owners[
                    self._service_instance_name
                ].owner,
                group=self._node_project_variables_model.workspaces_owners[
                    self._service_instance_name
                ].group,
            ),
        )

    def _create_workspace(self):
        if not self._spec_model.workspace.mounts:
            return

        compose_volumes = {}

        self._node_project_variables_model.workspaces_owners.update(
            {
                self._service_instance_name: NodeProjectWorkspaceOwnerModel(
                    owner=self._spec_model.workspace.owner,
                    group=self._spec_model.workspace.group
                    if self._spec_model.workspace.group is not None
                    else self._spec_model.workspace.owner,
                    bump=self._spec_model.workspace.bump,
                ),
            },
        )

        self._node_project_variables_model.workspaces.update(
            {
                self._service_instance_name: {},
            },
        )
        for mount_source, mount in self._spec_model.workspace.mounts.items():
            volume_source_parts = [
                "ro" if mount.volume is None else "rw",
                self._service_instance_name,
                mount_source,
            ]

            volume_source = "-".join(volume_source_parts)
            workspace_source = (
                f"{self._node_project_variables_model.workspace}/{volume_source}"
            )

            # WORKSPACE MOUNT
            if mount.volume is None:
                if mount.create:
                    self._append_workspace_paths(
                        workspace_source,
                        "0755" if mount.mode is None else mount.mode,
                    )

                config_mount: dict[str, object] = {
                    "target": mount.target,
                    "read_only": True,
                    "type": "bind",
                    "source": workspace_source,
                }
                self._compose.common.volumes.append(config_mount)

                self._node_project_variables_model.workspaces[
                    self._service_instance_name
                ].update(
                    {
                        mount_source: NodeProjectWorkspaceModel(
                            target=mount.target,
                            source=workspace_source,
                        ),
                    },
                )
            # VOLUME
            else:
                config_volume: dict[str, object] = {
                    "target": mount.target,
                    "type": "volume",
                }
                compose_volume: dict[str, object] = {}
                # LOCAL OR REMOTE VOLUME
                mount_volume_param = (
                    getattr(self._params, mount.volume.param, None)
                    if mount.volume.param is not None
                    else None
                )
                if mount_volume_param is not None:
                    storage: NodeProjectServiceParamsStorageVolume = (
                        NodeProjectServiceParamsStorageVolumeAdapter.validate_python(
                            mount_volume_param
                        )
                    )
                    if isinstance(
                        storage, NodeProjectServiceParamsStorageVolumeFSModel
                    ):
                        storage_path = (
                            storage.path
                            if storage.exclusive
                            else f"{storage.path}/{self._node_project_variables_model.node_name}-{self._node_project_variables_model.project_name}-{mount_source}"
                        )
                        self._append_workspace_paths(
                            storage_path,
                            "0755" if mount.mode is None else mount.mode,
                        )
                        compose_volume.update(
                            {
                                "driver": "local",
                                "driver_opts": {
                                    "type": "none",
                                    "o": "bind",
                                    "device": storage_path,
                                },
                            }
                        )
                    elif isinstance(
                        storage, NodeProjectServiceParamsStorageVolumeNFSModel
                    ):
                        # storage_path must already exist with correct permission!
                        storage_path = (
                            storage.path
                            if storage.exclusive
                            else f"{storage.path}/{self._node_project_variables_model.node_name}-{self._node_project_variables_model.project_name}-{mount_source}"
                        )
                        nfs_version = storage.version or "4.1"
                        nfs_address = self._group_variables_model.config.hosts[
                            storage.host
                        ]
                        compose_volume.update(
                            {
                                "driver": "local",
                                "driver_opts": {
                                    "type": "nfs",
                                    "o": f"addr={nfs_address},nfsvers={nfs_version},timeo={storage.timeout * 10},hard,rw",
                                    "device": f":{storage_path}",
                                },
                            }
                        )
                    elif isinstance(
                        storage, NodeProjectServiceParamsStorageVolumeS3Model
                    ):
                        pass
                    else:
                        raise ValueError(f"Unknown storage type: {storage}")
                # WORKSPACE VOLUME
                else:
                    self._append_workspace_paths(
                        workspace_source,
                        "0755" if mount.mode is None else mount.mode,
                    )
                    compose_volume.update(
                        {
                            "driver": "local",
                            "driver_opts": {
                                "type": "none",
                                "o": "bind",
                                "device": workspace_source,
                            },
                        }
                    )

                    self._node_project_variables_model.workspaces[
                        self._service_instance_name
                    ].update(
                        {
                            mount_source: NodeProjectWorkspaceModel(
                                target=mount.target,
                                source=workspace_source,
                            ),
                        },
                    )
                compose_volumes.update(
                    {
                        volume_source: compose_volume,
                    },
                )
                config_volume.update(source=volume_source)
                self._compose.common.volumes.append(config_volume)

        self._node_project_variables_model.compose_volumes.update(
            compose_volumes,
        )

    def create_networks(self) -> GroupProjectsVariablesProjectServiceEndpoints:
        networks: GroupProjectsVariablesProjectServiceEndpoints = {}

        if self._spec_model.network:
            if (
                self._config_node_project_service_model.expose is not None
                and self._config_node_project_service_model.expose
            ):
                unknown_expose_names = set(
                    self._config_node_project_service_model.expose
                ) - set(self._spec_model.network)
                if unknown_expose_names:
                    raise ValueError(
                        f"{self._service_container_name}: unknown expose name(s), not in network target {unknown_expose_names}",
                    )

            for (
                network_target_name,
                network_target_config,
            ) in self._spec_model.network.items():
                address_internal = (
                    GroupProjectsVariablesServiceEndpointAddressInternalModel(
                        host=self._service_container_name,
                        port=network_target_config.port,
                    )
                )
                address_external: (
                    GroupProjectsVariablesServiceEndpointAddressExternalModel | None
                ) = None
                if self._config_node_project_service_model.expose is not None and (
                    network_target_name
                    in self._config_node_project_service_model.expose
                    or not self._config_node_project_service_model.expose
                ):
                    if self._config_node_project_service_model.expose:
                        expose_config: ConfigNodeProjectServiceExposeModel = (
                            self._config_node_project_service_model.expose[
                                network_target_name
                            ]
                        )
                        port_number_host: int | None = expose_config.port
                        if port_number_host is None:
                            port_number_host = network_target_config.port
                        address_external = (
                            GroupProjectsVariablesServiceEndpointAddressExternalModel(
                                host=expose_config.bind
                                if expose_config.bind is not None
                                else self._node_address,
                                port=port_number_host,
                            )
                        )

                        # expose ports in container
                        if expose_config.container_expose:
                            port_mapping = f"{address_external.address}:{network_target_config.port}"

                            if "tcp" in network_target_config.mode:
                                self._compose.common.ports.append(f"{port_mapping}/tcp")

                            if "udp" in network_target_config.mode:
                                self._compose.common.ports.append(f"{port_mapping}/udp")
                    else:
                        address_external = (
                            GroupProjectsVariablesServiceEndpointAddressExternalModel(
                                host=self._node_address,
                                port=network_target_config.port,
                            )
                        )

                networks.update(
                    {
                        network_target_name: GroupProjectsVariablesServiceEndpointModel(
                            external=address_external,
                            internal=address_internal,
                            target=network_target_config,
                        ),
                    },
                )

        if (
            self._config_node_project_service_model.expose is not None
            and not self._config_node_project_service_model.expose
        ):
            self._compose.common.ports.clear()
            self._compose.extra.update(network_mode="host")

        return networks

    def spec(self) -> NodeProjectServiceSpecModel:
        raise NotImplementedError

    def customize(self):
        if self._dependencies:
            self._compose.extra.update(
                depends_on={
                    service: {
                        "condition": "service_healthy",
                        # "condition": "service_started",
                        "restart": True,
                    }
                    for service in self._dependencies
                }
            )

        for name, script in self._scripts.items():
            self._node_project_variables_model.scripts.update(
                {
                    f"{self._service_instance_name}:{name}": script,
                },
            )

        self._node_project_variables_model.specs.update(
            {
                self._service_instance_name: self._spec_model.model_dump(),
            },
        )

        self._node_project_variables_model.params.update(
            {
                self._service_instance_name: self._params.model_dump()
                | self._params_extra,
            },
        )
        self._node_project_variables_model.compose_services.update(
            {
                self._service_instance_name: self._compose.model_dump(),
            },
        )
