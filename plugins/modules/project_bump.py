#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec={
            "env": {
                "type": "path",
                "required": True,
            },
            "workspace": {
                "type": "path",
                "required": True,
            },
            "workspace_owners": {
                "required": True,
                "type": "dict",
            },
        },
        supports_check_mode=False,
    )
    services: list[tuple[str, str]] = []
    for service, config in module.params["workspace_owners"].items():
        if config["bump"] is None or config["bump"] not in {"restart", "reload"}:
            continue
        if service == "main":
            services.insert(
                0,
                (
                    service,
                    config["bump"],
                ),
            )
        else:
            services.append(
                (
                    service,
                    config["bump"],
                )
            )

    for service, service_bump_method in services:
        cmd = [
            "docker",
            "compose",
            "--env-file",
            module.params["env"],
        ]
        if service_bump_method == "restart":
            cmd.append("restart")
        elif service_bump_method == "reload":
            cmd.extend(["kill", "-sSIGHUP"])
        else:
            continue
        cmd.append(service)

        module.run_command(
            cmd,
            check_rc=True,
            cwd=module.params["workspace"],
        )

    module.exit_json(
        changed=len(services) > 0,
        services=[service for service, _ in services],
    )


if __name__ == "__main__":
    main()
