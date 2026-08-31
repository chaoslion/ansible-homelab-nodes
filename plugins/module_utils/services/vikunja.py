# from ..models.net import (
#     NetworkAddress,
#     NetworkTargetModel,
#     NetworkUrl,
# )
# from ..models.node import (
#     NodeProjectServiceParamsModel,
#     NodeProjectServiceParamsOpenIDModel,
#     NodeProjectServiceParamsStorageVolume,
#     NodeProjectServiceSpecModel,
#     NodeProjectServiceWorkspaceModel,
#     NodeProjectServiceWorkspaceMountModel,
#     NodeProjectServiceWorkspaceMountVolumeModel,
# )
# from . import (
#     NodeProjectService,
# )


# class ServiceParamsModel(NodeProjectServiceParamsModel):
#     data: NodeProjectServiceParamsStorageVolume | None = None
#     jwt_secret: str
#     openid: NodeProjectServiceParamsOpenIDModel
#     postgres: NetworkAddress
#     redis: NetworkAddress
#     upload_limit: int
#     url: NetworkUrl


# class Service(NodeProjectService):
#     def spec(self) -> NodeProjectServiceSpecModel:
#         return NodeProjectServiceSpecModel(
#             upstream="docker.io/vikunja/vikunja",
#             network={
#                 "http": NetworkTargetModel(
#                     port=3456,
#                 ),
#             },
#             workspace=NodeProjectServiceWorkspaceModel(
#                 mounts={
#                     "config": NodeProjectServiceWorkspaceMountModel(
#                         target="/etc/vikunja",
#                         volume=None,
#                     ),
#                     "data": NodeProjectServiceWorkspaceMountModel(
#                         target="/app/vikunja/files",
#                         volume=NodeProjectServiceWorkspaceMountVolumeModel(
#                             param="data",
#                         ),
#                     ),
#                 },
#                 owner=1000,
#             ),
#         )

#     def customize(self, group_project_variables: GroupProjectVariables):
#         self._enable_feature_timezone()
#         self._resolve_address_param(
#             "postgres",
#             group_project_variables,
#         )
#         self._resolve_address_param(
#             "redis",
#             group_project_variables,
#         )
#         self._compose.common.environment.update(
#             VIKUNJA_CACHE_ENABLED="1",
#             VIKUNJA_CACHE_TYPE="redis",
#         )
#         super().customize(group_project_variables)
