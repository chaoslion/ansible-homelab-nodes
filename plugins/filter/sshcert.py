import base64
import io
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import NamedTuple

from jinja2.environment import Template

CLIENT_DEFAULT_PRINCIPALS = {"root", "homelab"}

SSHCERT_INSTALL_COMMON = """\
{% macro install_package() %}
{%- if not no_header -%}
#!/bin/bash
set -euxo pipefail
# KEY: {{ keygen_args | join(' ') }}
# CERT: {{ keygen_cert_args | join(' ') }}
{%- endif %}
readonly HOMELAB_SSH_PATH={{ output }}
{% if no_overwrite -%}
rm -rf "${HOMELAB_SSH_PATH}"
{% else -%}
if test -d "${HOMELAB_SSH_PATH}"; then
    exit 1
fi
{% endif -%}
mkdir "${HOMELAB_SSH_PATH}"
base64 -d <<'EOF' | tar -C "${HOMELAB_SSH_PATH}" --no-same-owner -xzvf -
{{ package }}
EOF
cat <<EOF > ${HOMELAB_SSH_PATH}/config
{{ caller() | trim }}
EOF
chmod 600 "${HOMELAB_SSH_PATH}/config"
{% endmacro %}
"""

SSHCERT_INSTALL_CLIENT = """\
{%- call install_package() -%}
Host host-*.{{ domain }} {{ specfic_options.ip_range | join(' ') }}
    UserKnownHostsFile "${HOMELAB_SSH_PATH}/hosts"
    IdentityFile "${HOMELAB_SSH_PATH}/key"
    IdentitiesOnly yes
Host host-node-*.{{ domain }}
    User homelab
{%- endcall -%}
"""


SSHCERT_INSTALL_SERVER = """\
{%- call install_package() -%}
TrustedUserCAKeys "${HOMELAB_SSH_PATH}/ca.pub"
HostCertificate "${HOMELAB_SSH_PATH}/key-cert.pub"
HostKey "${HOMELAB_SSH_PATH}/key"
PubkeyAuthentication yes
ChallengeResponseAuthentication no
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
{%- endcall -%}
echo "Include ${HOMELAB_SSH_PATH}/config" > /etc/ssh/sshd_config.d/2424-homelab.conf
"""


class Options(NamedTuple):
    ca_path: Path
    output_path: Path | None
    domain: str
    no_header: bool
    no_overwrite: bool


class OptionsClient(NamedTuple):
    ip_range: list[str]


class OptionsServer(NamedTuple):
    hostname: str
    ip: str


def _generate_package(
    options: Options,
    specfic_options: OptionsClient | OptionsServer,
):
    is_server = isinstance(specfic_options, OptionsServer)

    cert_args: list[str] = []
    ca_content = options.ca_path.read_text()
    ca_pub = options.ca_path.with_suffix(".pub")
    ca_pub_content = ca_pub.read_text()

    output_expanded = (
        options.output_path.expanduser()
        if options.output_path is not None
        else Path.cwd() / f"homelab-{('server' if is_server else 'client')}"
    )

    principals = (
        [
            f"host-{specfic_options.hostname}.{options.domain}",
            specfic_options.ip,
        ]
        if is_server
        else CLIENT_DEFAULT_PRINCIPALS
    )

    cert_args.append(
        f"-n{','.join(principals)}",
    )
    if is_server:
        cert_args.append("-h")
        cert_args.append("-Valways:forever")

    with tempfile.TemporaryDirectory() as dir_package_output:
        path_output = Path(dir_package_output)
        path_output_ca = Path(path_output) / "ca"
        path_output_capub = Path(path_output) / "ca.pub"
        path_key = path_output / "key"
        path_hosts = path_output / "hosts"

        if not is_server:
            _ = path_hosts.write_text(f"@cert-authority * {ca_pub_content.strip()}\n")

        _ = path_output_ca.write_text(ca_content)
        path_output_ca.chmod(0o600)

        _ = path_output_capub.write_text(ca_pub_content)
        path_output_capub.chmod(0o644)

        sshkeygen_args = [
            "-ted25519",
            f"-f{path_key}",
            "-N",
            "",
        ]

        _ = subprocess.run(
            [
                "ssh-keygen",
                "-q",
                *sshkeygen_args,
            ],
            check=True,
        )

        sshkeygen_cert_args = [
            "-s",
            str(path_output_ca),
            "-Ihomelab",
            *cert_args,
            f"{path_key.with_suffix('.pub')}",
        ]

        _ = subprocess.run(
            [
                "ssh-keygen",
                "-q",
                *sshkeygen_cert_args,
            ],
            check=True,
        )

        # customize output
        path_output_ca.unlink()
        if not is_server:
            path_output_capub.unlink()

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as ftar:
            ftar.add(path_output, "./")

        package = base64.b64encode(tar_buffer.getvalue())
        template = Template(
            SSHCERT_INSTALL_COMMON
            + (SSHCERT_INSTALL_SERVER if is_server else SSHCERT_INSTALL_CLIENT)
        )
        install_script_content = template.render(
            {
                "domain": options.domain,
                "keygen_args": sshkeygen_args,
                "keygen_cert_args": sshkeygen_cert_args,
                "no_header": options.no_header,
                "no_overwrite": options.no_overwrite,
                "output": output_expanded,
                "package": package.decode(),
                "principals": principals,
                "specfic_options": specfic_options,
            },
        )

        return base64.b64encode(install_script_content.strip().encode()).decode()


class FilterModule:
    def filters(self):
        return {
            "sshcert_server": lambda ca, output, domain, hostname, ip: (
                _generate_package(
                    Options(
                        ca_path=Path(ca),
                        output_path=Path(output),
                        domain=domain,
                        no_header=True,
                        no_overwrite=False,
                    ),
                    OptionsServer(hostname=hostname, ip=ip),
                )
            ),
            "sshcert_client": lambda ca, output, domain, ip_range: _generate_package(
                Options(
                    ca_path=Path(ca),
                    output_path=Path(output),
                    domain=domain,
                    no_header=True,
                    no_overwrite=False,
                ),
                OptionsClient(ip_range=ip_range),
            ),
        }
