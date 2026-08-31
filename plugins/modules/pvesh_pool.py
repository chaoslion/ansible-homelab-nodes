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
            "/pools",
            "--output-format=json",
        ],
        check_rc=True,
    )

    poolid = module.params["name"].replace(" ", "-").lower()
    pools = module.from_json(stdout)
    if poolid in map(lambda p: p["poolid"], pools):
        module.exit_json(
            changed=False,
        )

    module.run_command(
        [
            "pvesh",
            "create",
            "/pools",
            "--poolid",
            poolid,
            "--comment",
            module.params["name"],
        ],
        check_rc=True,
    )

    module.exit_json(
        changed=True,
    )


if __name__ == "__main__":
    main()
