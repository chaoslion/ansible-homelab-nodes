# from ..models.group import (
#     GroupProjectVariables,
# )
# from . import NodeProjectService
# from ..models.net import NetworkAddress, NetworkTargetModel, NetworkUrl
# from ..models.node import (
#     NodeProjectServiceParamsModel,
#     NodeProjectServiceParamsOpenIDModel,
#     NodeProjectServiceSpecModel,
#     NodeProjectServiceWorkspaceModel,
#     NodeProjectServiceWorkspaceMountModel,
#     NodeProjectServiceWorkspaceMountVolumeModel,
# )


# class ServiceParamsModel(NodeProjectServiceParamsModel):
#     jwt_secret: str
#     openid: NodeProjectServiceParamsOpenIDModel
#     postgres: NetworkAddress
#     url: NetworkUrl


# class Service(NodeProjectService):
#     def spec(self) -> NodeProjectServiceSpecModel:
#         return NodeProjectServiceSpecModel(
#             upstream="docker.io/donetick/donetick",
#             network={
#                 "http": NetworkTargetModel(
#                     port=2021,
#                 ),
#             },
#             workspace=NodeProjectServiceWorkspaceModel(
#                 mounts={
#                     "config": NodeProjectServiceWorkspaceMountModel(
#                         target="/config",
#                     ),
#                     "assets": NodeProjectServiceWorkspaceMountModel(
#                         target="/app/assets",
#                         volume=NodeProjectServiceWorkspaceMountVolumeModel(),
#                     ),
#                 },
#             ),
#         )

#     def customize(self, group_project_variables: GroupProjectVariables):
#         self._enable_feature_timezone()
#         self.append_environment(
#             DT_ENV="selfhosted",
#         )
#         self._resolve_address_param(
#             "postgres",
#             group_project_variables,
#         )
#         super().customize(group_project_variables)
