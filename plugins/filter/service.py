from ansible_collections.homelab.nodes.plugins.module_utils.services import (
    ServiceHelper,
)


class FilterModule:
    def filters(self):
        return {
            "service_container_mount": ServiceHelper.container_mount,
        }
