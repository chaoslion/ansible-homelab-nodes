import importlib
from pathlib import Path
from typing import cast

import pydantic
import yaml
from ansible.plugins import AnsibleError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible_collections.homelab.nodes.plugins.module_utils.models.common import (
    CONTAINER_NAME_MAIN,
    CONTAINER_PREFIX,
)
from ansible_collections.homelab.nodes.plugins.module_utils.models.config import (
    ConfigModel,
    ConfigNodeModel,
    ConfigNodeProjectServiceModel,
)
from ansible_collections.homelab.nodes.plugins.module_utils.models.group import (
    GroupProjectsVariablesProjectsServicesEndpoints,
    GroupProjectVariablesModel,
    GroupsModel,
    GroupVariablesModel,
)
from ansible_collections.homelab.nodes.plugins.module_utils.models.net import IPAddress
from ansible_collections.homelab.nodes.plugins.module_utils.models.node import (
    NodeProjectServiceImageModel,
    NodeProjectServiceParamsModel,
    NodeProjectVariablesModel,
    NodeVariablesModel,
)
from ansible_collections.homelab.nodes.plugins.module_utils.services import (
    NodeProjectService,
    ServiceHelper,
)

DOCUMENTATION = r"""
  name: homelab.nodes.inventory
  options:
    plugin:
      required: true
      choices: [homelab.nodes.inventory]
    config:
      type: "dict"
      required: true
    cache_path:
      type: "str"
      default: "cache-homelab-nodes"
  extends_documentation_fragment:
    - constructed
"""


