import typing

from ..models.net import (
    NetworkAddress,
    NetworkTargetModel,
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
    email: str
    key: str
    mqtt: NetworkAddress


class Service(NodeProjectService[ServiceParamsModel]):
    @typing.override
    def spec(self) -> NodeProjectServiceSpecModel:
        return NodeProjectServiceSpecModel(
            upstream="ghcr.io/wez/govee2mqtt",
            add_timezone="",
            network={
                "http": NetworkTargetModel(
                    port=8056,
                ),
            },
            workspace=NodeProjectServiceWorkspaceModel(
                mounts={
                    "data": NodeProjectServiceWorkspaceMountModel(
                        target="/data",
                        volume=NodeProjectServiceWorkspaceMountVolumeModel(),
                    ),
                },
                owner=1000,
            ),
        )

    @typing.override
    def customize(
        self,
    ):
        param_mqtt = self._resolve_address("mqtt")
        self._compose.common.environment.update(
            GOVEE_MQTT_HOST=f"{param_mqtt.host}",
            GOVEE_MQTT_PORT=f"{param_mqtt.port}",
            GOVEE_EMAIL=self._params.email,
            GOVEE_API_KEY=self._params.key,
            GOVEE_TEMPERATURE_SCALE="C",
        )
        super().customize()
