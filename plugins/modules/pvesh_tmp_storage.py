#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec={
            "name": {
                "required": True,
                "type": "str",
            },
        },
        supports_check_mode=False,
    )

    _, stdout, _ = module.run_command(
        [
            "pvesh",
            "get",
            "/storage",
            "--output-format=json",
        ],
        check_rc=True,
    )

    storages = module.from_json(stdout)
    if module.params["name"] in map(lambda p: p["storage"], storages):
        module.exit_json(
            changed=False,
        )

    module.run_command(
        [
            "pvesh",
            "create",
            "/storage",
            "--storage",
            module.params["name"],
            "--type",
            "dir",
            "--content",
            "snippets",
            "--path",
            "/tmp/" + module.params["name"],
        ],
        check_rc=True,
    )

    module.exit_json(
        changed=True,
    )


if __name__ == "__main__":
    main()
