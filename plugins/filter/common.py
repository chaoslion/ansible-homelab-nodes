import functools

from ansible.plugins.filter.core import to_nice_json, to_nice_yaml


class FilterModule:
    def filters(self):
        return {
            "to_yaml": functools.partial(to_nice_yaml, indent=2),
            "to_json": functools.partial(to_nice_json, indent=2),
        }
