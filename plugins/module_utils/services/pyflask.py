# from pathlib import Path
# from typing import Any, Literal

# from . import (
#     NodeProjectService,
#     ServiceHelper,
# )
# from ..models.group import (
#     GroupProjectVariables,
# )
# from ..models.net import (
#     NetworkTargetModel,
# )
# from ..models.node import (
#     NodeProjectServiceParamsModel,
#     NodeProjectServiceSpecModel,
#     NodeProjectServiceWorkspaceModel,
#     NodeProjectServiceWorkspaceMountModel,
#     NodeProjectServiceWorkspaceMountVolumeModel,
# )


# class AppParams(NodeProjectServiceParamsModel):
#     name: str
#     params: dict[str, Any] = {}


# class ServiceParamsModel(NodeProjectServiceParamsModel):
#     app: AppParams
#     options: dict[str, Any] = {}


# class Service(NodeProjectService):
#     def spec(self) -> NodeProjectServiceSpecModel:
#         return NodeProjectServiceSpecModel(
#             upstream="docker.io/python",
#             upstream_tag="3.13-slim",
#             upstream_tag_force=True,
#             network={
#                 "http": NetworkTargetModel(
#                     port=8080,
#                 ),
#             },
#             workspace=NodeProjectServiceWorkspaceModel(
#                 bump="restart",
#                 mounts={
#                     "data": NodeProjectServiceWorkspaceMountModel(
#                         target=ServiceHelper.container_mount("data"),
#                         volume=NodeProjectServiceWorkspaceMountVolumeModel(),
#                     ),
#                     "package": NodeProjectServiceWorkspaceMountModel(
#                         target=ServiceHelper.container_mount("package"),
#                     ),
#                 },
#             ),
#         )

#     def customize(self, group_project_variables: GroupProjectVariables):
#         self._enable_feature_healthcheck(
#             [
#                 "CMD",
#                 "curl",
#                 "-f",
#                 f"http://localhost:{self._spec_model.network['http'].port}/health",
#             ],
#         )

#         self._compose.extra.update(
#             command=[
#                 "gunicorn",
#                 "-w4",
#                 "-b",
#                 f"0.0.0.0:{self._spec_model.network['http'].port}",
#                 "--chdir",
#                 self._spec_model.workspace.mounts["package"].target,
#                 "package.server:create_app('WARN')",
#             ],
#         )
#         super().customize(group_project_variables)
