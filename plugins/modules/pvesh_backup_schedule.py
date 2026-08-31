#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec={
            "name": {
                "required": True,
                "type": "str",
            },
            "options": {
                "required": True,
                "type": "dict",
            },
        },
        supports_check_mode=False,
    )

    _, stdout, _ = module.run_command(
        [
            "pvesh",
            "get",
            "/cluster/backup",
            "--output-format=json",
        ],
        check_rc=True,
    )

    backups = module.from_json(stdout)
    backupid = module.params["name"].replace(" ", "-").lower()
    if backupid in map(lambda p: p["id"], backups):
        module.exit_json(
            changed=False,
        )

    module.run_command(
        [
            "pvesh",
            "create",
            "/cluster/backup",
            "--id",
            backupid,
            "--comment",
            module.params["name"],
        ]
        + [f"--{k}={v}" for k, v in module.params["options"].items()],
        check_rc=True,
    )

    module.exit_json(
        changed=True,
    )


if __name__ == "__main__":
    main()
