from collections.abc import Callable
from typing import NamedTuple

import yaml


class ModbusConfig(NamedTuple):
    address: int
    name: str
    siblings: list[str]
    config: dict[str, object]
    domain: str = "sensor"


def modbus_generate_slave(
    slave_topology: dict[str, object],
    slave_address: int,
    customize: dict[str, object],
    master: dict[str, object],
    slave_name: str,
    name_func: Callable[[str], str],
):
    for domain, channels in slave_topology.items():
        domain_config = []
        for channel in channels:
            name_constructed = f"{slave_name} {channel['name']}"
            entity_id = name_func(name_constructed.lower())
            channel_result = {
                "slave": slave_address,
                "address": channel["address"],
                "scan_interval": 60,
                "name": entity_id,
            }
            domain_config.append(channel_result)
            channel_result.update(channel["attributes"])
            channel_result.update({})
            if channel["siblings"]:
                channel_result.update({"virtual_count": len(channel["siblings"]) - 1})
                for sibling_index, sibling in enumerate(channel["siblings"]):
                    customize.update(
                        {
                            f"{domain}.{entity_id}_{sibling_index}"
                            if sibling_index > 0
                            else f"{domain}.{entity_id}": {
                                "friendly_name": f"{name_constructed}{sibling}".replace(
                                    " ",
                                    "",
                                ),
                            },
                        },
                    )
            else:
                customize.update(
                    {
                        f"{domain}.{entity_id}": {
                            "friendly_name": name_constructed.replace(
                                " ",
                                "",
                            ),
                        },
                    },
                )

        if domain not in master:
            master.update({domain: []})
        master[domain].extend(domain_config)


class FilterModule:
    def filters(self):
        return {
            "homeassistant_modbus": self._homeassistant_modbus,
        }

    def _homeassistant_modbus(self, topology, slaves_topology):
        modbus_config = []
        customize_config = {}
        result = {
            "modbus": modbus_config,
            "homeassistant": {
                "customize": customize_config,
            },
        }
        for name, master, slaves in (master.values() for master in topology):
            master_config = {
                "name": name,
                **master,
            }
            modbus_config += [master_config]
            for slave_name, slave_config in slaves.items():
                modbus_generate_slave(
                    slaves_topology[slave_config["device"]],
                    slave_config["address"],
                    customize_config,
                    master_config,
                    slave_name,
                    lambda i: self._homeassistant_name(i),
                )

        return yaml.safe_dump(result)