class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = "homelab.nodes.inventory"

    def verify_file(self, path):
        ppath = Path(path)
        return (
            super().verify_file(path)
            and ppath.suffix in {".yaml", ".yml"}
            and ppath.stem == "homelab"
        )

    def _homelab_groups(self) -> GroupsModel:
        prefix = "homelab_nodes"
        return GroupsModel(
            group=f"group_{prefix}",
            group_hosts=f"group_{prefix}_hosts",
            group_hosts_virt=f"group_{prefix}_hosts_virt",
            group_projects=f"group_{prefix}_projects",
            group_images=f"group_{prefix}_images",
            group_supervisors=f"group_{prefix}_supervisors",
            prefix=prefix,
        )

    def _homelab_create_group_variable_name(self, group: str, name: str):
        return f"vars_{group}__{name}"

    def _homelab_create_inventory_variables(
        self,
        inventory: str,
        group: str,
        variables,
        prefix: str | None = None,
    ):
        for key, value in variables.items():
            if prefix is not None:
                key = f"{prefix}_{key}"
            self.inventory.set_variable(
                inventory,
                self._homelab_create_group_variable_name(group, key),
                value,
            )

    # remove "group_" prefix and "s" suffix
    def _homelab_create_inventory_from_group(
        self,
        group: str,
        name: str,
        host: str | None = None,
        inventory_group_strip_plural: bool = True,
        inventory_group_override: str | None = None,
    ) -> str:
        inventory_group = group[6:]
        if inventory_group_strip_plural:
            inventory_group = inventory_group[:-1]
        inventory = f"{inventory_group}__{name}"
        self.inventory.add_host(
            inventory,
            group if inventory_group_override is None else inventory_group_override,
        )
        if host is not None:
            self.inventory.set_variable(
                inventory,
                "ansible_host",
                host,
            )
        else:
            self.inventory.set_variable(
                inventory,
                "ansible_connection",
                "local",
            )
        return inventory

    def _homelab_create_node(
        self,
        node_name: str,
        node_address: IPAddress,
        node_model: ConfigNodeModel,
        group_projects_variables_model: GroupProjectVariablesModel,
    ):
        node_inventory = self._homelab_create_inventory_from_group(
            self._homelab_groups_model.group_hosts,
            node_name.replace("-", "_"),
            f"{node_address}",
            inventory_group_override=(
                self._homelab_groups_model.group_hosts_virt
                if node_model.supervisor is not None
                else None
            ),
        )

        group_projects_variables_model.nodes.update(
            {
                node_name: node_inventory,
            },
        )

        self.inventory.set_variable(
            node_inventory,
            "ansible_user",
            self._homelab_group_variables_model.config.admin.name,
        )

        node_workspace = (
            Path("/home")
            / self._homelab_group_variables_model.config.admin.name
            / "workspace"
        )
        node_variables_model: NodeVariablesModel = NodeVariablesModel(
            # cache=str(node_cache),
            config=node_model.model_copy(deep=True),
            hostname=f"node-{node_name.replace('_', '-')}",
            name=node_name,
            workspace=str(node_workspace),
        )
        supervisor_variables: dict[str, str | int | list[str]] = {}
        if node_model.supervisor is not None:
            if self._homelab_group_variables_model.config.supervisors is None:
                raise AnsibleError(f"node requires supervisors: f{node_name}")
            vmid_offset = 0
            if (
                self._homelab_group_variables_model.config.supervisors.offset
                is not None
            ):
                vmid_offset = (
                    self._homelab_group_variables_model.config.supervisors.offset
                )
            supervisor_variables.update(
                supervisor_vmid=vmid_offset + node_model.supervisor.index,
            )
            supervisor_qemu = (
                self._homelab_group_variables_model.config.supervisors.hosts[
                    node_model.supervisor.name
                ].config
                # node_model.supervisor.config
                # if node_model.supervisor.override
                # else self._homelab_group_variables_model.config.supervisors.hosts[
                #     node_model.supervisor.name
                # ].config
                # | node_model.supervisor.config
            )
            supervisor_variables.update(
                supervisor_qemu=[
                    f"--{key}={value}" for key, value in supervisor_qemu.items()
                ]
            )

        self._homelab_create_inventory_variables(
            node_inventory,
            self._homelab_groups_model.group_hosts.replace("group", "host"),
            {
                "config": node_variables_model.model_dump(mode="json"),
            }
            | supervisor_variables,
        )

        node_networks: GroupProjectsVariablesProjectsServicesEndpoints = {}
        group_projects_variables_model.networks.update(
            {
                node_name: node_networks,
            },
        )

        for project_name, project in node_model.projects.items():
            node_networks.update({project_name: {}})
            node_project_id = f"{node_name}__{project_name.replace('-', '_')}"
            node_project_variables_model: NodeProjectVariablesModel = (
                NodeProjectVariablesModel(
                    id=node_project_id,
                    urn=node_project_id.replace("__", "-").replace("_", "-"),
                    node_name=node_name,
                    project_name=project_name,
                    workspace=str(node_workspace / f"homelab-{project_name}"),
                    workspace_root=str(node_workspace),
                )
            )

            node_project_services: dict[str, ConfigNodeProjectServiceModel] = {
                CONTAINER_NAME_MAIN: project.service,
                **{
                    service_name: service
                    for service_name, service in project.dependencies.items()
                },
            }

            service_name_mapping = {
                CONTAINER_NAME_MAIN: project.service.service
                if project.service.service is not None
                else project.name or project_name,
                **{
                    name: config.service if config.service is not None else name
                    for name, config in project.dependencies.items()
                },
            }
            for (
                node_project_service_instance_name,
                config_node_project_service_model,
            ) in node_project_services.items():
                service_name = service_name_mapping[
                    node_project_service_instance_name
                ].replace("-", "_")
                # project_roles.insert(
                #     0,
                #     (
                #         roles_path / f"service_{service_name}",
                #         node_project_service_instance_name,
                #     ),
                # )
                service_module = importlib.import_module(
                    f"ansible_collections.homelab.nodes.plugins.module_utils.services.{service_name}"
                )
                node_project_service_factory: type[NodeProjectService] = (
                    service_module.Service
                )
                node_project_service_params_model_factory: type[
                    NodeProjectServiceParamsModel
                ] = service_module.ServiceParamsModel

                try:
                    node_project_service_params_model = (
                        node_project_service_params_model_factory(
                            **config_node_project_service_model.params
                        )
                    )
                except pydantic.ValidationError as exc0:
                    raise AnsibleError(
                        f"error validating project service: {node_project_variables_model.node_name}/{node_project_variables_model.project_name}/{node_project_service_instance_name}",
                        orig_exc=exc0,
                    )

                # node_project_service_container_name = ServiceHelper.container_name(
                #     node_project_variables_model.project_name,
                #     node_project_service_instance_name,
                # )
                node_project_variables_model.containers.update(
                    {
                        node_project_service_instance_name: node_project_service_instance_name,
                    }
                )

                node_project_service: NodeProjectService = node_project_service_factory(
                    self._homelab_group_variables_model,
                    group_projects_variables_model,
                    node_project_variables_model,
                    config_node_project_service_model,
                    node_project_service_params_model,
                    service_name,
                    node_project_service_instance_name,
                    f"{CONTAINER_PREFIX}-{project_name}-{node_project_service_instance_name}",
                    node_address,
                    list(set(service_name_mapping) - set({CONTAINER_NAME_MAIN}))
                    if node_project_service_instance_name == CONTAINER_NAME_MAIN
                    else [],
                )

                node_networks[project_name].update(
                    {
                        node_project_service_instance_name: node_project_service.create_networks()
                    }
                )

                if node_name not in self._homelab_services:
                    self._homelab_services.update(
                        {
                            node_name: [],
                        },
                    )
                self._homelab_services[node_name].append(node_project_service)

            project_inventory = self._homelab_create_inventory_from_group(
                self._homelab_groups_model.group_hosts,
                node_project_id,
                f"{node_address}",
                inventory_group_override=self._homelab_groups_model.group_projects,
            )

            self._homelab_projects.update(
                {
                    project_inventory: node_project_variables_model,
                }
            )

    def _homelab_create_image(
        self,
        inventory_images: list[str],
        image: NodeProjectServiceImageModel,
    ):
        if image.id in inventory_images:
            return
        image_inventory = self._homelab_create_inventory_from_group(
            self._homelab_groups_model.group_images,
            image.id,
        )
        self._homelab_create_inventory_variables(
            image_inventory,
            self._homelab_groups_model.group_images.replace("group", "host"),
            image.model_dump(mode="json"),
        )
        inventory_images.append(image.id)

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)

        self._read_config_data(path)

        config = cast(dict[str, object], self.get_option("config"))
        try:
            config_model = ConfigModel.model_validate(config)
        except pydantic.ValidationError as exc0:
            raise AnsibleError(
                "error validating config",
                orig_exc=exc0,
            ) from exc0

        self._homelab_groups_model = self._homelab_groups()
        self.inventory.add_group(self._homelab_groups_model.group)
        self.inventory.add_group(self._homelab_groups_model.group_hosts)
        self.inventory.add_group(self._homelab_groups_model.group_hosts_virt)
        self.inventory.add_group(self._homelab_groups_model.group_projects)
        self.inventory.add_group(self._homelab_groups_model.group_images)
        self.inventory.add_group(self._homelab_groups_model.group_supervisors)

        self.inventory.add_child(
            self._homelab_groups_model.group, self._homelab_groups_model.group_hosts
        )
        self.inventory.add_child(
            self._homelab_groups_model.group_hosts,
            self._homelab_groups_model.group_hosts_virt,
        )
        self.inventory.add_child(
            self._homelab_groups_model.group, self._homelab_groups_model.group_projects
        )
        self.inventory.add_child(
            self._homelab_groups_model.group, self._homelab_groups_model.group_images
        )
        self.inventory.add_child(
            self._homelab_groups_model.group,
            self._homelab_groups_model.group_supervisors,
        )

        self._homelab_create_inventory_from_group(
            self._homelab_groups_model.group,
            "local",
            inventory_group_strip_plural=False,
        )

        # create supervisors
        supervisor_inventories = {}
        if config_model.supervisors is not None:
            for (
                supervisor_name,
                supervisor_config,
            ) in config_model.supervisors.hosts.items():
                supervisor_inventory = self._homelab_create_inventory_from_group(
                    self._homelab_groups_model.group_supervisors,
                    supervisor_name,
                    str(supervisor_config.host),
                )
                self.inventory.set_variable(
                    supervisor_inventory,
                    "ansible_user",
                    "root",
                )
                supervisor_inventories.update(
                    {
                        supervisor_name: supervisor_inventory,
                    },
                )

        cache_path = Path(self.get_option("cache_path")).absolute()
        cache_path.mkdir(parents=True, exist_ok=True)
        registry_domain = "homelab-registry"
        registry_url = f"{registry_domain}:{config_model.registry.port}"
        registry_url_push = registry_url.replace(registry_domain, "localhost")
        content_path = Path(config_model.content).absolute()
        self._homelab_group_variables_model: GroupVariablesModel = GroupVariablesModel(
            cache=str(cache_path),
            ca_path=str(content_path / "ca"),
            roles_path=str(content_path / "roles"),
            config=config_model,
            container_prefix=CONTAINER_PREFIX,
            registry_address=config_model.registry.address,
            registry_domain=registry_domain,
            registry_url=registry_url,
            registry_url_push=registry_url_push,
            supervisor_inventories=supervisor_inventories,
            supervisor_groups={
                "low": 0.25,
                "mid": 0.50,
                "high": 0.75,
                "max": 1.0,
            },
        )

        self._homelab_services: dict[str, list[NodeProjectService]] = {}
        self._homelab_projects: dict[str, NodeProjectVariablesModel] = {}
        group_projects_variables_model = GroupProjectVariablesModel()

        for node_name, node_address in config_model.hosts.items():
            if not node_name.startswith("node-"):
                continue

            node_config_path = content_path / f"{node_name}.yaml"
            try:
                node_config = yaml.full_load(node_config_path.read_text())
            except yaml.YAMLError as exc1:
                raise AnsibleError(
                    f"error parsing node: {node_config_path}",
                    orig_exc=exc1,
                ) from exc1
            try:
                node_model = ConfigNodeModel.model_validate(node_config)
            except pydantic.ValidationError as exc2:
                raise AnsibleError(
                    f"error validating node: {node_config_path}",
                    orig_exc=exc2,
                ) from exc2

            self._homelab_create_node(
                node_name.replace("node-", ""),
                node_address,
                node_model,
                group_projects_variables_model,
            )

        group_variables = self._homelab_group_variables_model.model_dump(mode="json")

        def __calc_fqdn(domain: str, subdomains: list[str]) -> dict[str, object]:
            fqdns = [
                f"{subdomain}.{domain}" if subdomain != "@" else domain
                for subdomain in subdomains
            ]
            fqdn = max(fqdns, key=len) if fqdns else domain
            return {
                "fqdn": fqdn,
                "fqdns": fqdns,
                "id": fqdn.replace(".", "-"),
            }

        # eval websites targets and inject into group_variables
        if self._homelab_group_variables_model.config.websites:
            for index, website in enumerate(
                self._homelab_group_variables_model.config.websites.sites
            ):
                website_config = group_variables["config"]["websites"]["sites"][index]
                if website.homepage is not None:
                    if (
                        website.homepage.description is not None
                        and website.homepage.auth in {"admin", "sso/admin"}
                    ):
                        website_config["homepage"].update(
                            description=f"{website.homepage.description} ({self._homelab_group_variables_model.config.admin.name}:{self._homelab_group_variables_model.config.admin.password})",
                        )
                    if website.homepage.group is None:
                        website_config["homepage"].update(
                            group=self._homelab_group_variables_model.config.websites.default_homepage_group.value,
                        )

                website_config.update(
                    domains={
                        domain: __calc_fqdn(
                            domain,
                            [website.id]
                            + (
                                website.proxy.router
                                if website.proxy is not None
                                and website.proxy.router is not None
                                else []
                            ),
                        )
                        for domain in website.domains
                    },
                )

                if website.proxy is not None and not isinstance(
                    website.proxy.service, str
                ):
                    website_config["proxy"]["service"].update({"servers_resolved": {}})

                    for (
                        service_name,
                        service_servers,
                    ) in website.proxy.service.servers.items():
                        servers = []
                        for server in service_servers:
                            addresses = ServiceHelper.resolve_addresses(
                                server,
                                self._homelab_group_variables_model.config,
                                group_projects_variables_model.networks,
                            )
                            if isinstance(addresses, tuple):
                                node_name, internal, external = addresses
                                servers.append(
                                    (
                                        node_name,
                                        internal.model_dump(mode="json"),
                                        external.model_dump(mode="json")
                                        if external
                                        else None,
                                    ),
                                )
                            else:
                                servers.append(
                                    addresses.model_dump(mode="json"),
                                )
                        website_config["proxy"]["service"]["servers_resolved"].update(
                            {
                                service_name: servers,
                            },
                        )

        self._homelab_create_inventory_variables(
            self._homelab_groups_model.group,
            self._homelab_groups_model.group,
            group_variables,
        )

        self._homelab_create_inventory_variables(
            self._homelab_groups_model.group_projects,
            self._homelab_groups_model.group_projects,
            group_projects_variables_model.model_dump(mode="json"),
        )

        # used to check for duplicated images
        inventory_images: list[str] = []
        for inventory_services in self._homelab_services.values():
            for inventory_service in inventory_services:
                # call service customize
                inventory_service.customize()
                # add service image
                self._homelab_create_image(
                    inventory_images,
                    inventory_service.image,
                )

        for (
            project_inventory,
            node_project_variables_model,
        ) in self._homelab_projects.items():
            self._homelab_create_inventory_variables(
                project_inventory,
                self._homelab_groups_model.group_projects.replace("group", "host"),
                node_project_variables_model.model_dump(mode="json"),
            )

        # add config images
        for (
            config_image_name,
            config_image_upstream,
        ) in config_model.registry.images.items():
            try:
                _, image_tag = config_image_upstream.rsplit(":", maxsplit=1)
            except ValueError:
                image_tag = "latest"
            image: NodeProjectServiceImageModel = NodeProjectServiceImageModel(
                name=config_image_name,
                tag=image_tag,
                source=config_image_upstream,
            )
            self._homelab_create_image(
                inventory_images,
                image,
            )
