from collections.abc import Callable
from typing import NamedTuple, override




class ModbusConfig(NamedTuple):
    address: int
    name: str
    siblings: list[str]
    config: dict[str, object]
    domain: str = "sensor"


class DeviceConfig(object):
    def configs(self) -> list[ModbusConfig]:
        return []

    def generate(
        self,
        name: str,
        address: int,
        master: dict[str, object],
        customize: dict[str, object],
        name_func: Callable[[str], str],
    ):
        for config in self.configs():
            name_constructed = f"{name} {config.name}"
            entity = name_func(name_constructed.lower())
            entityid = f"{config.domain}.{entity}"
            sensor = {
                "address": config.address,
                "scan_interval": 60,
                "name": entity,
                "slave": address,
            }
            if config.siblings:
                sensor |= {
                    "virtual_count": len(config.siblings) - 1,
                }
                for sibling_index, sibling in enumerate(config.siblings):
                    customize.update(
                        {
                            f"{entityid}_{sibling_index}"
                            if sibling_index > 0
                            else entityid: {
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
                        entityid: {
                            "friendly_name": name_constructed.replace(
                                " ",
                                "",
                            ),
                        },
                    },
                )

            sensor |= config.config
            master_domain = f"{config.domain}s"
            if master_domain not in master:
                master |= {
                    master_domain: [],
                }
            master[master_domain].append(sensor)


class DeviceConfigDS100(DeviceConfig):
    @override
    def configs(self) -> list[ModbusConfig]:
        configs = [
            ModbusConfig(
                0x0400,
                "Voltage",
                [
                    "AN",
                    "BN",
                    "CN",
                    "AB",
                    "BC",
                    "CA",
                    "LN Average",
                    "LL Average",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "V",
                    "state_class": "measurement",
                    "device_class": "voltage",
                    "data_type": "int32",
                    "scale": 0.001,
                    "precision": 2,
                },
            ),
            ModbusConfig(
                0x0410,
                "Current",
                [
                    "A",
                    "B",
                    "C",
                    "N",
                    "Vector Sum",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "A",
                    "state_class": "measurement",
                    "device_class": "current",
                    "data_type": "int32",
                    "scale": 0.001,
                    "precision": 3,
                },
            ),
            ModbusConfig(
                0x041A,
                "Active Power",
                [
                    "A",
                    "B",
                    "C",
                    "Combined",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "W",
                    "state_class": "measurement",
                    "device_class": "power",
                    "data_type": "int32",
                    "precision": 0,
                },
            ),
            ModbusConfig(
                0x0422,
                "Apparent Power",
                [
                    "A",
                    "B",
                    "C",
                    "Combined",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "VA",
                    "state_class": "measurement",
                    "device_class": "apparent_power",
                    "data_type": "int32",
                    "precision": 0,
                },
            ),
            ModbusConfig(
                0x042A,
                "Reactive Power",
                [
                    "A",
                    "B",
                    "C",
                    "Combined",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "var",
                    "state_class": "measurement",
                    "device_class": "reactive_power",
                    "data_type": "int32",
                    "precision": 0,
                },
            ),
            ModbusConfig(
                0x0432,
                "Frequency",
                [
                    "A",
                    "B",
                    "C",
                    "Combined",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "Hz",
                    "state_class": "measurement",
                    "device_class": "frequency",
                    "data_type": "int16",
                    "scale": 0.1,
                    "precision": 1,
                },
            ),
            ModbusConfig(
                0x0436,
                "Phase Power Factor",
                [
                    "A",
                    "B",
                    "C",
                    "Combined",
                ],
                {
                    "input_type": "input",
                    "unit_of_measurement": "%",
                    "state_class": "measurement",
                    "device_class": "power_factor",
                    "data_type": "int16",
                    "scale": 0.001,
                    "precision": 3,
                },
            ),
            ModbusConfig(
                0x1004,
                "Version",
                [
                    "Software",
                    "Hardware",
                ],
                {
                    "input_type": "input",
                    "data_type": "int16",
                },
            ),
        ]

        for address, name in [
            (0x010E, "Energy Total Forward Active"),
            (0x0118, "Energy Total Reverse Active"),
            (0x0122, "Energy Total Active"),
            (0x012C, "Energy Total Forward Reactive"),
            (0x0136, "Energy Total Reverse Reactive"),
            (0x0140, "Energy Total Reactive"),
            # A
            (0x0500, "Energy A Total Active"),
            (0x050A, "Energy A Forward Active"),
            (0x0514, "Energy A Reverse Active"),
            (0x051E, "Energy A Total Reactive"),
            (0x0528, "Energy A Forward Reactive"),
            (0x0532, "Energy A Reverse Reactive"),
            # B
            (0x0564, "Energy B Total Active"),
            (0x056E, "Energy B Forward Active"),
            (0x0578, "Energy B Reverse Active"),
            (0x0582, "Energy B Total Reactive"),
            (0x058C, "Energy B Forward Reactive"),
            (0x0596, "Energy B Reverse Reactive"),
            # C
            (0x05C8, "Energy C Total Active"),
            (0x05D2, "Energy C Forward Active"),
            (0x05DC, "Energy C Reverse Active"),
            (0x05E6, "Energy C Total Reactive"),
            (0x05F0, "Energy C Forward Reactive"),
            (0x05FA, "Energy C Reverse Reactive"),
        ]:
            configs += [
                ModbusConfig(
                    address,
                    name,
                    [],
                    {
                        "input_type": "input",
                        "unit_of_measurement": "kWh",
                        "state_class": "total_increasing",
                        "device_class": "energy",
                        "data_type": "int32",
                        "scale": 0.01,
                        "precision": 2,
                    },
                ),
            ]
        return configs
