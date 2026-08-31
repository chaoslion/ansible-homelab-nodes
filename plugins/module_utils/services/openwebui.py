# from ..models.group import (
#     GroupProjectVariables,
# )
# from . import NodeProjectService
# from ..models.net import (
#     NetworkUrl,
#     NetworkTargetModel,
# )
# from ..models.node import (
#     NodeProjectServiceParamsModel,
#     NodeProjectServiceParamsOpenIDModel,
#     NodeProjectServiceSpecModel,
#     NodeProjectServiceWorkspaceModel,
#     NodeProjectServiceWorkspaceMountModel,
#     NodeProjectServiceWorkspaceMountVolumeModel,
# )


# class ServiceParamsModel(NodeProjectServiceParamsModel):
#     openid: NodeProjectServiceParamsOpenIDModel
#     url: NetworkUrl
#     upload_limit: int


# class Service(NodeProjectService):
#     def spec(self) -> NodeProjectServiceSpecModel:
#         return NodeProjectServiceSpecModel(
#             upstream="ghcr.io/open-webui/open-webui",
#             network={
#                 "http": NetworkTargetModel(
#                     port=8080,
#                 ),
#             },
#             workspace=NodeProjectServiceWorkspaceModel(
#                 mounts={
#                     "data": NodeProjectServiceWorkspaceMountModel(
#                         target="/app/backend/data",
#                         volume=NodeProjectServiceWorkspaceMountVolumeModel(),
#                     ),
#                 },
#             ),
#         )

#     def customize(
#         self,
#         group_project_variables: GroupProjectVariables,
#     ):
#         self._compose.common.environment.update(
#             BYPASS_MODEL_ACCESS_CONTROL="true",
#             DEFAULT_USER_ROLE="user",
#             ENABLE_ADMIN_CHAT_ACCESS="false",
#             ENABLE_ADMIN_EXPORT="false",
#             ENABLE_OAUTH_SIGNUP="true",
#             OAUTH_CLIENT_ID=self._params["openid"]["client_id"],
#             OAUTH_CLIENT_SECRET=self._params["openid"]["client_secret"],
#             OAUTH_PROVIDER_NAME=self._params["openid"]["name"],
#             OPENID_PROVIDER_URL=self._params["openid"]["url_well_known"],
#             WEBUI_ADMIN_EMAIL=self._group_variables_model.config.admin.mail,
#             WEBUI_ADMIN_NAME=self._group_variables_model.config.admin.name,
#             WEBUI_ADMIN_PASSWORD=self._group_variables_model.config.admin.password,
#             RAG_FILE_MAX_SIZE=self._params["upload_limit"],
#             RAG_FILE_MAX_COUNT=1,
#             FOLDER_MAX_FILE_COUNT=1,
#             WEBUI_URL=self._params["url"]["value"],
#         )
#         super().customize(group_project_variables)
