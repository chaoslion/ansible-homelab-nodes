import typing
from operator import add

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
    NetworkUrl,
)
from ..models.node import (
    NodeProjectServiceParamsModel,
    NodeProjectServiceSpecModel,
    NodeProjectServiceWorkspaceModel,
    NodeProjectServiceWorkspaceMountModel,
    NodeProjectServiceWorkspaceMountVolumeModel,
)
from . import NodeProjectService


class ServiceParamsModel(NodeProjectServiceParamsModel):
    adapter: NetworkAddress
    channel: int
    mqtt: NetworkAddress
    power: int | None = None
    url: NetworkUrl


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="docker.io/koenkk/zigbee2mqtt",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=8080,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/app/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_adapter = self._resolve_address("adapter")
        param_mqtt = self._resolve_address("mqtt")
        self._compose.common.environment.update(
            ZIGBEE2MQTT_CONFIG_ADVANCED_CHANNEL=f"{self._params.channel}",
            ZIGBEE2MQTT_CONFIG_ADVANCED_LOG_OUTPUT='["console"]',
            ZIGBEE2MQTT_CONFIG_DEVICES="devices.yaml",
            ZIGBEE2MQTT_CONFIG_FRONTEND_ENABLED="true",
            ZIGBEE2MQTT_CONFIG_FRONTEND_HOST="0.0.0.0",
            ZIGBEE2MQTT_CONFIG_FRONTEND_PORT="8080",
            ZIGBEE2MQTT_CONFIG_FRONTEND_URL=f"{self._params.url}",
            ZIGBEE2MQTT_CONFIG_GROUPS="groups.yaml",
            ZIGBEE2MQTT_CONFIG_MQTT_SERVER=f"mqtt://{param_mqtt.address}",
            ZIGBEE2MQTT_CONFIG_SERIAL_ADAPTER="zstack",
            ZIGBEE2MQTT_CONFIG_SERIAL_BAUDRATE="115200",
            ZIGBEE2MQTT_CONFIG_SERIAL_PORT=f"tcp://{param_adapter.address}",
        )
        if self._params.power is not None:
            self._compose.common.environment.update(
                ZIGBEE2MQTT_CONFIG_ADVANCED_TRANSMIT_POWER=f"{self._params.power}",
            )

        super().customize()
